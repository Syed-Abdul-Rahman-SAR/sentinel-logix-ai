import os
import tempfile
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

# Use temp database for test isolation
temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db_path = temp_db.name
temp_db.close()
os.environ["NERLINK_DB_PATH"] = temp_db_path
import backend.app.config as config
config.DB_PATH = temp_db_path

from backend.app.main import app
from backend.app.db.database import init_db, get_db
from backend.app.db.seed import seed_database
from backend.app.services.tracking_service import TrackingService

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    config.DB_PATH = temp_db_path
    init_db(temp_db_path)
    seed_database(temp_db_path)
    yield
    if os.path.exists(temp_db_path):
        try:
            os.remove(temp_db_path)
        except Exception:
            pass

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"

def test_seed_verification(client):
    # Verify seeded vehicles and drivers
    v_resp = client.get("/api/vehicles")
    assert v_resp.status_code == 200
    vehicles = v_resp.json()
    assert len(vehicles) >= 5
    
    d_resp = client.get("/api/drivers")
    assert d_resp.status_code == 200
    assert len(d_resp.json()) >= 5

def test_trip_lifecycle(client):
    # 1. Start trip for V-01 with D-01
    start_payload = {
        "vehicle_id": "V-01",
        "driver_id": "D-01",
        "origin_node": "GHY",
        "dest_node": "SIL",
        "cargo_type": "Emergency Medical Supplies",
        "cargo_weight_tons": 4.5
    }
    resp = client.post("/api/trips/start", json=start_payload)
    assert resp.status_code == 200
    trip = resp.json()
    trip_id = trip["id"]
    assert trip["status"] == "ACTIVE"
    assert trip["vehicle_id"] == "V-01"

    # 2. Starting another trip on V-01 while active should fail with 409
    resp_conflict = client.post("/api/trips/start", json=start_payload)
    assert resp_conflict.status_code == 409

    # 3. Check active trip endpoint
    active_resp = client.get("/api/trips/active/V-01")
    assert active_resp.status_code == 200
    assert active_resp.json()["active_trip"]["id"] == trip_id

    # 4. Ingest GPS telemetry for active trip
    now_iso = datetime.now(timezone.utc).isoformat()
    telemetry_payload = {
        "vehicle_id": "V-01",
        "trip_id": trip_id,
        "latitude": 26.1445,
        "longitude": 91.7362,
        "altitude": 55.0,
        "speed_kmh": 42.5,
        "heading": 135.0,
        "accuracy_meters": 5.2,
        "battery_pct": 88.0,
        "network_status": "ONLINE",
        "recorded_at": now_iso
    }
    tel_resp = client.post("/api/locations", json=telemetry_payload)
    assert tel_resp.status_code == 200
    data = tel_resp.json()
    assert data["status"] == "ok"
    assert data["telemetry"]["status"] == "IN_TRANSIT"

    # 5. Ingest second GPS point (moving toward Shillong)
    tel_resp2 = client.post("/api/locations", json={
        "vehicle_id": "V-01",
        "trip_id": trip_id,
        "latitude": 25.8600,
        "longitude": 91.8000,
        "speed_kmh": 48.0,
        "recorded_at": datetime.now(timezone.utc).isoformat()
    })
    assert tel_resp2.status_code == 200

    # 6. Verify location history is stored
    hist_resp = client.get(f"/api/locations/history/V-01?trip_id={trip_id}")
    assert hist_resp.status_code == 200
    history = hist_resp.json()["history"]
    assert len(history) >= 2

    # 7. End trip
    end_resp = client.post("/api/trips/end", json={"trip_id": trip_id})
    assert end_resp.status_code == 200
    ended_trip = end_resp.json()
    assert ended_trip["status"] == "COMPLETED"
    assert ended_trip["end_time"] is not None
    assert ended_trip["total_distance_km"] > 0.0

def test_invalid_coordinate_validation(client):
    # Invalid latitude > 90
    bad_lat = {
        "vehicle_id": "V-02",
        "latitude": 99.9999,
        "longitude": 91.8933,
        "recorded_at": datetime.now(timezone.utc).isoformat()
    }
    resp = client.post("/api/locations", json=bad_lat)
    assert resp.status_code == 422

    # Invalid longitude < -180
    bad_lng = {
        "vehicle_id": "V-02",
        "latitude": 25.5788,
        "longitude": -195.0,
        "recorded_at": datetime.now(timezone.utc).isoformat()
    }
    resp2 = client.post("/api/locations", json=bad_lng)
    assert resp2.status_code == 422

def test_offline_batch_sync(client):
    now = datetime.now(timezone.utc)
    # Simulate 3 points captured while driving through a mountain gorge without mobile signal
    batch_payload = {
        "vehicle_id": "V-03",
        "points": [
            {
                "vehicle_id": "V-03",
                "latitude": 26.7000,
                "longitude": 92.8100,
                "speed_kmh": 35.0,
                "recorded_at": (now - timedelta(seconds=120)).isoformat()
            },
            {
                "vehicle_id": "V-03",
                "latitude": 26.8500,
                "longitude": 92.8300,
                "speed_kmh": 38.0,
                "recorded_at": (now - timedelta(seconds=60)).isoformat()
            },
            {
                "vehicle_id": "V-03",
                "latitude": 27.0000,
                "longitude": 92.8500,
                "speed_kmh": 40.0,
                "recorded_at": now.isoformat()
            }
        ]
    }
    resp = client.post("/api/locations/sync", json=batch_payload)
    assert resp.status_code == 200
    assert resp.json()["result"]["synced_count"] == 3

    # Check that latest state has the newest point (27.0000)
    latest_resp = client.get("/api/locations/latest")
    assert latest_resp.status_code == 200
    v3 = next(v for v in latest_resp.json() if v["vehicle_id"] == "V-03")
    assert abs(v3["latitude"] - 27.0000) < 0.001

def test_stale_detection(client):
    # Set V-04 to a timestamp 60 seconds in the past to test stale state computation
    past_iso = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
    with get_db(temp_db_path) as conn:
        conn.execute("""
        UPDATE latest_vehicle_states 
        SET received_at = ?, status = 'ONLINE'
        WHERE vehicle_id = 'V-04'
        """, (past_iso,))

    states = TrackingService.get_latest_states(temp_db_path)
    v4 = next(v for v in states if v["vehicle_id"] == "V-04")
    assert v4["is_stale"] is True
    assert v4["status"] == "STALE"
    assert v4["age_seconds"] >= 50.0

def test_incident_reporting(client):
    incident_payload = {
        "type": "LANDSLIDE",
        "severity": "CRITICAL",
        "title": "Bhalukpong Rockfall Blockade",
        "description": "Boulders on NH-13 near Bhalukpong bridge",
        "latitude": 27.0125,
        "longitude": 92.6541,
        "road_name": "NH-13",
        "reported_by": "V-03-DRIVER"
    }
    resp = client.post("/api/incidents", json=incident_payload)
    assert resp.status_code == 200
    inc = resp.json()
    inc_id = inc["id"]
    assert inc["title"] == "Bhalukpong Rockfall Blockade"
    assert inc["is_active"] is True

    # List active incidents
    list_resp = client.get("/api/incidents?is_active=true")
    assert list_resp.status_code == 200
    active_list = list_resp.json()
    assert any(i["id"] == inc_id for i in active_list)

    # Resolve incident
    res_resp = client.post(f"/api/incidents/{inc_id}/resolve")
    assert res_resp.status_code == 200
    assert res_resp.json()["is_active"] is False

def test_websocket_dashboard(client):
    with client.websocket_connect("/ws/dashboard") as ws:
        # First message must be the fleet snapshot
        snapshot_msg = ws.receive_json()
        assert snapshot_msg["type"] == "FLEET_SNAPSHOT"
        assert len(snapshot_msg["vehicles"]) >= 5
        
        # Test ping/pong
        ws.send_text("ping")
        pong = ws.receive_text()
        assert pong == "pong"

def test_driver_websocket(client):
    with client.websocket_connect("/ws/driver/V-05") as ws:
        # Send telemetry over WebSocket
        ws.send_json({
            "latitude": 25.9090,
            "longitude": 93.7266,
            "speed_kmh": 32.0,
            "heading": 85.0,
            "recorded_at": datetime.now(timezone.utc).isoformat()
        })
        ack = ws.receive_json()
        assert ack["type"] == "TELEMETRY_ACK"
        assert ack["status"] == "PERSISTED"

def test_static_and_dashboard_serving(client):
    # Verify dashboard root returns 200 HTML
    resp = client.get("/")
    assert resp.status_code == 200
    assert "NER-LINK" in resp.text

    # Verify driver client page returns 200 HTML
    driver_resp = client.get("/driver-client/")
    assert driver_resp.status_code == 200
    assert "Driver Cockpit" in driver_resp.text


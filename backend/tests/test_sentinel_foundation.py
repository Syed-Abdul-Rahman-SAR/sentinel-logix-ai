import os
import tempfile
import pytest
from fastapi.testclient import TestClient

# Use temp database for test isolation
temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db_path = temp_db.name
temp_db.close()
os.environ["NERLINK_DB_PATH"] = temp_db_path
import backend.app.config as config
config.DB_PATH = temp_db_path

from backend.app.main import app
from backend.app.db.seed import seed_database

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    config.DB_PATH = temp_db_path
    from backend.app.db.database import init_db
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

def test_bases_crud_and_validation(client):
    # 1. Seed verification: check seeded bases
    resp = client.get("/api/bases")
    assert resp.status_code == 200
    bases = resp.json()
    assert len(bases) >= 4
    assert any(b["id"] == "BASE-GHY" for b in bases)

    # 2. Get specific base
    ghy = client.get("/api/bases/BASE-GHY")
    assert ghy.status_code == 200
    assert ghy.json()["name"] == "Guwahati Central Logistics Hub"

    # 3. Create new base
    new_base_payload = {
        "name": "Tezpur Forward Staging Base",
        "base_type": "SUPPORT_BASE",
        "latitude": 26.6528,
        "longitude": 92.7926,
        "capacity": 1800.0,
        "status": "OPERATIONAL",
        "description": "Tactical staging area",
        "road_node_id": "TEZ"
    }
    create_resp = client.post("/api/bases", json=new_base_payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    base_id = created["id"]
    assert created["name"] == "Tezpur Forward Staging Base"

    # 4. Update base
    update_resp = client.put(f"/api/bases/{base_id}", json={"status": "LIMITED", "capacity": 2000.0})
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "LIMITED"

    # 5. Invalid base_type validation
    invalid_type = {**new_base_payload, "base_type": "INVALID_TYPE"}
    assert client.post("/api/bases", json=invalid_type).status_code == 422

    # 6. Invalid road_node_id reference validation
    invalid_node = {**new_base_payload, "road_node_id": "NON_EXISTENT_NODE"}
    assert client.post("/api/bases", json=invalid_node).status_code == 400

def test_depots_crud_and_relationship(client):
    # 1. Seed verification
    resp = client.get("/api/depots")
    assert resp.status_code == 200
    depots = resp.json()
    assert len(depots) >= 5

    # 2. Filter depots by base_id
    ghy_depots = client.get("/api/depots?base_id=BASE-GHY")
    assert ghy_depots.status_code == 200
    assert len(ghy_depots.json()) >= 2

    # 3. Create depot under BASE-GHY
    new_depot = {
        "base_id": "BASE-GHY",
        "name": "Guwahati Medical Storage Unit B",
        "depot_type": "MEDICAL",
        "storage_capacity": 8000.0,
        "status": "OPERATIONAL",
        "latitude": 26.1448,
        "longitude": 91.7368
    }
    create_resp = client.post("/api/depots", json=new_depot)
    assert create_resp.status_code == 201
    depot_id = create_resp.json()["id"]

    # 4. Invalid base_id relationship handling
    bad_base_depot = {**new_depot, "base_id": "BASE-NONEXISTENT"}
    assert client.post("/api/depots", json=bad_base_depot).status_code == 400

def test_inventory_crud_and_validation(client):
    # 1. Seed verification
    resp = client.get("/api/inventory")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 5

    # 2. Create inventory item
    new_item = {
        "depot_id": "DEPOT-GHY-FUEL",
        "item_name": "Aviation Jet-A Fuel",
        "category": "FUEL",
        "unit": "LITERS",
        "current_quantity": 15000.0,
        "minimum_threshold": 5000.0,
        "maximum_capacity": 3000.0,  # Invalid: current > max!
        "daily_consumption_rate": 500.0,
        "criticality": "HIGH"
    }
    # Should fail validation because current_quantity > maximum_capacity
    assert client.post("/api/inventory", json=new_item).status_code == 400

    # Fix capacity and recreate
    new_item["maximum_capacity"] = 25000.0
    create_resp = client.post("/api/inventory", json=new_item)
    assert create_resp.status_code == 201
    item_id = create_resp.json()["id"]

    # 3. Update stock quantity
    upd_resp = client.put(f"/api/inventory/{item_id}", json={"current_quantity": 12000.0})
    assert upd_resp.status_code == 200
    assert upd_resp.json()["current_quantity"] == 12000.0

    # 4. Invalid negative stock validation
    neg_item = {**new_item, "current_quantity": -50.0}
    assert client.post("/api/inventory", json=neg_item).status_code == 422

    # 5. Invalid parent depot relationship
    bad_depot_item = {**new_item, "depot_id": "DEPOT-NONEXISTENT"}
    assert client.post("/api/inventory", json=bad_depot_item).status_code == 400

def test_consumption_history_creation_and_filtering(client):
    # 1. Seed verification: consumption records pre-seeded
    resp = client.get("/api/consumption")
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) >= 14 * 5  # 14 days x 5 configs = 70 records

    # 2. Filter by inventory_item_id
    diesel_history = client.get("/api/consumption?inventory_item_id=INV-GHY-DIESEL")
    assert diesel_history.status_code == 200
    assert len(diesel_history.json()) == 14

    # 3. Add new consumption record
    new_rec = {
        "depot_id": "DEPOT-GHY-FUEL",
        "inventory_item_id": "INV-GHY-DIESEL",
        "quantity_consumed": 1350.0,
        "consumption_date": "2026-10-02",
        "operational_intensity": "HIGH"
    }
    create_resp = client.post("/api/consumption", json=new_rec)
    assert create_resp.status_code == 201
    assert create_resp.json()["quantity_consumed"] == 1350.0

    # 4. Invalid item-to-depot mismatch validation
    mismatched_rec = {
        "depot_id": "DEPOT-SHL-MED",  # Wrong depot for INV-GHY-DIESEL!
        "inventory_item_id": "INV-GHY-DIESEL",
        "quantity_consumed": 500.0,
        "consumption_date": "2026-10-02"
    }
    assert client.post("/api/consumption", json=mismatched_rec).status_code == 400

    # 5. Non-positive quantity validation
    zero_rec = {**new_rec, "quantity_consumed": 0.0}
    assert client.post("/api/consumption", json=zero_rec).status_code == 422

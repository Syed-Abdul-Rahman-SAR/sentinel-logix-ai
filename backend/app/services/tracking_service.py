import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from ..db.database import get_db, haversine_km
from ..schemas.location import LocationTelemetry, LocationBatch
from ..websocket.connection_manager import manager
from ..config import STALE_THRESHOLD_SECONDS, NER_BOUNDS

logger = logging.getLogger("nerlink.tracking")

class TrackingService:
    @staticmethod
    def _is_within_ner_bounds(lat: float, lng: float) -> bool:
        return (
            NER_BOUNDS["min_lat"] <= lat <= NER_BOUNDS["max_lat"] and
            NER_BOUNDS["min_lng"] <= lng <= NER_BOUNDS["max_lng"]
        )

    @staticmethod
    async def process_telemetry(data: LocationTelemetry, db_path: str = None) -> Dict[str, Any]:
        """Ingest, validate, store, and broadcast a single location telemetry update."""
        server_received_at = datetime.now(timezone.utc).isoformat()
        
        # Spatial bounding check
        in_ner = TrackingService._is_within_ner_bounds(data.latitude, data.longitude)
        if not in_ner:
            logger.warning(f"Vehicle {data.vehicle_id} coordinates ({data.latitude}, {data.longitude}) outside NER bounds.")

        with get_db(db_path) as conn:
            cursor = conn.cursor()
            
            # Fetch previous position from latest_vehicle_states to compute delta distance
            cursor.execute("SELECT latitude, longitude, speed_kmh, trip_id, status FROM latest_vehicle_states WHERE vehicle_id = ?", (data.vehicle_id,))
            prev = cursor.fetchone()
            
            delta_km = 0.0
            computed_speed = data.speed_kmh or 0.0
            
            if prev and prev["latitude"] is not None and prev["longitude"] is not None:
                delta_km = haversine_km(prev["latitude"], prev["longitude"], data.latitude, data.longitude)
                # If speed is reported 0 or not set, estimate from delta distance if reasonable
                if computed_speed == 0.0 and delta_km > 0.02:
                    computed_speed = min(80.0, round(delta_km * 3600 / 10, 1)) # rough estimate for 10s ping

            # Active trip association
            effective_trip_id = data.trip_id
            if not effective_trip_id and prev and prev["trip_id"]:
                effective_trip_id = prev["trip_id"]

            # Update trip accumulated distance if active
            if effective_trip_id and delta_km > 0:
                cursor.execute("""
                UPDATE trips 
                SET total_distance_km = total_distance_km + ? 
                WHERE id = ? AND status = 'ACTIVE'
                """, (delta_km, effective_trip_id))

            # 1. Insert into vehicle_locations (History / Audit Trail)
            cursor.execute("""
            INSERT INTO vehicle_locations 
            (trip_id, vehicle_id, latitude, longitude, altitude, speed_kmh, heading, accuracy_meters, battery_pct, network_status, recorded_at, received_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                effective_trip_id,
                data.vehicle_id,
                data.latitude,
                data.longitude,
                data.altitude or 0.0,
                computed_speed,
                data.heading or 0.0,
                data.accuracy_meters or 10.0,
                data.battery_pct or 100.0,
                data.network_status or "ONLINE",
                data.recorded_at,
                server_received_at
            ))

            # 2. Upsert into latest_vehicle_states (O(1) dashboard cache)
            status = "IN_TRANSIT" if effective_trip_id else "ONLINE"
            cursor.execute("""
            INSERT INTO latest_vehicle_states 
            (vehicle_id, trip_id, driver_id, latitude, longitude, altitude, speed_kmh, heading, accuracy_meters, battery_pct, network_status, status, recorded_at, received_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(vehicle_id) DO UPDATE SET
                trip_id = coalesce(excluded.trip_id, latest_vehicle_states.trip_id),
                driver_id = coalesce(excluded.driver_id, latest_vehicle_states.driver_id),
                latitude = excluded.latitude,
                longitude = excluded.longitude,
                altitude = excluded.altitude,
                speed_kmh = excluded.speed_kmh,
                heading = excluded.heading,
                accuracy_meters = excluded.accuracy_meters,
                battery_pct = excluded.battery_pct,
                network_status = excluded.network_status,
                status = excluded.status,
                recorded_at = excluded.recorded_at,
                received_at = excluded.received_at;
            """, (
                data.vehicle_id,
                effective_trip_id,
                data.driver_id,
                data.latitude,
                data.longitude,
                data.altitude or 0.0,
                computed_speed,
                data.heading or 0.0,
                data.accuracy_meters or 10.0,
                data.battery_pct or 100.0,
                data.network_status or "ONLINE",
                status,
                data.recorded_at,
                server_received_at
            ))

        # Prepare payload for dashboard broadcast
        broadcast_payload = {
            "type": "TELEMETRY_UPDATE",
            "data": {
                "vehicle_id": data.vehicle_id,
                "trip_id": effective_trip_id,
                "latitude": data.latitude,
                "longitude": data.longitude,
                "altitude": data.altitude or 0.0,
                "speed_kmh": computed_speed,
                "heading": data.heading or 0.0,
                "accuracy_meters": data.accuracy_meters or 10.0,
                "battery_pct": data.battery_pct or 100.0,
                "network_status": data.network_status or "ONLINE",
                "status": status,
                "recorded_at": data.recorded_at,
                "received_at": server_received_at,
                "in_ner_bounds": in_ner,
                "is_stale": False,
                "age_seconds": 0.0
            }
        }
        await manager.broadcast_to_dashboards(broadcast_payload)
        return broadcast_payload["data"]

    @staticmethod
    async def process_batch(batch: LocationBatch, db_path: str = None) -> Dict[str, Any]:
        """Ingest batch telemetry points stored while vehicle was offline."""
        server_received_at = datetime.now(timezone.utc).isoformat()
        points = sorted(batch.points, key=lambda p: p.recorded_at)
        total_points = len(points)
        if total_points == 0:
            return {"synced_count": 0}

        latest_point = points[-1]
        
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT trip_id FROM latest_vehicle_states WHERE vehicle_id = ?", (batch.vehicle_id,))
            state = cursor.fetchone()
            active_trip = batch.trip_id or (state["trip_id"] if state else None)

            # Insert all points into history
            for pt in points:
                cursor.execute("""
                INSERT INTO vehicle_locations 
                (trip_id, vehicle_id, latitude, longitude, altitude, speed_kmh, heading, accuracy_meters, battery_pct, network_status, recorded_at, received_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    active_trip,
                    batch.vehicle_id,
                    pt.latitude,
                    pt.longitude,
                    pt.altitude or 0.0,
                    pt.speed_kmh or 0.0,
                    pt.heading or 0.0,
                    pt.accuracy_meters or 10.0,
                    pt.battery_pct or 100.0,
                    "OFFLINE_SYNC",
                    pt.recorded_at,
                    server_received_at
                ))

            # Upsert latest state with the newest point in the batch
            status = "IN_TRANSIT" if active_trip else "ONLINE"
            cursor.execute("""
            INSERT INTO latest_vehicle_states 
            (vehicle_id, trip_id, driver_id, latitude, longitude, altitude, speed_kmh, heading, accuracy_meters, battery_pct, network_status, status, recorded_at, received_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ONLINE', ?, ?, ?)
            ON CONFLICT(vehicle_id) DO UPDATE SET
                trip_id = coalesce(excluded.trip_id, latest_vehicle_states.trip_id),
                driver_id = coalesce(excluded.driver_id, latest_vehicle_states.driver_id),
                latitude = excluded.latitude,
                longitude = excluded.longitude,
                altitude = excluded.altitude,
                speed_kmh = excluded.speed_kmh,
                heading = excluded.heading,
                accuracy_meters = excluded.accuracy_meters,
                battery_pct = excluded.battery_pct,
                network_status = 'ONLINE',
                status = excluded.status,
                recorded_at = excluded.recorded_at,
                received_at = excluded.received_at;
            """, (
                batch.vehicle_id,
                active_trip,
                latest_point.driver_id,
                latest_point.latitude,
                latest_point.longitude,
                latest_point.altitude or 0.0,
                latest_point.speed_kmh or 0.0,
                latest_point.heading or 0.0,
                latest_point.accuracy_meters or 10.0,
                latest_point.battery_pct or 100.0,
                status,
                latest_point.recorded_at,
                server_received_at
            ))

        broadcast_payload = {
            "type": "BATCH_SYNCED",
            "vehicle_id": batch.vehicle_id,
            "points_synced": total_points,
            "latest_point": {
                "latitude": latest_point.latitude,
                "longitude": latest_point.longitude,
                "recorded_at": latest_point.recorded_at,
                "received_at": server_received_at
            }
        }
        await manager.broadcast_to_dashboards(broadcast_payload)
        return {"vehicle_id": batch.vehicle_id, "synced_count": total_points}

    @staticmethod
    def get_latest_states(db_path: str = None) -> List[Dict[str, Any]]:
        """Retrieve latest vehicle states with calculated age and stale flag."""
        now = datetime.now(timezone.utc)
        results = []
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT 
                s.*,
                v.plate_number,
                v.vehicle_type,
                v.capacity_tons,
                d.name as driver_name,
                d.phone as driver_phone
            FROM latest_vehicle_states s
            LEFT JOIN vehicles v ON s.vehicle_id = v.id
            LEFT JOIN drivers d ON s.driver_id = d.id
            """)
            rows = cursor.fetchall()
            for r in rows:
                item = dict(r)
                # Compute elapsed seconds since last received telemetry
                try:
                    recv_time = datetime.fromisoformat(item["received_at"].replace("Z", "+00:00"))
                    age = (now - recv_time).total_seconds()
                except Exception:
                    age = 0.0
                
                is_stale = age > STALE_THRESHOLD_SECONDS and item["status"] not in ("IDLE", "OFFLINE")
                item["age_seconds"] = round(age, 1)
                item["is_stale"] = is_stale
                if is_stale and item["status"] != "STALE":
                    item["status"] = "STALE"
                results.append(item)
        return results

    @staticmethod
    async def check_and_broadcast_stale_vehicles(db_path: str = None):
        """Background task helper: detects stale vehicles and alerts dashboards."""
        now = datetime.now(timezone.utc)
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT vehicle_id, status, received_at FROM latest_vehicle_states WHERE status IN ('ONLINE', 'IN_TRANSIT')")
            active_vehicles = cursor.fetchall()
            
            stale_ids = []
            for row in active_vehicles:
                try:
                    recv = datetime.fromisoformat(row["received_at"].replace("Z", "+00:00"))
                    age = (now - recv).total_seconds()
                    if age > STALE_THRESHOLD_SECONDS:
                        stale_ids.append((row["vehicle_id"], age))
                except Exception:
                    continue

            for vid, age in stale_ids:
                cursor.execute("UPDATE latest_vehicle_states SET status = 'STALE' WHERE vehicle_id = ?", (vid,))
                logger.warning(f"Vehicle {vid} detected STALE (no ping for {age:.1f}s)")
                await manager.broadcast_to_dashboards({
                    "type": "VEHICLE_STALE",
                    "vehicle_id": vid,
                    "age_seconds": round(age, 1),
                    "status": "STALE",
                    "message": f"Vehicle {vid} has stopped reporting telemetry for {round(age)}s (possible terrain dead-zone)"
                })

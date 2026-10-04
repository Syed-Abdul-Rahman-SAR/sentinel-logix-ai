import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import HTTPException
from ..db.database import get_db
from ..schemas.trip import TripStartRequest, TripEndRequest

class TripService:
    @staticmethod
    def start_trip(req: TripStartRequest, db_path: str = None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            
            # 1. Verify vehicle exists
            cursor.execute("SELECT id, status FROM vehicles WHERE id = ?", (req.vehicle_id,))
            veh = cursor.fetchone()
            if not veh:
                raise HTTPException(status_code=404, detail=f"Vehicle {req.vehicle_id} not found")
            
            # 2. Verify driver exists
            cursor.execute("SELECT id, is_active FROM drivers WHERE id = ?", (req.driver_id,))
            drv = cursor.fetchone()
            if not drv:
                raise HTTPException(status_code=404, detail=f"Driver {req.driver_id} not found")
            if not drv["is_active"]:
                raise HTTPException(status_code=400, detail=f"Driver {req.driver_id} is inactive")
                
            # 3. Check if vehicle already has an active trip
            cursor.execute("SELECT id FROM trips WHERE vehicle_id = ? AND status = 'ACTIVE'", (req.vehicle_id,))
            existing = cursor.fetchone()
            if existing:
                raise HTTPException(status_code=409, detail=f"Vehicle {req.vehicle_id} already has active trip {existing['id']}. Please end it first.")

            # 4. Create new trip
            trip_id = f"TRIP-{uuid.uuid4().hex[:8].upper()}"
            cursor.execute("""
            INSERT INTO trips (id, vehicle_id, driver_id, origin_node, dest_node, cargo_type, cargo_weight_tons, status, start_time, total_distance_km)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, 0.0)
            """, (trip_id, req.vehicle_id, req.driver_id, req.origin_node, req.dest_node, req.cargo_type, req.cargo_weight_tons, now))

            # 5. Update vehicle status to IN_TRANSIT
            cursor.execute("UPDATE vehicles SET status = 'IN_TRANSIT' WHERE id = ?", (req.vehicle_id,))
            
            # 6. Update latest state with active trip_id
            cursor.execute("""
            UPDATE latest_vehicle_states 
            SET trip_id = ?, driver_id = ?, status = 'IN_TRANSIT'
            WHERE vehicle_id = ?
            """, (trip_id, req.driver_id, req.vehicle_id))

            cursor.execute("SELECT * FROM trips WHERE id = ?", (trip_id,))
            row = cursor.fetchone()
            return dict(row)

    @staticmethod
    def end_trip(req: TripEndRequest, db_path: str = None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trips WHERE id = ?", (req.trip_id,))
            trip = cursor.fetchone()
            if not trip:
                raise HTTPException(status_code=404, detail=f"Trip {req.trip_id} not found")
            if trip["status"] != "ACTIVE":
                raise HTTPException(status_code=400, detail=f"Trip {req.trip_id} is already {trip['status']}")

            vehicle_id = trip["vehicle_id"]

            cursor.execute("""
            UPDATE trips 
            SET status = 'COMPLETED', end_time = ?
            WHERE id = ?
            """, (now, req.trip_id))

            cursor.execute("UPDATE vehicles SET status = 'IDLE' WHERE id = ?", (vehicle_id,))

            cursor.execute("""
            UPDATE latest_vehicle_states 
            SET trip_id = NULL, status = 'IDLE'
            WHERE vehicle_id = ?
            """, (vehicle_id,))

            cursor.execute("SELECT * FROM trips WHERE id = ?", (req.trip_id,))
            row = cursor.fetchone()
            return dict(row)

    @staticmethod
    def get_active_trip_for_vehicle(vehicle_id: str, db_path: str = None) -> Optional[Dict[str, Any]]:
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trips WHERE vehicle_id = ? AND status = 'ACTIVE'", (vehicle_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def list_trips(status: Optional[str] = None, limit: int = 50, db_path: str = None) -> List[Dict[str, Any]]:
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute("SELECT * FROM trips WHERE status = ? ORDER BY start_time DESC LIMIT ?", (status, limit))
            else:
                cursor.execute("SELECT * FROM trips ORDER BY start_time DESC LIMIT ?", (limit,))
            return [dict(r) for r in cursor.fetchall()]

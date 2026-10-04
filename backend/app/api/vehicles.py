from fastapi import APIRouter
from typing import List, Dict, Any
from ..db.database import get_db

router = APIRouter(prefix="/api", tags=["Vehicles & Network"])

@router.get("/vehicles")
def list_vehicles():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT 
            v.*, 
            s.latitude, 
            s.longitude, 
            s.status as state_status, 
            s.trip_id,
            s.speed_kmh,
            s.received_at
        FROM vehicles v
        LEFT JOIN latest_vehicle_states s ON v.id = s.vehicle_id
        """)
        return [dict(r) for r in cursor.fetchall()]

@router.get("/drivers")
def list_drivers():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM drivers WHERE is_active = 1")
        return [dict(r) for r in cursor.fetchall()]

@router.get("/network/nodes")
def list_nodes():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM road_nodes")
        return [dict(r) for r in cursor.fetchall()]

@router.get("/network/segments")
def list_segments():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM road_segments")
        return [dict(r) for r in cursor.fetchall()]

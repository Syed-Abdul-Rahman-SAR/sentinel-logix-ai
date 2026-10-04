from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from ..schemas.location import LocationTelemetry, LocationBatch, LatestStateOut
from ..services.tracking_service import TrackingService
from ..db.database import get_db

router = APIRouter(prefix="/api/locations", tags=["Locations"])

@router.post("", summary="Ingest real-time GPS telemetry from vehicle/driver")
async def ingest_location(data: LocationTelemetry):
    result = await TrackingService.process_telemetry(data)
    return {"status": "ok", "telemetry": result}

@router.post("/sync", summary="Batch sync offline telemetry when re-entering coverage")
async def sync_offline_locations(batch: LocationBatch):
    result = await TrackingService.process_batch(batch)
    return {"status": "ok", "result": result}

@router.get("/latest", response_model=List[LatestStateOut], summary="Get snapshot of all vehicles' latest positions and stale statuses")
async def get_latest_locations():
    return TrackingService.get_latest_states()

@router.get("/history/{vehicle_id}", summary="Get location history for route replay")
async def get_vehicle_history(
    vehicle_id: str,
    trip_id: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000)
):
    with get_db() as conn:
        cursor = conn.cursor()
        if trip_id:
            cursor.execute("""
            SELECT * FROM vehicle_locations 
            WHERE vehicle_id = ? AND trip_id = ? 
            ORDER BY recorded_at ASC LIMIT ?
            """, (vehicle_id, trip_id, limit))
        else:
            cursor.execute("""
            SELECT * FROM vehicle_locations 
            WHERE vehicle_id = ? 
            ORDER BY recorded_at DESC LIMIT ?
            """, (vehicle_id, limit))
        rows = cursor.fetchall()
        # Return chronological
        items = [dict(r) for r in rows]
        if not trip_id:
            items.reverse()
        return {"vehicle_id": vehicle_id, "count": len(items), "history": items}

from fastapi import APIRouter, Query
from typing import List, Optional
from ..schemas.trip import TripStartRequest, TripEndRequest, TripOut
from ..services.trip_service import TripService
from ..websocket.connection_manager import manager

router = APIRouter(prefix="/api/trips", tags=["Trips"])

@router.post("/start", response_model=TripOut)
async def start_trip(req: TripStartRequest):
    result = TripService.start_trip(req)
    await manager.broadcast_to_dashboards({
        "type": "TRIP_STARTED",
        "trip": result
    })
    return result

@router.post("/end", response_model=TripOut)
async def end_trip(req: TripEndRequest):
    result = TripService.end_trip(req)
    await manager.broadcast_to_dashboards({
        "type": "TRIP_ENDED",
        "trip": result
    })
    return result

@router.get("/active/{vehicle_id}")
async def get_active_trip(vehicle_id: str):
    trip = TripService.get_active_trip_for_vehicle(vehicle_id)
    return {"active_trip": trip}

@router.get("", response_model=List[TripOut])
async def list_trips(status: Optional[str] = Query(None, description="Filter by ACTIVE or COMPLETED")):
    return TripService.list_trips(status=status)

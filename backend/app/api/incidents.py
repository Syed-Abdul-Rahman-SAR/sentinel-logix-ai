from fastapi import APIRouter, Query
from typing import List, Optional
from ..schemas.incident import IncidentCreate, IncidentOut
from ..services.incident_service import IncidentService

router = APIRouter(prefix="/api/incidents", tags=["Incidents & Hazards"])

@router.post("", response_model=IncidentOut)
async def report_incident(data: IncidentCreate):
    return await IncidentService.create_incident(data)

@router.get("", response_model=List[IncidentOut])
def list_incidents(is_active: Optional[bool] = Query(None)):
    return IncidentService.list_incidents(is_active=is_active)

@router.post("/{incident_id}/resolve", response_model=IncidentOut)
async def resolve_incident(incident_id: str):
    return await IncidentService.resolve_incident(incident_id)

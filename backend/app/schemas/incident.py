from pydantic import BaseModel, Field, validator
from typing import Optional

class IncidentCreate(BaseModel):
    type: str = Field(..., description="LANDSLIDE, FLOOD, ROAD_BLOCK, ACCIDENT, FOG_HAZARD")
    severity: str = Field("HIGH", description="LOW, MEDIUM, HIGH, CRITICAL")
    title: str = Field(..., min_length=3, max_length=150)
    description: Optional[str] = None
    latitude: float = Field(...)
    longitude: float = Field(...)
    road_name: Optional[str] = None
    reported_by: Optional[str] = "DRIVER"

    @validator("latitude")
    def validate_lat(cls, v):
        if not (-90.0 <= v <= 90.0):
            raise ValueError("Latitude out of range")
        return round(v, 6)

    @validator("longitude")
    def validate_lng(cls, v):
        if not (-180.0 <= v <= 180.0):
            raise ValueError("Longitude out of range")
        return round(v, 6)

class IncidentOut(BaseModel):
    id: str
    type: str
    severity: str
    title: str
    description: Optional[str] = None
    latitude: float
    longitude: float
    road_name: Optional[str] = None
    is_active: bool
    reported_by: Optional[str] = None
    reported_at: str
    resolved_at: Optional[str] = None

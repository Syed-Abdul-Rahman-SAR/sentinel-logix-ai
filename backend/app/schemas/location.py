from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

class LocationTelemetry(BaseModel):
    vehicle_id: str = Field(..., description="Unique vehicle ID (e.g. V-01)")
    trip_id: Optional[str] = Field(None, description="Active trip ID if underway")
    driver_id: Optional[str] = Field(None, description="Driver identifier")
    latitude: float = Field(..., description="GPS latitude in decimal degrees")
    longitude: float = Field(..., description="GPS longitude in decimal degrees")
    altitude: Optional[float] = Field(0.0, description="Altitude in meters")
    speed_kmh: Optional[float] = Field(0.0, description="Ground speed in km/h")
    heading: Optional[float] = Field(0.0, description="Course heading in degrees (0-360)")
    accuracy_meters: Optional[float] = Field(10.0, description="GPS fix horizontal accuracy in meters")
    battery_pct: Optional[float] = Field(100.0, description="Device battery percentage")
    network_status: Optional[str] = Field("ONLINE", description="ONLINE, 2G, 3G, OFFLINE_SYNC")
    recorded_at: str = Field(..., description="ISO 8601 timestamp generated on phone")

    @validator("latitude")
    def validate_latitude(cls, v):
        if not (-90.0 <= v <= 90.0):
            raise ValueError("Latitude must be between -90.0 and 90.0 degrees")
        return round(v, 6)

    @validator("longitude")
    def validate_longitude(cls, v):
        if not (-180.0 <= v <= 180.0):
            raise ValueError("Longitude must be between -180.0 and 180.0 degrees")
        return round(v, 6)

    @validator("heading")
    def validate_heading(cls, v):
        if v is not None:
            return round(v % 360.0, 2)
        return 0.0

    @validator("speed_kmh")
    def validate_speed(cls, v):
        if v is not None:
            return max(0.0, round(v, 2))
        return 0.0

    @validator("recorded_at")
    def validate_recorded_at(cls, v):
        # Ensure it can be parsed as ISO datetime
        try:
            # handle 'Z' or offset
            cleaned = v.replace("Z", "+00:00")
            datetime.fromisoformat(cleaned)
        except Exception:
            raise ValueError("recorded_at must be a valid ISO 8601 timestamp string")
        return v


class LocationBatch(BaseModel):
    vehicle_id: str
    trip_id: Optional[str] = None
    points: List[LocationTelemetry] = Field(..., min_items=1)


class LatestStateOut(BaseModel):
    vehicle_id: str
    trip_id: Optional[str] = None
    driver_id: Optional[str] = None
    plate_number: Optional[str] = None
    vehicle_type: Optional[str] = None
    latitude: float
    longitude: float
    altitude: Optional[float] = 0.0
    speed_kmh: Optional[float] = 0.0
    heading: Optional[float] = 0.0
    accuracy_meters: Optional[float] = 10.0
    battery_pct: Optional[float] = 100.0
    network_status: Optional[str] = "ONLINE"
    status: str = "ONLINE"
    recorded_at: str
    received_at: str
    is_stale: bool = False
    age_seconds: float = 0.0

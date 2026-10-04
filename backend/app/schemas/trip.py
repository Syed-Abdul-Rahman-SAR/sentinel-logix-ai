from pydantic import BaseModel, Field
from typing import Optional

class TripStartRequest(BaseModel):
    vehicle_id: str = Field(..., description="Assigned vehicle ID (e.g. V-01)")
    driver_id: str = Field(..., description="Driver ID (e.g. D-01)")
    origin_node: str = Field(..., description="Origin node code (e.g. GHY)")
    dest_node: str = Field(..., description="Destination node code (e.g. SIL)")
    cargo_type: str = Field("General Freight", description="Cargo nature (e.g. Pharmaceuticals, Food)")
    cargo_weight_tons: float = Field(5.0, ge=0.1, le=50.0, description="Cargo weight in metric tons")

class TripEndRequest(BaseModel):
    trip_id: str = Field(..., description="Active trip ID to complete")
    end_lat: Optional[float] = None
    end_lng: Optional[float] = None

class TripOut(BaseModel):
    id: str
    vehicle_id: str
    driver_id: str
    origin_node: str
    dest_node: str
    cargo_type: str
    cargo_weight_tons: float
    status: str
    start_time: str
    end_time: Optional[str] = None
    total_distance_km: float = 0.0

from pydantic import BaseModel
from typing import Optional

class DriverOut(BaseModel):
    id: str
    name: str
    phone: str
    license_no: str
    is_active: bool
    created_at: str

class VehicleOut(BaseModel):
    id: str
    plate_number: str
    vehicle_type: str
    capacity_tons: float
    fuel_type: str
    status: str
    created_at: str

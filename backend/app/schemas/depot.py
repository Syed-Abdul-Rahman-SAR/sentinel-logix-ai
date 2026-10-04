from pydantic import BaseModel, Field, field_validator
from typing import Optional

VALID_DEPOT_TYPES = {"FUEL", "FOOD", "MEDICAL", "AMMUNITION", "GENERAL_SUPPLY"}
VALID_DEPOT_STATUSES = {"OPERATIONAL", "LIMITED", "OFFLINE"}

class DepotCreate(BaseModel):
    base_id: str = Field(..., description="Parent Base ID")
    name: str = Field(..., min_length=2, description="Depot name")
    depot_type: str = Field(..., description="Depot type (FUEL, FOOD, MEDICAL, AMMUNITION, GENERAL_SUPPLY)")
    storage_capacity: float = Field(1000.0, ge=0.0, description="Total storage capacity")
    status: str = Field("OPERATIONAL", description="Status (OPERATIONAL, LIMITED, OFFLINE)")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude")

    @field_validator("depot_type")
    @classmethod
    def validate_depot_type(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in VALID_DEPOT_TYPES:
            raise ValueError(f"Invalid depot_type: {v}. Must be one of {sorted(VALID_DEPOT_TYPES)}")
        return v_upper

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in VALID_DEPOT_STATUSES:
            raise ValueError(f"Invalid status: {v}. Must be one of {sorted(VALID_DEPOT_STATUSES)}")
        return v_upper

class DepotUpdate(BaseModel):
    base_id: Optional[str] = None
    name: Optional[str] = Field(None, min_length=2)
    depot_type: Optional[str] = None
    storage_capacity: Optional[float] = Field(None, ge=0.0)
    status: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)

    @field_validator("depot_type")
    @classmethod
    def validate_depot_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v_upper = v.upper()
        if v_upper not in VALID_DEPOT_TYPES:
            raise ValueError(f"Invalid depot_type: {v}. Must be one of {sorted(VALID_DEPOT_TYPES)}")
        return v_upper

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v_upper = v.upper()
        if v_upper not in VALID_DEPOT_STATUSES:
            raise ValueError(f"Invalid status: {v}. Must be one of {sorted(VALID_DEPOT_STATUSES)}")
        return v_upper

class DepotOut(BaseModel):
    id: str
    base_id: str
    name: str
    depot_type: str
    storage_capacity: float
    status: str
    latitude: float
    longitude: float
    created_at: str
    updated_at: str

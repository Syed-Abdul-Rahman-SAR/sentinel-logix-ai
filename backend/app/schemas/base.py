from pydantic import BaseModel, Field, field_validator
from typing import Optional

VALID_BASE_TYPES = {"FORWARD_BASE", "MAIN_BASE", "SUPPORT_BASE", "LOGISTICS_HUB"}
VALID_BASE_STATUSES = {"OPERATIONAL", "LIMITED", "OFFLINE"}

class BaseCreate(BaseModel):
    name: str = Field(..., min_length=2, description="Base name")
    base_type: str = Field(..., description="Type of base (FORWARD_BASE, MAIN_BASE, SUPPORT_BASE, LOGISTICS_HUB)")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude")
    capacity: float = Field(100.0, ge=0.0, description="Capacity metric")
    status: str = Field("OPERATIONAL", description="Status (OPERATIONAL, LIMITED, OFFLINE)")
    description: Optional[str] = None
    road_node_id: Optional[str] = None

    @field_validator("base_type")
    @classmethod
    def validate_base_type(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in VALID_BASE_TYPES:
            raise ValueError(f"Invalid base_type: {v}. Must be one of {sorted(VALID_BASE_TYPES)}")
        return v_upper

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in VALID_BASE_STATUSES:
            raise ValueError(f"Invalid status: {v}. Must be one of {sorted(VALID_BASE_STATUSES)}")
        return v_upper

class BaseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2)
    base_type: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    capacity: Optional[float] = Field(None, ge=0.0)
    status: Optional[str] = None
    description: Optional[str] = None
    road_node_id: Optional[str] = None

    @field_validator("base_type")
    @classmethod
    def validate_base_type(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v_upper = v.upper()
        if v_upper not in VALID_BASE_TYPES:
            raise ValueError(f"Invalid base_type: {v}. Must be one of {sorted(VALID_BASE_TYPES)}")
        return v_upper

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v_upper = v.upper()
        if v_upper not in VALID_BASE_STATUSES:
            raise ValueError(f"Invalid status: {v}. Must be one of {sorted(VALID_BASE_STATUSES)}")
        return v_upper

class BaseOut(BaseModel):
    id: str
    name: str
    base_type: str
    latitude: float
    longitude: float
    capacity: float
    status: str
    description: Optional[str] = None
    road_node_id: Optional[str] = None
    created_at: str
    updated_at: str

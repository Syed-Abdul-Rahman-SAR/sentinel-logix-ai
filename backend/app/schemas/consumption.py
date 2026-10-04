from pydantic import BaseModel, Field, field_validator
from typing import Optional

VALID_INTENSITY_LEVELS = {"LOW", "NORMAL", "HIGH", "CRITICAL"}

class ConsumptionRecordCreate(BaseModel):
    depot_id: str = Field(..., description="Depot ID")
    inventory_item_id: str = Field(..., description="Inventory Item ID")
    quantity_consumed: float = Field(..., gt=0.0, description="Quantity consumed on given date")
    consumption_date: str = Field(..., description="Date of consumption (ISO format YYYY-MM-DD)")
    operational_intensity: str = Field("NORMAL", description="Operational intensity level (LOW, NORMAL, HIGH, CRITICAL)")

    @field_validator("operational_intensity")
    @classmethod
    def validate_intensity(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in VALID_INTENSITY_LEVELS:
            raise ValueError(f"Invalid operational_intensity: {v}. Must be one of {sorted(VALID_INTENSITY_LEVELS)}")
        return v_upper

class ConsumptionRecordOut(BaseModel):
    id: int
    depot_id: str
    inventory_item_id: str
    quantity_consumed: float
    consumption_date: str
    operational_intensity: str

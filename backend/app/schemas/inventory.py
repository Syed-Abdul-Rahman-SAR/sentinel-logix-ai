from pydantic import BaseModel, Field, field_validator
from typing import Optional

VALID_INVENTORY_CATEGORIES = {"FUEL", "FOOD", "MEDICAL", "GENERAL"}
VALID_CRITICALITY_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

class InventoryItemCreate(BaseModel):
    depot_id: str = Field(..., description="Parent Depot ID")
    item_name: str = Field(..., min_length=2, description="Item name (e.g., Diesel Fuel, MRE Rations, Emergency Trauma Kits)")
    category: str = Field(..., description="Category (FUEL, FOOD, MEDICAL, GENERAL)")
    unit: str = Field("LITERS", description="Measurement unit (LITERS, KG, BOXES, UNITS, TONS)")
    current_quantity: float = Field(..., ge=0.0, description="Current stock level")
    minimum_threshold: float = Field(..., ge=0.0, description="Minimum stock threshold before alert")
    maximum_capacity: float = Field(..., ge=0.0, description="Maximum storage capacity for item")
    daily_consumption_rate: float = Field(0.0, ge=0.0, description="Estimated daily consumption rate")
    criticality: str = Field("MEDIUM", description="Item criticality (LOW, MEDIUM, HIGH, CRITICAL)")

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in VALID_INVENTORY_CATEGORIES:
            raise ValueError(f"Invalid category: {v}. Must be one of {sorted(VALID_INVENTORY_CATEGORIES)}")
        return v_upper

    @field_validator("criticality")
    @classmethod
    def validate_criticality(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in VALID_CRITICALITY_LEVELS:
            raise ValueError(f"Invalid criticality: {v}. Must be one of {sorted(VALID_CRITICALITY_LEVELS)}")
        return v_upper

class InventoryItemUpdate(BaseModel):
    depot_id: Optional[str] = None
    item_name: Optional[str] = Field(None, min_length=2)
    category: Optional[str] = None
    unit: Optional[str] = None
    current_quantity: Optional[float] = Field(None, ge=0.0)
    minimum_threshold: Optional[float] = Field(None, ge=0.0)
    maximum_capacity: Optional[float] = Field(None, ge=0.0)
    daily_consumption_rate: Optional[float] = Field(None, ge=0.0)
    criticality: Optional[str] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v_upper = v.upper()
        if v_upper not in VALID_INVENTORY_CATEGORIES:
            raise ValueError(f"Invalid category: {v}. Must be one of {sorted(VALID_INVENTORY_CATEGORIES)}")
        return v_upper

    @field_validator("criticality")
    @classmethod
    def validate_criticality(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v_upper = v.upper()
        if v_upper not in VALID_CRITICALITY_LEVELS:
            raise ValueError(f"Invalid criticality: {v}. Must be one of {sorted(VALID_CRITICALITY_LEVELS)}")
        return v_upper

class InventoryItemOut(BaseModel):
    id: str
    depot_id: str
    item_name: str
    category: str
    unit: str
    current_quantity: float
    minimum_threshold: float
    maximum_capacity: float
    daily_consumption_rate: float
    criticality: str
    last_updated: str

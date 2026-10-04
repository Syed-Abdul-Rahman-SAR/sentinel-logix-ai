from .location import LocationTelemetry, LocationBatch, LatestStateOut
from .trip import TripStartRequest, TripEndRequest, TripOut
from .vehicle import VehicleOut, DriverOut
from .incident import IncidentCreate, IncidentOut
from .base import BaseCreate, BaseUpdate, BaseOut
from .depot import DepotCreate, DepotUpdate, DepotOut
from .inventory import InventoryItemCreate, InventoryItemUpdate, InventoryItemOut
from .consumption import ConsumptionRecordCreate, ConsumptionRecordOut

__all__ = [
    "LocationTelemetry",
    "LocationBatch",
    "LatestStateOut",
    "TripStartRequest",
    "TripEndRequest",
    "TripOut",
    "VehicleOut",
    "DriverOut",
    "IncidentCreate",
    "IncidentOut",
    "BaseCreate",
    "BaseUpdate",
    "BaseOut",
    "DepotCreate",
    "DepotUpdate",
    "DepotOut",
    "InventoryItemCreate",
    "InventoryItemUpdate",
    "InventoryItemOut",
    "ConsumptionRecordCreate",
    "ConsumptionRecordOut"
]

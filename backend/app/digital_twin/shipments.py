"""
SENTINEL LOGIX AI - Synthetic Replenishment Shipments
Defines synthetic demonstration shipment records and deterministic shipment lookup functions
for Digital Twin what-if simulations.
"""

from typing import List, Dict, Any, Optional

SYNTHETIC_REPLENISHMENT_SHIPMENTS: List[Dict[str, Any]] = [
    # Imphal Depot (DEPOT-IMP-SUP)
    {
        "shipment_id": "SHIP-IMP-001",
        "origin_base_id": "BASE-GHY",
        "destination_depot_id": "DEPOT-IMP-SUP",
        "cargo_item_id": "INV-IMP-RATIONS",
        "quantity": 1000.0,
        "expected_arrival_day": 3,
        "transit_duration_days": 2,
        "route_id": "SIL-IMP",
        "status": "IN_TRANSIT",
        "data_source": "synthetic_demo"
    },
    {
        "shipment_id": "SHIP-IMP-002",
        "origin_base_id": "BASE-SHL",
        "destination_depot_id": "DEPOT-IMP-SUP",
        "cargo_item_id": "INV-IMP-RATIONS",
        "quantity": 600.0,
        "expected_arrival_day": 6,
        "transit_duration_days": 2,
        "route_id": "KHM-IMP",
        "status": "SCHEDULED",
        "data_source": "synthetic_demo"
    },

    # Tawang Depot (DEPOT-TWA-AMM)
    {
        "shipment_id": "SHIP-TWA-001",
        "origin_base_id": "BASE-GHY",
        "destination_depot_id": "DEPOT-TWA-AMM",
        "cargo_item_id": "INV-TWA-AVGAS",
        "quantity": 1500.0,
        "expected_arrival_day": 4,
        "transit_duration_days": 3,
        "route_id": "TEZ-TWA",
        "status": "IN_TRANSIT",
        "data_source": "synthetic_demo"
    },

    # Shillong Depot (DEPOT-SHL-MED)
    {
        "shipment_id": "SHIP-SHL-001",
        "origin_base_id": "BASE-GHY",
        "destination_depot_id": "DEPOT-SHL-MED",
        "cargo_item_id": "INV-SHL-MEDKIT",
        "quantity": 300.0,
        "expected_arrival_day": 2,
        "transit_duration_days": 1,
        "route_id": "GHY-SHL",
        "status": "IN_TRANSIT",
        "data_source": "synthetic_demo"
    },

    # Guwahati Fuel Depot (DEPOT-GHY-FUEL)
    {
        "shipment_id": "SHIP-GHY-001",
        "origin_base_id": "BASE-GHY",
        "destination_depot_id": "DEPOT-GHY-FUEL",
        "cargo_item_id": "INV-GHY-DIESEL",
        "quantity": 10000.0,
        "expected_arrival_day": 5,
        "transit_duration_days": 2,
        "route_id": "GHY-TEZ",
        "status": "SCHEDULED",
        "data_source": "synthetic_demo"
    }
]

def get_synthetic_shipments(
    depot_id: Optional[str] = None,
    cargo_item_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Returns deterministic synthetic replenishment shipment records.
    Optionally filtered by destination depot_id or cargo_item_id.
    Does NOT mutate any database tables.
    """
    shipments = [dict(s) for s in SYNTHETIC_REPLENISHMENT_SHIPMENTS]
    if depot_id:
        shipments = [s for s in shipments if s["destination_depot_id"] == depot_id]
    if cargo_item_id:
        shipments = [s for s in shipments if s["cargo_item_id"] == cargo_item_id]
    return shipments

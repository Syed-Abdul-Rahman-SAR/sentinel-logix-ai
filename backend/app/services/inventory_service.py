import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from ..db.database import get_db
from ..schemas.inventory import InventoryItemCreate, InventoryItemUpdate

class InventoryService:
    @staticmethod
    def create_inventory_item(data: InventoryItemCreate, db_path: str = None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        item_id = f"INV-{uuid.uuid4().hex[:6].upper()}"

        # Validation: current_quantity cannot exceed maximum_capacity
        if data.current_quantity > data.maximum_capacity:
            raise HTTPException(
                status_code=400,
                detail=f"current_quantity ({data.current_quantity}) cannot exceed maximum_capacity ({data.maximum_capacity})"
            )

        with get_db(db_path) as conn:
            cursor = conn.cursor()
            
            # Verify depot_id exists
            cursor.execute("SELECT id FROM depots WHERE id = ?", (data.depot_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=400, detail=f"Parent Depot '{data.depot_id}' not found")

            cursor.execute("""
            INSERT INTO inventory_items 
            (id, depot_id, item_name, category, unit, current_quantity, minimum_threshold, maximum_capacity, daily_consumption_rate, criticality, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item_id,
                data.depot_id,
                data.item_name,
                data.category,
                data.unit,
                data.current_quantity,
                data.minimum_threshold,
                data.maximum_capacity,
                data.daily_consumption_rate,
                data.criticality,
                now
            ))

            cursor.execute("SELECT * FROM inventory_items WHERE id = ?", (item_id,))
            return dict(cursor.fetchone())

    @staticmethod
    def get_inventory_item(item_id: str, db_path: str = None) -> Dict[str, Any]:
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM inventory_items WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"Inventory item '{item_id}' not found")
            return dict(row)

    @staticmethod
    def list_inventory(depot_id: Optional[str] = None, category: Optional[str] = None, criticality: Optional[str] = None, db_path: str = None) -> List[Dict[str, Any]]:
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM inventory_items WHERE 1=1"
            params = []
            if depot_id:
                query += " AND depot_id = ?"
                params.append(depot_id)
            if category:
                query += " AND category = ?"
                params.append(category.upper())
            if criticality:
                query += " AND criticality = ?"
                params.append(criticality.upper())
            query += " ORDER BY item_name ASC"
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def update_inventory_item(item_id: str, data: InventoryItemUpdate, db_path: str = None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM inventory_items WHERE id = ?", (item_id,))
            existing = cursor.fetchone()
            if not existing:
                raise HTTPException(status_code=404, detail=f"Inventory item '{item_id}' not found")

            existing_dict = dict(existing)
            new_qty = data.current_quantity if data.current_quantity is not None else existing_dict["current_quantity"]
            new_max = data.maximum_capacity if data.maximum_capacity is not None else existing_dict["maximum_capacity"]

            if new_qty > new_max:
                raise HTTPException(
                    status_code=400,
                    detail=f"Updated current_quantity ({new_qty}) cannot exceed maximum_capacity ({new_max})"
                )

            updates = []
            params = []

            if data.depot_id is not None:
                cursor.execute("SELECT id FROM depots WHERE id = ?", (data.depot_id,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=400, detail=f"Parent Depot '{data.depot_id}' not found")
                updates.append("depot_id = ?")
                params.append(data.depot_id)

            if data.item_name is not None:
                updates.append("item_name = ?")
                params.append(data.item_name)
            if data.category is not None:
                updates.append("category = ?")
                params.append(data.category)
            if data.unit is not None:
                updates.append("unit = ?")
                params.append(data.unit)
            if data.current_quantity is not None:
                updates.append("current_quantity = ?")
                params.append(data.current_quantity)
            if data.minimum_threshold is not None:
                updates.append("minimum_threshold = ?")
                params.append(data.minimum_threshold)
            if data.maximum_capacity is not None:
                updates.append("maximum_capacity = ?")
                params.append(data.maximum_capacity)
            if data.daily_consumption_rate is not None:
                updates.append("daily_consumption_rate = ?")
                params.append(data.daily_consumption_rate)
            if data.criticality is not None:
                updates.append("criticality = ?")
                params.append(data.criticality)

            if updates:
                updates.append("last_updated = ?")
                params.append(now)
                params.append(item_id)
                cursor.execute(f"UPDATE inventory_items SET {', '.join(updates)} WHERE id = ?", params)

            cursor.execute("SELECT * FROM inventory_items WHERE id = ?", (item_id,))
            return dict(cursor.fetchone())

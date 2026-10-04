from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from ..db.database import get_db
from ..schemas.consumption import ConsumptionRecordCreate

class ConsumptionService:
    @staticmethod
    def create_record(data: ConsumptionRecordCreate, db_path: str = None) -> Dict[str, Any]:
        with get_db(db_path) as conn:
            cursor = conn.cursor()

            # Verify depot_id exists
            cursor.execute("SELECT id FROM depots WHERE id = ?", (data.depot_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=400, detail=f"Depot '{data.depot_id}' not found")

            # Verify inventory_item_id exists and matches depot_id
            cursor.execute("SELECT id, depot_id FROM inventory_items WHERE id = ?", (data.inventory_item_id,))
            item = cursor.fetchone()
            if not item:
                raise HTTPException(status_code=400, detail=f"Inventory Item '{data.inventory_item_id}' not found")
            if item["depot_id"] != data.depot_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Inventory Item '{data.inventory_item_id}' belongs to depot '{item['depot_id']}', not '{data.depot_id}'"
                )

            cursor.execute("""
            INSERT INTO consumption_history (depot_id, inventory_item_id, quantity_consumed, consumption_date, operational_intensity)
            VALUES (?, ?, ?, ?, ?)
            """, (
                data.depot_id,
                data.inventory_item_id,
                data.quantity_consumed,
                data.consumption_date,
                data.operational_intensity
            ))

            rec_id = cursor.lastrowid
            cursor.execute("SELECT * FROM consumption_history WHERE id = ?", (rec_id,))
            return dict(cursor.fetchone())

    @staticmethod
    def list_records(
        inventory_item_id: Optional[str] = None,
        depot_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        db_path: str = None
    ) -> List[Dict[str, Any]]:
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM consumption_history WHERE 1=1"
            params = []

            if inventory_item_id:
                query += " AND inventory_item_id = ?"
                params.append(inventory_item_id)
            if depot_id:
                query += " AND depot_id = ?"
                params.append(depot_id)
            if start_date:
                query += " AND consumption_date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND consumption_date <= ?"
                params.append(end_date)

            query += " ORDER BY consumption_date DESC, id DESC"
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from ..db.database import get_db
from ..schemas.depot import DepotCreate, DepotUpdate

class DepotService:
    @staticmethod
    def create_depot(data: DepotCreate, db_path: str = None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        depot_id = f"DEPOT-{uuid.uuid4().hex[:6].upper()}"

        with get_db(db_path) as conn:
            cursor = conn.cursor()
            
            # Verify base_id exists
            cursor.execute("SELECT id FROM bases WHERE id = ?", (data.base_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=400, detail=f"Parent Base '{data.base_id}' not found")

            cursor.execute("""
            INSERT INTO depots (id, base_id, name, depot_type, storage_capacity, status, latitude, longitude, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                depot_id,
                data.base_id,
                data.name,
                data.depot_type,
                data.storage_capacity,
                data.status,
                data.latitude,
                data.longitude,
                now,
                now
            ))

            cursor.execute("SELECT * FROM depots WHERE id = ?", (depot_id,))
            return dict(cursor.fetchone())

    @staticmethod
    def get_depot(depot_id: str, db_path: str = None) -> Dict[str, Any]:
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM depots WHERE id = ?", (depot_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"Depot '{depot_id}' not found")
            return dict(row)

    @staticmethod
    def list_depots(base_id: Optional[str] = None, depot_type: Optional[str] = None, db_path: str = None) -> List[Dict[str, Any]]:
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM depots WHERE 1=1"
            params = []
            if base_id:
                query += " AND base_id = ?"
                params.append(base_id)
            if depot_type:
                query += " AND depot_type = ?"
                params.append(depot_type.upper())
            query += " ORDER BY name ASC"
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def update_depot(depot_id: str, data: DepotUpdate, db_path: str = None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM depots WHERE id = ?", (depot_id,))
            existing = cursor.fetchone()
            if not existing:
                raise HTTPException(status_code=404, detail=f"Depot '{depot_id}' not found")

            updates = []
            params = []

            if data.base_id is not None:
                cursor.execute("SELECT id FROM bases WHERE id = ?", (data.base_id,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=400, detail=f"Parent Base '{data.base_id}' not found")
                updates.append("base_id = ?")
                params.append(data.base_id)

            if data.name is not None:
                updates.append("name = ?")
                params.append(data.name)
            if data.depot_type is not None:
                updates.append("depot_type = ?")
                params.append(data.depot_type)
            if data.storage_capacity is not None:
                updates.append("storage_capacity = ?")
                params.append(data.storage_capacity)
            if data.status is not None:
                updates.append("status = ?")
                params.append(data.status)
            if data.latitude is not None:
                updates.append("latitude = ?")
                params.append(data.latitude)
            if data.longitude is not None:
                updates.append("longitude = ?")
                params.append(data.longitude)

            if updates:
                updates.append("updated_at = ?")
                params.append(now)
                params.append(depot_id)
                cursor.execute(f"UPDATE depots SET {', '.join(updates)} WHERE id = ?", params)

            cursor.execute("SELECT * FROM depots WHERE id = ?", (depot_id,))
            return dict(cursor.fetchone())

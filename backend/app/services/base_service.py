import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from ..db.database import get_db
from ..schemas.base import BaseCreate, BaseUpdate

class BaseService:
    @staticmethod
    def create_base(data: BaseCreate, db_path: str = None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        base_id = f"BASE-{uuid.uuid4().hex[:6].upper()}"

        with get_db(db_path) as conn:
            cursor = conn.cursor()
            
            # Check road_node_id if provided
            if data.road_node_id:
                cursor.execute("SELECT id FROM road_nodes WHERE id = ?", (data.road_node_id,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=400, detail=f"Referenced road_node_id '{data.road_node_id}' does not exist")

            cursor.execute("""
            INSERT INTO bases (id, name, base_type, latitude, longitude, capacity, status, description, road_node_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                base_id,
                data.name,
                data.base_type,
                data.latitude,
                data.longitude,
                data.capacity,
                data.status,
                data.description,
                data.road_node_id,
                now,
                now
            ))

            cursor.execute("SELECT * FROM bases WHERE id = ?", (base_id,))
            return dict(cursor.fetchone())

    @staticmethod
    def get_base(base_id: str, db_path: str = None) -> Dict[str, Any]:
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM bases WHERE id = ?", (base_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"Base '{base_id}' not found")
            return dict(row)

    @staticmethod
    def list_bases(base_type: Optional[str] = None, status: Optional[str] = None, db_path: str = None) -> List[Dict[str, Any]]:
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM bases WHERE 1=1"
            params = []
            if base_type:
                query += " AND base_type = ?"
                params.append(base_type.upper())
            if status:
                query += " AND status = ?"
                params.append(status.upper())
            query += " ORDER BY name ASC"
            cursor.execute(query, params)
            return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def update_base(base_id: str, data: BaseUpdate, db_path: str = None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM bases WHERE id = ?", (base_id,))
            existing = cursor.fetchone()
            if not existing:
                raise HTTPException(status_code=404, detail=f"Base '{base_id}' not found")

            updates = []
            params = []

            if data.name is not None:
                updates.append("name = ?")
                params.append(data.name)
            if data.base_type is not None:
                updates.append("base_type = ?")
                params.append(data.base_type)
            if data.latitude is not None:
                updates.append("latitude = ?")
                params.append(data.latitude)
            if data.longitude is not None:
                updates.append("longitude = ?")
                params.append(data.longitude)
            if data.capacity is not None:
                updates.append("capacity = ?")
                params.append(data.capacity)
            if data.status is not None:
                updates.append("status = ?")
                params.append(data.status)
            if data.description is not None:
                updates.append("description = ?")
                params.append(data.description)
            if data.road_node_id is not None:
                cursor.execute("SELECT id FROM road_nodes WHERE id = ?", (data.road_node_id,))
                if not cursor.fetchone():
                    raise HTTPException(status_code=400, detail=f"Referenced road_node_id '{data.road_node_id}' does not exist")
                updates.append("road_node_id = ?")
                params.append(data.road_node_id)

            if updates:
                updates.append("updated_at = ?")
                params.append(now)
                params.append(base_id)
                cursor.execute(f"UPDATE bases SET {', '.join(updates)} WHERE id = ?", params)

            cursor.execute("SELECT * FROM bases WHERE id = ?", (base_id,))
            return dict(cursor.fetchone())

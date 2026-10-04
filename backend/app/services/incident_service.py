import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import HTTPException
from ..db.database import get_db
from ..schemas.incident import IncidentCreate
from ..websocket.connection_manager import manager

class IncidentService:
    @staticmethod
    async def create_incident(data: IncidentCreate, db_path: str = None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        incident_id = f"INC-{uuid.uuid4().hex[:6].upper()}"
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO incidents 
            (id, type, severity, title, description, latitude, longitude, road_name, is_active, reported_by, reported_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (
                incident_id,
                data.type,
                data.severity,
                data.title,
                data.description,
                data.latitude,
                data.longitude,
                data.road_name,
                data.reported_by,
                now
            ))
            cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
            row = cursor.fetchone()
            incident_data = dict(row)

        # Broadcast incident to all dashboards and drivers
        await manager.broadcast_to_dashboards({
            "type": "INCIDENT_REPORTED",
            "incident": incident_data
        })
        return incident_data

    @staticmethod
    def list_incidents(is_active: Optional[bool] = None, db_path: str = None) -> List[Dict[str, Any]]:
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            if is_active is not None:
                cursor.execute("SELECT * FROM incidents WHERE is_active = ? ORDER BY reported_at DESC", (1 if is_active else 0,))
            else:
                cursor.execute("SELECT * FROM incidents ORDER BY reported_at DESC")
            return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    async def resolve_incident(incident_id: str, db_path: str = None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
            inc = cursor.fetchone()
            if not inc:
                raise HTTPException(status_code=404, detail="Incident not found")
            cursor.execute("UPDATE incidents SET is_active = 0, resolved_at = ? WHERE id = ?", (now, incident_id))
            cursor.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,))
            updated = dict(cursor.fetchone())

        await manager.broadcast_to_dashboards({
            "type": "INCIDENT_RESOLVED",
            "incident_id": incident_id
        })
        return updated

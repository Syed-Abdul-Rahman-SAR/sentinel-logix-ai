import logging
import json
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger("nerlink.websocket")

class ConnectionManager:
    def __init__(self):
        # Set of active dashboard connections
        self.dashboard_connections: Set[WebSocket] = set()
        # Mapping vehicle_id -> Set of driver WebSocket connections
        self.driver_connections: Dict[str, Set[WebSocket]] = {}

    async def connect_dashboard(self, websocket: WebSocket):
        await websocket.accept()
        self.dashboard_connections.add(websocket)
        logger.info(f"Dashboard client connected. Total dashboards: {len(self.dashboard_connections)}")

    def disconnect_dashboard(self, websocket: WebSocket):
        self.dashboard_connections.discard(websocket)
        logger.info(f"Dashboard client disconnected. Total dashboards: {len(self.dashboard_connections)}")

    async def connect_driver(self, vehicle_id: str, websocket: WebSocket):
        await websocket.accept()
        if vehicle_id not in self.driver_connections:
            self.driver_connections[vehicle_id] = set()
        self.driver_connections[vehicle_id].add(websocket)
        logger.info(f"Driver client connected for {vehicle_id}. Active driver sockets: {len(self.driver_connections[vehicle_id])}")

    def disconnect_driver(self, vehicle_id: str, websocket: WebSocket):
        if vehicle_id in self.driver_connections:
            self.driver_connections[vehicle_id].discard(websocket)
            if not self.driver_connections[vehicle_id]:
                del self.driver_connections[vehicle_id]
        logger.info(f"Driver client disconnected for {vehicle_id}.")

    async def broadcast_to_dashboards(self, message: dict):
        """Broadcast JSON payload to all connected dashboard clients."""
        if not self.dashboard_connections:
            return
        payload = json.dumps(message)
        dead_connections = set()
        for ws in list(self.dashboard_connections):
            try:
                await ws.send_text(payload)
            except Exception as e:
                logger.warning(f"Error broadcasting to dashboard, scheduling removal: {e}")
                dead_connections.add(ws)
        for dead in dead_connections:
            self.dashboard_connections.discard(dead)

    async def send_to_driver(self, vehicle_id: str, message: dict):
        """Send direct payload to active driver connections for a vehicle."""
        if vehicle_id not in self.driver_connections:
            return
        payload = json.dumps(message)
        dead_connections = set()
        for ws in list(self.driver_connections[vehicle_id]):
            try:
                await ws.send_text(payload)
            except Exception as e:
                logger.warning(f"Error sending to driver {vehicle_id}: {e}")
                dead_connections.add(ws)
        for dead in dead_connections:
            self.driver_connections[vehicle_id].discard(dead)

manager = ConnectionManager()

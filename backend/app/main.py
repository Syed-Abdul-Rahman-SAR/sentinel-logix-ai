import asyncio
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .config import BASE_DIR
from .db.seed import seed_database
from .api import trips, locations, vehicles, incidents, bases, depots, inventory, consumption, stockout, risk, readiness, digital_twin, intelligence, environment, advisor
from .websocket.connection_manager import manager
from .services.tracking_service import TrackingService
from .schemas.location import LocationTelemetry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("nerlink.main")

app = FastAPI(
    title="NER-LINK / SENTINEL LOGIX AI Core",
    description="North East Region Logistics & Accessibility Intelligence Network - Telemetry, Supply & Routing Engine",
    version="1.1.0"
)

# Enable CORS for local dev and cross-device testing on LAN
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(trips.router)
app.include_router(locations.router)
app.include_router(vehicles.router)
app.include_router(incidents.router)
app.include_router(bases.router)
app.include_router(depots.router)
app.include_router(inventory.router)
app.include_router(consumption.router)
app.include_router(stockout.router)
app.include_router(risk.router)
app.include_router(readiness.router)
app.include_router(digital_twin.router)
app.include_router(intelligence.router)
app.include_router(environment.router)
app.include_router(advisor.router)

# Stale vehicle detector background loop
stale_check_task = None

async def stale_vehicle_monitor_loop():
    logger.info("Starting background stale vehicle detector loop...")
    while True:
        try:
            await asyncio.sleep(10.0)
            await TrackingService.check_and_broadcast_stale_vehicles()
        except asyncio.CancelledError:
            logger.info("Stale vehicle monitor loop cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in stale vehicle monitor: {e}", exc_info=True)

@app.on_event("startup")
async def on_startup():
    global stale_check_task
    logger.info("Initializing database and baseline seeds...")
    seed_database()
    stale_check_task = asyncio.create_task(stale_vehicle_monitor_loop())
    logger.info("NER-LINK AI Core successfully started.")

@app.on_event("shutdown")
async def on_shutdown():
    global stale_check_task
    if stale_check_task:
        stale_check_task.cancel()
        try:
            await stale_check_task
        except asyncio.CancelledError:
            pass
    logger.info("NER-LINK AI Core shutdown complete.")

@app.get("/api/health", tags=["Health"])
def health():
    return {
        "status": "HEALTHY",
        "system": "NER-LINK AI Logistics Intelligence Engine",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_dashboard_connections": len(manager.dashboard_connections),
        "active_driver_connections": sum(len(conns) for conns in manager.driver_connections.values())
    }

# ==========================================
# WebSocket Endpoints
# ==========================================

@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """WebSocket endpoint for control room dashboards. Receives real-time telemetry, incidents, and stale alerts."""
    await manager.connect_dashboard(websocket)
    try:
        # On connection, immediately push the current snapshot of all vehicles
        snapshot = TrackingService.get_latest_states()
        await websocket.send_json({
            "type": "FLEET_SNAPSHOT",
            "vehicles": snapshot
        })
        
        while True:
            # Keep socket open and listen for ping/client requests
            msg_text = await websocket.receive_text()
            if msg_text == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect_dashboard(websocket)
    except Exception as e:
        logger.warning(f"Dashboard websocket exception: {e}")
        manager.disconnect_dashboard(websocket)


@app.websocket("/ws/driver/{vehicle_id}")
async def websocket_driver(websocket: WebSocket, vehicle_id: str):
    """WebSocket endpoint for driver client. Accepts streaming GPS telemetry with instant bi-directional feedback."""
    await manager.connect_driver(vehicle_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            # Process incoming telemetry
            try:
                # Inject vehicle_id from route if not provided
                data["vehicle_id"] = vehicle_id
                if "recorded_at" not in data:
                    data["recorded_at"] = datetime.now(timezone.utc).isoformat()
                
                telemetry = LocationTelemetry(**data)
                result = await TrackingService.process_telemetry(telemetry)
                
                # Send ACK to driver
                await websocket.send_json({
                    "type": "TELEMETRY_ACK",
                    "recorded_at": telemetry.recorded_at,
                    "received_at": result["received_at"],
                    "status": "PERSISTED"
                })
            except Exception as ex:
                await websocket.send_json({
                    "type": "ERROR",
                    "message": str(ex)
                })
    except WebSocketDisconnect:
        manager.disconnect_driver(vehicle_id, websocket)
    except Exception as e:
        logger.warning(f"Driver websocket {vehicle_id} exception: {e}")
        manager.disconnect_driver(vehicle_id, websocket)

# ==========================================
# Static Files & Dashboard Mounting
# ==========================================
from fastapi.responses import FileResponse

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

if (ROOT_DIR / "css").exists():
    app.mount("/css", StaticFiles(directory=str(ROOT_DIR / "css")), name="css")
if (ROOT_DIR / "js").exists():
    app.mount("/js", StaticFiles(directory=str(ROOT_DIR / "js")), name="js")
if (ROOT_DIR / "driver-client").exists():
    app.mount("/driver-client", StaticFiles(directory=str(ROOT_DIR / "driver-client"), html=True), name="driver-client")

@app.get("/", include_in_schema=False)
async def serve_dashboard():
    index_path = ROOT_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "NER-LINK AI Core Backend Active"}


import os
import sqlite3
import math
from contextlib import contextmanager
from typing import Generator
from ..config import DB_PATH

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Great Circle distance between two points in km."""
    try:
        r = 6371.0  # Earth radius in kilometers
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = (math.sin(delta_phi / 2.0) ** 2 +
             math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return round(r * c, 3)
    except Exception:
        return 0.0

def get_connection(db_path: str = None) -> sqlite3.Connection:
    """Create and configure a SQLite connection with WAL mode and custom math functions."""
    path = db_path or os.getenv("NERLINK_DB_PATH") or DB_PATH
    conn = sqlite3.connect(path, check_same_thread=False, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.create_function("haversine_distance", 4, haversine_km)
    return conn

@contextmanager
def get_db(db_path: str = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite database transactions."""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db(db_path: str = None):
    """Initialize database tables, constraints, and indexes."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        
        # 1. Drivers
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS drivers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            license_no TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        );
        """)

        # 2. Vehicles
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicles (
            id TEXT PRIMARY KEY,
            plate_number TEXT NOT NULL UNIQUE,
            vehicle_type TEXT NOT NULL,
            capacity_tons REAL NOT NULL DEFAULT 5.0,
            fuel_type TEXT DEFAULT 'DIESEL',
            status TEXT DEFAULT 'IDLE',
            created_at TEXT NOT NULL
        );
        """)

        # 3. Trips
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id TEXT PRIMARY KEY,
            vehicle_id TEXT NOT NULL,
            driver_id TEXT NOT NULL,
            origin_node TEXT NOT NULL,
            dest_node TEXT NOT NULL,
            cargo_type TEXT NOT NULL,
            cargo_weight_tons REAL NOT NULL,
            status TEXT DEFAULT 'ACTIVE',
            start_time TEXT NOT NULL,
            end_time TEXT,
            total_distance_km REAL DEFAULT 0.0,
            FOREIGN KEY(vehicle_id) REFERENCES vehicles(id),
            FOREIGN KEY(driver_id) REFERENCES drivers(id)
        );
        """)

        # 4. Vehicle Locations (Full audit trail & telemetry time series)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS vehicle_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id TEXT,
            vehicle_id TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            altitude REAL,
            speed_kmh REAL DEFAULT 0.0,
            heading REAL DEFAULT 0.0,
            accuracy_meters REAL DEFAULT 10.0,
            battery_pct REAL,
            network_status TEXT DEFAULT 'ONLINE',
            recorded_at TEXT NOT NULL,
            received_at TEXT NOT NULL,
            FOREIGN KEY(trip_id) REFERENCES trips(id),
            FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
        );
        """)

        # 5. Latest Vehicle States (O(1) dashboard snapshot cache table)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS latest_vehicle_states (
            vehicle_id TEXT PRIMARY KEY,
            trip_id TEXT,
            driver_id TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            altitude REAL,
            speed_kmh REAL DEFAULT 0.0,
            heading REAL DEFAULT 0.0,
            accuracy_meters REAL DEFAULT 10.0,
            battery_pct REAL,
            network_status TEXT DEFAULT 'ONLINE',
            status TEXT DEFAULT 'ONLINE',
            recorded_at TEXT NOT NULL,
            received_at TEXT NOT NULL,
            FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
        );
        """)

        # 6. Incidents & Obstacles (Road blocks, landslides, floods, maintenance)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            road_name TEXT,
            is_active INTEGER DEFAULT 1,
            reported_by TEXT,
            reported_at TEXT NOT NULL,
            resolved_at TEXT
        );
        """)

        # 7. Road Network Nodes (NER topological graph)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS road_nodes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            state TEXT NOT NULL
        );
        """)

        # 8. Road Network Segments
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS road_segments (
            id TEXT PRIMARY KEY,
            source_node TEXT NOT NULL,
            target_node TEXT NOT NULL,
            distance_km REAL NOT NULL,
            base_speed_kmh REAL NOT NULL,
            elevation_gain_m REAL DEFAULT 0,
            road_quality TEXT DEFAULT 'GOOD',
            is_blocked INTEGER DEFAULT 0,
            FOREIGN KEY(source_node) REFERENCES road_nodes(id),
            FOREIGN KEY(target_node) REFERENCES road_nodes(id)
        );
        """)

        # 9. Bases (SENTINEL Operational Logistics Base)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bases (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            base_type TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            capacity REAL DEFAULT 100.0,
            status TEXT DEFAULT 'OPERATIONAL',
            description TEXT,
            road_node_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(road_node_id) REFERENCES road_nodes(id)
        );
        """)

        # 10. Depots (SENTINEL Storage & Distribution Facility)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS depots (
            id TEXT PRIMARY KEY,
            base_id TEXT NOT NULL,
            name TEXT NOT NULL,
            depot_type TEXT NOT NULL,
            storage_capacity REAL NOT NULL DEFAULT 1000.0,
            status TEXT DEFAULT 'OPERATIONAL',
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(base_id) REFERENCES bases(id)
        );
        """)

        # 11. Inventory Items (SENTINEL Stock Position)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory_items (
            id TEXT PRIMARY KEY,
            depot_id TEXT NOT NULL,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            unit TEXT NOT NULL,
            current_quantity REAL NOT NULL DEFAULT 0.0,
            minimum_threshold REAL NOT NULL DEFAULT 0.0,
            maximum_capacity REAL NOT NULL DEFAULT 1000.0,
            daily_consumption_rate REAL NOT NULL DEFAULT 0.0,
            criticality TEXT DEFAULT 'MEDIUM',
            last_updated TEXT NOT NULL,
            FOREIGN KEY(depot_id) REFERENCES depots(id)
        );
        """)

        # 12. Consumption History (SENTINEL Historical Demand Dataset)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS consumption_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            depot_id TEXT NOT NULL,
            inventory_item_id TEXT NOT NULL,
            quantity_consumed REAL NOT NULL,
            consumption_date TEXT NOT NULL,
            operational_intensity TEXT DEFAULT 'NORMAL',
            FOREIGN KEY(depot_id) REFERENCES depots(id),
            FOREIGN KEY(inventory_item_id) REFERENCES inventory_items(id)
        );
        """)

        # Indexes for fast querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_loc_vehicle ON vehicle_locations(vehicle_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_loc_trip ON vehicle_locations(trip_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_loc_recorded ON vehicle_locations(recorded_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_latest_status ON latest_vehicle_states(status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_latest_received ON latest_vehicle_states(received_at);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trips_vehicle ON trips(vehicle_id, status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_incidents_active ON incidents(is_active);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bases_type ON bases(base_type);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_depots_base ON depots(base_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_depot ON inventory_items(depot_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_category ON inventory_items(category);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_consumption_item ON consumption_history(inventory_item_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_consumption_date ON consumption_history(consumption_date);")

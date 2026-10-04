from datetime import datetime, timezone
from .database import get_db, init_db

NODES_SEED = [
    ("GHY", "Guwahati", 26.1445, 91.7362, "Assam"),
    ("SHL", "Shillong", 25.5788, 91.8933, "Meghalaya"),
    ("TEZ", "Tezpur", 26.6528, 92.7926, "Assam"),
    ("JOR", "Jorhat", 26.7509, 94.2037, "Assam"),
    ("DBR", "Dibrugarh", 27.4728, 94.9120, "Assam"),
    ("SIL", "Silchar", 24.8333, 92.7789, "Assam"),
    ("AGT", "Agartala", 23.8315, 91.2868, "Tripura"),
    ("IMP", "Imphal", 24.8170, 93.9368, "Manipur"),
    ("KHM", "Kohima", 25.6751, 94.1086, "Nagaland"),
    ("DMA", "Dimapur", 25.9090, 93.7266, "Nagaland"),
    ("ITN", "Itanagar", 27.0844, 93.6053, "Arunachal Pradesh"),
    ("TWA", "Tawang", 27.5861, 91.8594, "Arunachal Pradesh"),
    ("AIZ", "Aizawl", 23.7271, 92.7176, "Mizoram"),
    ("GXT", "Gangtok", 27.3389, 88.6065, "Sikkim")
]

SEGMENTS_SEED = [
    ("GHY-SHL", "GHY", "SHL", 100.0, 45.0, 1400.0, "EXCELLENT", 0),
    ("SHL-GHY", "SHL", "GHY", 100.0, 50.0, -1400.0, "EXCELLENT", 0),
    ("GHY-TEZ", "GHY", "TEZ", 175.0, 60.0, 50.0, "GOOD", 0),
    ("TEZ-GHY", "TEZ", "GHY", 175.0, 60.0, -50.0, "GOOD", 0),
    ("TEZ-JOR", "TEZ", "JOR", 160.0, 55.0, 60.0, "GOOD", 0),
    ("JOR-TEZ", "JOR", "TEZ", 160.0, 55.0, -60.0, "GOOD", 0),
    ("JOR-DBR", "JOR", "DBR", 135.0, 60.0, 20.0, "EXCELLENT", 0),
    ("DBR-JOR", "DBR", "JOR", 135.0, 60.0, -20.0, "EXCELLENT", 0),
    ("SHL-SIL", "SHL", "SIL", 215.0, 35.0, -1200.0, "FAIR", 0),
    ("SIL-SHL", "SIL", "SHL", 215.0, 32.0, 1200.0, "FAIR", 0),
    ("SIL-AGT", "SIL", "AGT", 250.0, 40.0, -80.0, "GOOD", 0),
    ("AGT-SIL", "AGT", "SIL", 250.0, 40.0, 80.0, "GOOD", 0),
    ("SIL-IMP", "SIL", "IMP", 255.0, 30.0, 700.0, "POOR", 0),
    ("IMP-SIL", "IMP", "SIL", 255.0, 30.0, -700.0, "POOR", 0),
    ("DMA-KHM", "DMA", "KHM", 74.0, 28.0, 1200.0, "POOR", 0),
    ("KHM-DMA", "KHM", "DMA", 74.0, 35.0, -1200.0, "POOR", 0),
    ("KHM-IMP", "KHM", "IMP", 140.0, 38.0, -600.0, "FAIR", 0),
    ("IMP-KHM", "IMP", "KHM", 140.0, 35.0, 600.0, "FAIR", 0),
    ("JOR-DMA", "JOR", "DMA", 115.0, 50.0, 70.0, "GOOD", 0),
    ("DMA-JOR", "DMA", "JOR", 115.0, 50.0, -70.0, "GOOD", 0),
    ("TEZ-ITN", "TEZ", "ITN", 155.0, 42.0, 350.0, "GOOD", 0),
    ("ITN-TEZ", "ITN", "TEZ", 155.0, 45.0, -350.0, "GOOD", 0),
    ("TEZ-TWA", "TEZ", "TWA", 320.0, 25.0, 2800.0, "POOR", 0),
    ("TWA-TEZ", "TWA", "TEZ", 320.0, 28.0, -2800.0, "POOR", 0),
    ("SIL-AIZ", "SIL", "AIZ", 180.0, 32.0, 950.0, "FAIR", 0),
    ("AIZ-SIL", "AIZ", "SIL", 180.0, 35.0, -950.0, "FAIR", 0)
]

DRIVERS_SEED = [
    ("D-01", "Biren Gogoi", "+919435011223", "AS-01-2018-0091"),
    ("D-02", "Tenzing Norbu", "+919862044556", "ML-05-2019-0442"),
    ("D-03", "Debashish Roy", "+919774077889", "TR-01-2020-0883"),
    ("D-04", "Lobsang Dorjee", "+919436033221", "AR-02-2021-0129"),
    ("D-05", "Khogen Sharma", "+919856055667", "MN-01-2017-0664")
]

VEHICLES_SEED = [
    ("V-01", "AS-01-EC-4412", "HEAVY_TRUCK", 16.0, "DIESEL", "IDLE"),
    ("V-02", "ML-05-A-8821", "MEDIUM_CARGO", 8.0, "DIESEL", "IDLE"),
    ("V-03", "AS-03-BC-1109", "MED_VAN", 3.5, "DIESEL", "IDLE"),
    ("V-04", "TR-01-X-3390", "FUEL_TANKER", 12.0, "DIESEL", "IDLE"),
    ("V-05", "NL-07-K-7744", "HEAVY_TRUCK", 20.0, "DIESEL", "IDLE")
]

def seed_database(db_path: str = None):
    """Seed initial records if not already populated."""
    init_db(db_path)
    now = datetime.now(timezone.utc).isoformat()
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        
        # Seed nodes
        for node in NODES_SEED:
            cursor.execute("""
            INSERT OR IGNORE INTO road_nodes (id, name, latitude, longitude, state)
            VALUES (?, ?, ?, ?, ?);
            """, node)
            
        # Seed segments
        for seg in SEGMENTS_SEED:
            cursor.execute("""
            INSERT OR IGNORE INTO road_segments (id, source_node, target_node, distance_km, base_speed_kmh, elevation_gain_m, road_quality, is_blocked)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, seg)
            
        # Seed drivers
        for drv in DRIVERS_SEED:
            cursor.execute("""
            INSERT OR IGNORE INTO drivers (id, name, phone, license_no, is_active, created_at)
            VALUES (?, ?, ?, ?, 1, ?);
            """, (*drv, now))
            
        # Seed vehicles
        for veh in VEHICLES_SEED:
            cursor.execute("""
            INSERT OR IGNORE INTO vehicles (id, plate_number, vehicle_type, capacity_tons, fuel_type, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """, (*veh, now))

        # Seed initial latest states for the vehicles so dashboard has positions on cold-start
        initial_states = [
            ("V-01", 26.1445, 91.7362, "GHY", "D-01"),
            ("V-02", 25.5788, 91.8933, "SHL", "D-02"),
            ("V-03", 26.6528, 92.7926, "TEZ", "D-03"),
            ("V-04", 24.8333, 92.7789, "SIL", "D-04"),
            ("V-05", 25.9090, 93.7266, "DMA", "D-05")
        ]
        for vid, lat, lng, node_id, did in initial_states:
            cursor.execute("""
            INSERT OR IGNORE INTO latest_vehicle_states 
            (vehicle_id, trip_id, driver_id, latitude, longitude, altitude, speed_kmh, heading, accuracy_meters, battery_pct, network_status, status, recorded_at, received_at)
            VALUES (?, NULL, ?, ?, ?, 100.0, 0.0, 0.0, 8.0, 95.0, 'ONLINE', 'IDLE', ?, ?);
            """, (vid, did, lat, lng, now, now))

        # Seed sample verified incident (Phase 3 readiness)
        cursor.execute("""
        INSERT OR IGNORE INTO incidents (id, type, severity, title, description, latitude, longitude, road_name, is_active, reported_by, reported_at)
        VALUES ('INC-001', 'LANDSLIDE', 'CRITICAL', 'Barapani Mudslide Hazard', 'Major rockfall & mudslide blocking both lanes on NH-6', 25.6540, 91.9050, 'NH-6 Barapani Bypass', 1, 'NER-Control-Room', ?);
        """, (now,))

        # =========================================================================
        # SENTINEL LOGIX AI SYNTHETIC DEMONSTRATION SEED DATA
        # Note: All records below are synthetic demonstration data for testing.
        # =========================================================================

        # 1. Bases Seed
        bases_seed = [
            ("BASE-GHY", "Guwahati Central Logistics Hub", "LOGISTICS_HUB", 26.1445, 91.7362, 5000.0, "OPERATIONAL", "Primary strategic distribution & multimodal hub for NER operations", "GHY"),
            ("BASE-SHL", "Shillong Forward Support Base", "SUPPORT_BASE", 25.5788, 91.8933, 2500.0, "OPERATIONAL", "Mountain transit support base and medical supply depot", "SHL"),
            ("BASE-IMP", "Imphal Operational Forward Base", "FORWARD_BASE", 24.8170, 93.9368, 1200.0, "LIMITED", "Forward operating logistics base for eastern border sectors", "IMP"),
            ("BASE-TWA", "Tawang High Altitude FOB", "FORWARD_BASE", 27.5861, 91.8594, 800.0, "LIMITED", "High altitude forward operating base subject to weather bottlenecks", "TWA")
        ]
        for b_id, name, b_type, lat, lng, cap, stat, desc, r_node in bases_seed:
            cursor.execute("""
            INSERT OR IGNORE INTO bases (id, name, base_type, latitude, longitude, capacity, status, description, road_node_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (b_id, name, b_type, lat, lng, cap, stat, desc, r_node, now, now))

        # 2. Depots Seed
        depots_seed = [
            ("DEPOT-GHY-FUEL", "BASE-GHY", "Guwahati Strategic Fuel Depot", "FUEL", 50000.0, "OPERATIONAL", 26.1450, 91.7370),
            ("DEPOT-GHY-FOOD", "BASE-GHY", "Guwahati Central Ration Warehouse", "FOOD", 20000.0, "OPERATIONAL", 26.1440, 91.7350),
            ("DEPOT-SHL-MED",  "BASE-SHL", "Shillong Tactical Medical Depot", "MEDICAL", 5000.0, "OPERATIONAL", 25.5790, 91.8940),
            ("DEPOT-IMP-SUP",  "BASE-IMP", "Imphal General Supply Depot", "GENERAL_SUPPLY", 10000.0, "LIMITED", 24.8175, 93.9370),
            ("DEPOT-TWA-AMM",  "BASE-TWA", "Tawang High Altitude Munitions Depot", "AMMUNITION", 3000.0, "LIMITED", 27.5865, 91.8600)
        ]
        for d_id, b_id, name, d_type, cap, stat, lat, lng in depots_seed:
            cursor.execute("""
            INSERT OR IGNORE INTO depots (id, base_id, name, depot_type, storage_capacity, status, latitude, longitude, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (d_id, b_id, name, d_type, cap, stat, lat, lng, now, now))

        # 3. Inventory Items Seed (Scenarios: Healthy, Watch, Critical)
        inventory_seed = [
            # Healthy depot
            ("INV-GHY-DIESEL", "DEPOT-GHY-FUEL", "Ultra-Low Sulfur Diesel Fuel", "FUEL", "LITERS", 38000.0, 10000.0, 50000.0, 1200.0, "CRITICAL"),
            ("INV-GHY-RATIONS", "DEPOT-GHY-FOOD", "Dry Grain & Packaged Rations", "FOOD", "KG", 14500.0, 4000.0, 20000.0, 650.0, "MEDIUM"),
            # Watch depot (close to threshold)
            ("INV-SHL-MEDKIT", "DEPOT-SHL-MED", "Tactical Trauma Field Kits", "MEDICAL", "BOXES", 650.0, 600.0, 2000.0, 45.0, "CRITICAL"),
            # Critical depots (below threshold!)
            ("INV-IMP-RATIONS", "DEPOT-IMP-SUP", "Operational MRE Rations Pack", "FOOD", "KG", 420.0, 1500.0, 8000.0, 220.0, "HIGH"),
            ("INV-TWA-AVGAS", "DEPOT-TWA-AMM", "Aviation High Altitude Fuel", "FUEL", "LITERS", 2800.0, 3000.0, 10000.0, 350.0, "CRITICAL")
        ]
        for item_id, d_id, name, cat, unit, cur_qty, min_th, max_cap, daily_r, crit in inventory_seed:
            cursor.execute("""
            INSERT OR IGNORE INTO inventory_items (id, depot_id, item_name, category, unit, current_quantity, minimum_threshold, maximum_capacity, daily_consumption_rate, criticality, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (item_id, d_id, name, cat, unit, cur_qty, min_th, max_cap, daily_r, crit, now))

        # 4. Historical Consumption Records Seed (14-day history for demand forecasting input)
        cursor.execute("SELECT COUNT(*) FROM consumption_history")
        if cursor.fetchone()[0] == 0:
            from datetime import timedelta, date
            base_date = date(2026, 10, 1)
            
            consumption_configs = [
                ("DEPOT-GHY-FUEL", "INV-GHY-DIESEL", 1200.0, "NORMAL"),
                ("DEPOT-GHY-FOOD", "INV-GHY-RATIONS", 650.0, "NORMAL"),
                ("DEPOT-SHL-MED",  "INV-SHL-MEDKIT",  50.0,  "HIGH"),
                ("DEPOT-IMP-SUP",  "INV-IMP-RATIONS", 240.0, "HIGH"),
                ("DEPOT-TWA-AMM",  "INV-TWA-AVGAS",   380.0, "CRITICAL")
            ]
            
            for d_id, item_id, base_rate, intensity in consumption_configs:
                for day_offset in range(14, 0, -1):
                    c_date = (base_date - timedelta(days=day_offset)).isoformat()
                    # Slight variation per day for realistic time-series data
                    variance = (day_offset % 3 - 1) * 0.08 * base_rate
                    qty = round(base_rate + variance, 1)
                    cursor.execute("""
                    INSERT INTO consumption_history (depot_id, inventory_item_id, quantity_consumed, consumption_date, operational_intensity)
                    VALUES (?, ?, ?, ?, ?);
                    """, (d_id, item_id, qty, c_date, intensity))

if __name__ == "__main__":
    seed_database()
    print("Database seeded successfully.")

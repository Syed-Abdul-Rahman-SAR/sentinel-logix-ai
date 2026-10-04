import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = os.getenv("NERLINK_DB_PATH", str(BASE_DIR / "nerlink.db"))
STALE_THRESHOLD_SECONDS = int(os.getenv("STALE_THRESHOLD_SECONDS", "45"))
OFFLINE_THRESHOLD_SECONDS = int(os.getenv("OFFLINE_THRESHOLD_SECONDS", "120"))
DEFAULT_HOST = os.getenv("HOST", "127.0.0.1")
DEFAULT_PORT = int(os.getenv("PORT", "8000"))

# NER Geospatial bounding box (covers Assam, Meghalaya, Arunachal, Nagaland, Manipur, Mizoram, Tripura, Sikkim)
NER_BOUNDS = {
    "min_lat": 21.0,
    "max_lat": 30.0,
    "min_lng": 87.5,
    "max_lng": 97.5,
}

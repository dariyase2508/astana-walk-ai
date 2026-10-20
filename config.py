from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
RAW_FILE = DATA_DIR / "raw_osm.json"
CLEAN_FILE = DATA_DIR / "poi_clean.json"

ASTANA_BBOX = (50.99, 71.25, 51.27, 71.65)

USER_AGENT = "AstanaWalkAI-hackathon/1.0 (team Unsurprised; educational project)"

WALK_SPEED_M_MIN = 80.0
DETOUR_FACTOR = 1.3

MIN_RADIUS_M = 600
MAX_RADIUS_M = 5000

TZ_HOURS = 5

FLIGHT_BUFFER_MIN = 90

STALE_DAYS = 45
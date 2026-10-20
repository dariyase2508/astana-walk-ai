"""Общие настройки проекта Astana Walk AI (команда Unsurprised)."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
RAW_FILE = DATA_DIR / "raw_osm.json"
CLEAN_FILE = DATA_DIR / "poi_clean.json"

# Рамка поиска Астаны: юг, запад, север, восток (градусы)
ASTANA_BBOX = (50.99, 71.25, 51.27, 71.65)

USER_AGENT = "AstanaWalkAI-hackathon/1.0 (team Unsurprised; educational project)"

# Пешая ходьба: ~4.8 км/ч = 80 м/мин. Коэффициент "извилистости" улиц.
WALK_SPEED_M_MIN = 80.0
DETOUR_FACTOR = 1.3

MIN_RADIUS_M = 600
MAX_RADIUS_M = 5000

# Астана: UTC+5
TZ_HOURS = 5

# Сколько минут до вылета нужно оставить на дорогу в аэропорт и регистрацию
FLIGHT_BUFFER_MIN = 90

# Данные старше этого срока (дней) помечаются как возможно устаревшие
STALE_DAYS = 45

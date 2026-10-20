"""Географические функции: расстояние, проверка координат, фильтр по радиусу."""
import math

from config import ASTANA_BBOX

EARTH_RADIUS_M = 6371000.0


def haversine_m(lat1, lon1, lat2, lon2):
    """Расстояние по прямой между двумя точками (метры)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def valid_coords(lat, lon):
    """Координаты — настоящие числа в допустимом диапазоне."""
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    if math.isnan(lat) or math.isnan(lon):
        return False
    return -90 <= lat <= 90 and -180 <= lon <= 180


def in_astana_area(lat, lon, margin=0.05):
    """Точка лежит в рамке Астаны (с небольшим запасом)."""
    if not valid_coords(lat, lon):
        return False
    s, w, n, e = ASTANA_BBOX
    return (s - margin) <= float(lat) <= (n + margin) and (w - margin) <= float(lon) <= (e + margin)


def within_radius(pois, lat, lon, radius_m):
    """Список (индекс_POI, расстояние_м) для мест внутри радиуса, ближайшие первыми."""
    out = []
    for i, p in enumerate(pois):
        if not valid_coords(p.get("lat"), p.get("lon")):
            continue
        d = haversine_m(lat, lon, p["lat"], p["lon"])
        if d <= radius_m:
            out.append((i, d))
    out.sort(key=lambda x: x[1])
    return out

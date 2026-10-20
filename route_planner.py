import math
from functools import lru_cache

import requests

from config import DETOUR_FACTOR, USER_AGENT, WALK_SPEED_M_MIN
from geo import haversine_m

OSRM_URL = "https://routing.openstreetmap.de/routed-foot/route/v1/foot"


@lru_cache(maxsize=512)
def _osrm_distance(lat1, lon1, lat2, lon2):
    url = f"{OSRM_URL}/{lon1:.5f},{lat1:.5f};{lon2:.5f},{lat2:.5f}"
    r = requests.get(url, params={"overview": "false"}, headers={"User-Agent": USER_AGENT}, timeout=6)
    r.raise_for_status()
    data = r.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise ValueError("OSRM: маршрут не найден")
    return float(data["routes"][0]["distance"])


def walk_distance(a, b, use_osrm=False):
    if use_osrm:
        try:
            return _osrm_distance(round(a[0], 5), round(a[1], 5), round(b[0], 5), round(b[1], 5)), "osrm"
        except Exception:
            pass
    return haversine_m(a[0], a[1], b[0], b[1]) * DETOUR_FACTOR, "estimate"


def minutes_for(meters):
    return max(1, math.ceil(meters / WALK_SPEED_M_MIN))


def plan_route(start, items, budget_min, use_osrm=False, max_stops=3):
    remaining = list(items)
    stops, legs = [], []
    total = 0
    pos = tuple(start)
    used = set()
    while remaining and len(stops) < max_stops:
        best = None
        for it in remaining:
            d, _ = walk_distance(pos, (it["lat"], it["lon"]), False)
            cost = minutes_for(d) + it["visit_min"]
            if total + cost > budget_min:
                continue
            value = it["score"] - 0.00015 * d + (0.15 if it["category"] not in used else -0.1)
            if best is None or value > best[0]:
                best = (value, it)
        if best is None:
            break
        it = best[1]
        remaining.remove(it)
        d, method = walk_distance(pos, (it["lat"], it["lon"]), use_osrm)
        walk = minutes_for(d)
        if total + walk + it["visit_min"] > budget_min:
            continue
        total += walk + it["visit_min"]
        legs.append({"to": it["id"], "distance_m": round(d, -1), "walk_min": walk, "method": method})
        stops.append(it)
        used.add(it["category"])
        pos = (it["lat"], it["lon"])
    if len(stops) < 2:
        return None
    return {
        "stops": [s["id"] for s in stops],
        "legs": legs,
        "walk_min": sum(l["walk_min"] for l in legs),
        "visit_min": sum(s["visit_min"] for s in stops),
        "total_min": total,
        "budget_min": budget_min,
    }
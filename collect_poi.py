import argparse
import json
import time
from datetime import datetime, timezone

import requests

from config import ASTANA_BBOX, RAW_DIR, RAW_FILE, USER_AGENT

ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

GROUPS = {
    "tourism": ['["tourism"~"^(attraction|museum|gallery|viewpoint|artwork|zoo|aquarium|theme_park)$"]'],
    "food": ['["amenity"~"^(cafe|restaurant|fast_food|food_court)$"]'],
    "amenity_leisure": ['["amenity"~"^(bar|pub|nightclub|cinema|theatre|arts_centre|library|marketplace|fountain)$"]'],
    "parks": ['["leisure"~"^(park|garden|playground|water_park)$"]'],
    "historic_shops": ['["historic"~"^(monument|memorial)$"]', '["shop"="mall"]'],
}


def build_query(filters):
    s, w, n, e = ASTANA_BBOX
    body = "\n".join(f"   nwr{f}({s},{w},{n},{e});" for f in filters)
    return f"[out:json][timeout:120];\n(\n{body}\n);\nout center tags;"


def fetch_group(name, query, retries=3):
    """Скачивает одну группу. Возвращает список элементов или None при неудаче."""
    for attempt in range(1, retries + 1):
        for url in ENDPOINTS:
            try:
                print(f"  [{name}] попытка {attempt}, сервер {url.split('/')[2]} ...")
                r = requests.post(url, data={"data": query}, headers={"User-Agent": USER_AGENT}, timeout=170)
                if r.status_code == 200:
                    return r.json().get("elements", [])
                print(f"  [{name}] HTTP {r.status_code} — сервер занят, пробуем дальше")
            except (requests.RequestException, ValueError) as exc:
                print(f"  [{name}] ошибка сети/данных: {exc.__class__.__name__}")
        wait = 10 * attempt
        print(f"  [{name}] пауза {wait} с перед повтором")
        time.sleep(wait)
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="скачать заново, игнорируя кэш")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    merged, failed = {}, []
    for name, filters in GROUPS.items():
        cache = RAW_DIR / f"{name}.json"
        payload = None
        if cache.exists() and not args.refresh:
            payload = json.loads(cache.read_text(encoding="utf-8"))
            print(f"[{name}] взято из кэша: {len(payload['elements'])} объектов")
        else:
            print(f"[{name}] скачиваем из OpenStreetMap ...")
            elements = fetch_group(name, build_query(filters))
            if elements is None:
                print(f"[{name}] НЕ УДАЛОСЬ скачать. Запустите скрипт позже ещё раз — готовые группы сохранены.")
                failed.append(name)
                continue
            payload = {"fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "elements": elements}
            cache.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            print(f"[{name}] получено {len(elements)} объектов")
            time.sleep(5)
        for el in payload["elements"]:
            el["_fetched_at"] = payload["fetched_at"]
            merged[f"{el.get('type')}/{el.get('id')}"] = el

    if not merged:
        print("Нет данных. Проверьте интернет и запустите снова.")
        return
    RAW_FILE.write_text(json.dumps(list(merged.values()), ensure_ascii=False), encoding="utf-8")
    print(f"\nГотово: {len(merged)} уникальных объектов -> {RAW_FILE}")
    if failed:
        print("Не скачаны группы:", ", ".join(failed), "— повторите запуск.")
    print("Дальше: .\\.venv\\Scripts\\python.exe process_data.py")


if __name__ == "__main__":
    main()
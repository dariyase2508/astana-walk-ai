import json
from collections import Counter
from datetime import datetime, timezone

from categories import CATEGORY_INFO
from config import ASTANA_BBOX, CLEAN_FILE, RAW_FILE
from geo import haversine_m, valid_coords

OSM_LICENSE = "© участники OpenStreetMap, ODbL"


def category_from_tags(tags):
    t = tags
    tour, amen, leis, hist, shop = (t.get(k) for k in ("tourism", "amenity", "leisure", "historic", "shop"))
    if tour == "museum": return "museum"
    if tour == "gallery": return "gallery"
    if tour == "attraction": return "attraction"
    if tour == "viewpoint": return "viewpoint"
    if tour == "artwork": return "artwork"
    if tour in ("zoo", "aquarium"): return "zoo"
    if tour == "theme_park": return "entertainment"
    if amen == "cafe": return "cafe"
    if amen in ("restaurant", "fast_food", "food_court"): return "restaurant"
    if amen in ("bar", "pub", "nightclub"): return "nightlife"
    if amen == "cinema": return "cinema"
    if amen in ("theatre", "arts_centre"): return "culture"
    if amen == "library": return "library"
    if amen == "marketplace": return "market"
    if amen == "fountain": return "attraction"
    if leis in ("park", "garden"): return "park"
    if leis == "playground": return "playground"
    if leis == "water_park": return "entertainment"
    if hist in ("monument", "memorial"): return "monument"
    if shop == "mall": return "mall"
    return None


def element_coords(el):
    if "lat" in el and "lon" in el:
        return el["lat"], el["lon"]
    c = el.get("center") or {}
    return c.get("lat"), c.get("lon")


def build_record(el):
    tags = el.get("tags") or {}
    cat = category_from_tags(tags)
    if cat is None:
        return None
    lat, lon = element_coords(el)
    if not valid_coords(lat, lon):
        return None
    s, w, n, e = ASTANA_BBOX
    if not (s <= lat <= n and w <= lon <= e):
        return None

    name_ru, name_kk, name_en = tags.get("name:ru", ""), tags.get("name:kk", ""), tags.get("name:en", "")
    name = name_ru or tags.get("name", "") or name_en or name_kk
    address = ", ".join(x for x in (tags.get("addr:street"), tags.get("addr:housenumber")) if x)
    if not name:
        if cat != "playground":
            return None
        name = "Детская площадка (без названия)"

    desc_osm = tags.get("description:ru") or tags.get("description") or tags.get("description:en") or ""
    cuisine = tags.get("cuisine", "")
    subcat = tags.get("tourism") or tags.get("amenity") or tags.get("leisure") or tags.get("historic") or tags.get("shop") or ""
    if desc_osm:
        description, desc_source = desc_osm, "osm_description"
    else:
        bits = [CATEGORY_INFO[cat]["ru"]]
        if cuisine:
            bits.append(f"кухня: {cuisine.replace(';', ', ').replace('_', ' ')}")
        if address:
            bits.append(f"адрес: {address}")
        description, desc_source = ", ".join(bits), "generated_from_tags"

    internet = tags.get("internet_access", "")
    power = any(k.startswith("socket") or k in ("power_supply", "charging_station") for k in tags)
    el_type, el_id = el.get("type"), el.get("id")
    kw = [CATEGORY_INFO[cat]["keywords"], subcat, cuisine.replace(";", " ").replace("_", " ")]
    if internet in ("wlan", "wifi", "yes"):
        kw.append("wifi вайфай интернет")

    rec = {
        "id": f"osm/{el_type}/{el_id}",
        "name": name, "name_ru": name_ru, "name_kk": name_kk, "name_en": name_en,
        "lat": round(float(lat), 6), "lon": round(float(lon), 6),
        "category": cat, "subcategory": subcat,
        "description": description, "description_source": desc_source,
        "address": address,
        "opening_hours": tags.get("opening_hours", ""),
        "phone": tags.get("phone") or tags.get("contact:phone") or "",
        "website": tags.get("website") or tags.get("contact:website") or "",
        "wheelchair": tags.get("wheelchair", ""),
        "internet_access": internet,
        "power_supply": True if power else None,
        "fee": tags.get("fee", ""),
        "cuisine": cuisine,
        "source": "OpenStreetMap (Overpass API)",
        "source_url": f"https://www.openstreetmap.org/{el_type}/{el_id}",
        "license": OSM_LICENSE,
        "fetched_at": el.get("_fetched_at", datetime.now(timezone.utc).isoformat(timespec="seconds")),
    }
    rec["search_text"] = " ".join(x for x in [name, name_ru, name_kk, name_en, *kw, desc_osm, address] if x)
    return rec


def richness(rec):
    keys = ("opening_hours", "address", "phone", "website", "wheelchair", "internet_access")
    return sum(bool(rec.get(k)) for k in keys) + (1 if rec["description_source"] == "osm_description" else 0)


def dedupe(records, max_dist_m=60):
    kept = []
    for rec in sorted(records, key=richness, reverse=True):
        dup = False
        for k in kept:
            if k["category"] != rec["category"]:
                continue
            same_name = k["name"].lower().strip() == rec["name"].lower().strip()
            if same_name and haversine_m(k["lat"], k["lon"], rec["lat"], rec["lon"]) <= max_dist_m:
                dup = True
                break
        if not dup:
            kept.append(rec)
    return kept


def process(elements):
    records, skipped = [], 0
    for el in elements:
        rec = build_record(el)
        if rec is None:
            skipped += 1
        else:
            records.append(rec)
    return dedupe(records), skipped


def main():
    if not RAW_FILE.exists():
        print("Нет файла data/raw_osm.json. Сначала запустите collect_poi.py")
        return
    elements = json.loads(RAW_FILE.read_text(encoding="utf-8"))
    clean, skipped = process(elements)
    CLEAN_FILE.write_text(json.dumps(clean, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Сырых объектов: {len(elements)}; отброшено (нет названия/координат/нужной категории): {skipped}")
    print(f"Итоговых POI: {len(clean)} -> {CLEAN_FILE}")
    for cat, n in Counter(r["category"] for r in clean).most_common():
        print(f"  {cat:14s} {n}")
    for field in ("opening_hours", "description_source", "wheelchair", "internet_access"):
        filled = sum(1 for r in clean if r.get(field) and (field != "description_source" or r[field] == "osm_description"))
        print(f"Заполнено «{field}»: {filled} из {len(clean)}")


if __name__ == "__main__":
    main()
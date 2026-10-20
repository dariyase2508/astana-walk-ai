from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

import llm
import route_planner
from categories import FREE_LIKELY, PAID_LIKELY, category_label, idea_text, visit_minutes
from config import (DETOUR_FACTOR, FLIGHT_BUFFER_MIN, MAX_RADIUS_M, MIN_RADIUS_M, STALE_DAYS,
                    TZ_HOURS, WALK_SPEED_M_MIN)
from geo import haversine_m, in_astana_area, within_radius
from hours import check_open
from landmarks import get_landmark
from query_parser import normalize, parse_query
from retrieval import POIIndex

POI, CALC, IDEA, AI, UNKNOWN = "POI", "CALC", "IDEA", "AI", "UNKNOWN"
DEFAULT_CATS = {"park": 1.0, "attraction": 1.0, "viewpoint": 0.8, "monument": 0.6, "museum": 0.6, "artwork": 0.4}
GROUP_BONUS = {"restaurant": 0.15, "park": 0.15, "attraction": 0.15, "viewpoint": 0.1, "entertainment": 0.15, "cafe": 0.05}


def L(lang, ru, en):
    return en if lang == "en" else ru


@dataclass
class Request:
    query: str = ""
    lat: Optional[float] = None
    lon: Optional[float] = None
    minutes: Optional[int] = None
    budget: str = "any"                  # any | free
    interests: list = field(default_factory=list)   # имена категорий
    wheelchair: bool = False
    group_size: Optional[int] = None
    lang: Optional[str] = None                  # ru | en | None (авто)
    now: Optional[datetime] = None
    use_osrm: bool = False
    use_llm: bool = False
    want_route: bool = True
    flight_buffer_min: int = FLIGHT_BUFFER_MIN
    max_results: int = 3


def build_index(pois):
    return POIIndex(pois)


def _fail(result, message):
    result.update(ok=False, message=message, items=[], route=None)
    return result


def _fetched_age_days(fetched_at, now):
    try:
        dt = datetime.fromisoformat(fetched_at)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (now - dt).days
    except (TypeError, ValueError):
        return None


def _completeness(p):
    pts = sum([bool(p.get("opening_hours")), bool(p.get("address")),
                bool(p.get("phone") or p.get("website")), p.get("description_source") == "osm_description"])
    return pts


def _make_item(p, straight, walk_m, method, state, parsed, cat_w, lang, now, score, wheelchair):
    cat = p["category"]
    label = category_label(cat, lang)
    walk_min = route_planner.minutes_for(walk_m)
    visit = visit_minutes(cat)
    why = [(L(lang, f"Категория: {label}", f"Category: {label}"), POI)]
    if parsed.categories.get(cat):
        why.append((L(lang, "Категория соответствует вашему запросу", "Category matches your request"), CALC))
    meth = (L(lang, "маршрут OSRM", "OSRM route") if method == "osrm"
            else L(lang, "оценка: по прямой × 1.3, не точный маршрут", "estimate: straight line × 1.3, not an exact route"))
    why.append((L(lang, f"≈{round(straight, -1):.0f} м по прямой; пешком ≈{walk_min} мин ({meth})",
                  f"≈{round(straight, -1):.0f} m straight line; ≈{walk_min} min on foot ({meth})"), CALC))
    oh = p.get("opening_hours", "")
    if state == "open":
        why.append((L(lang, f"Часы работы (OSM): {oh}; по ним сейчас открыто — это не гарантия",
                      f"Opening hours (OSM): {oh}; open now by these hours — not a guarantee"), POI))
    elif oh:
        why.append((L(lang, f"Часы работы указаны ({oh}), но разобрать их надёжно не удалось — уточните",
                      f"Hours listed ({oh}) but could not be parsed reliably — please verify"), UNKNOWN))
    else:
        why.append((L(lang, "Часы работы в данных не указаны — открыто ли сейчас, неизвестно",
                      "Opening hours are not in the data — whether it is open now is unknown"), UNKNOWN))
    if p.get("internet_access") in ("wlan", "wifi", "yes"):
        why.append((L(lang, "Wi-Fi: указан в данных OSM", "Wi-Fi: listed in OSM data"), POI))
    if p.get("description_source") == "osm_description" and p.get("description"):
        why.append((p["description"][:160], POI))
    if parsed.work:
        if p.get("power_supply"):
            why.append((L(lang, "Розетки: указаны в данных OSM", "Power outlets: listed in OSM data"), POI))
        else:
            why.append((L(lang, "Розетки: данных нет — не подтверждено", "Power outlets: no data — unconfirmed"), UNKNOWN))
        if parsed.quiet:
            why.append((L(lang, "Тишина: в данных нет — не подтверждено", "Quietness: no data — unconfirmed"), UNKNOWN))
    if wheelchair:
        wc = (p.get("wheelchair") or "").lower()
        if wc in ("yes", "designated"):
            why.append((L(lang, "Доступность для коляски: да (данные OSM)", "Wheelchair access: yes (OSM data)"), POI))
        elif wc == "limited":
            why.append((L(lang, "Доступность для коляски: частичная (данные OSM)", "Wheelchair access: limited (OSM data)"), POI))
        else:
            why.append((L(lang, "Доступность для коляски: не подтверждена", "Wheelchair access: not confirmed"), UNKNOWN))
    if parsed.child:
        why.append((L(lang, "Возрастные ограничения и безопасность не проверены", "Age suitability and safety not verified"), UNKNOWN))
    age = _fetched_age_days(p.get("fetched_at"), now)
    if age is not None and age > STALE_DAYS:
        why.append((L(lang, f"Данные получены {age} дн. назад — могли устареть", f"Data fetched {age} days ago — may be outdated"), UNKNOWN))
    pts = _completeness(p)
    conf = "high" if pts >= 3 else "medium" if pts == 2 else "low"
    return {
        "id": p["id"], "name": p["name"], "category": cat, "category_label": label,
        "lat": p["lat"], "lon": p["lon"], "address": p.get("address", ""),
        "straight_m": round(straight, -1), "distance_m": round(walk_m, -1), "walk_method": method,
        "walk_min": walk_min, "visit_min": visit, "total_min": walk_min + visit,
        "open_state": state, "opening_hours": oh, "has_power": bool(p.get("power_supply")),
        "score": round(score, 3), "confidence": conf,
        "why": [{"text": t, "kind": k} for t, k in why],
        "what_to_do": {"text": idea_text(cat, lang), "kind": IDEA},
        "ai_text": "",
        "source": {"name": p.get("source", ""), "url": p.get("source_url", ""), "fetched_at": p.get("fetched_at", ""),
                   "license": p.get("license", "")},
        "website": p.get("website", ""), "phone": p.get("phone", ""),
    }


def verify_items(items, pois_by_id):
    good, problems = [], []
    for it in items:
        p = pois_by_id.get(it["id"])
        if p is None:
            problems.append(f"{it.get('name')}: нет в базе POI")
            continue
        if p["name"] != it["name"]:
            problems.append(f"{it['id']}: название не совпадает с базой")
            continue
        if abs(haversine_m(it["lat"], it["lon"], p["lat"], p["lon"])) > 1:
            problems.append(f"{it['id']}: координаты не совпадают с базой")
            continue
        if it["walk_min"] != route_planner.minutes_for(it["distance_m"]) and abs(it["walk_min"] - it["distance_m"] / WALK_SPEED_M_MIN) > 2:
            problems.append(f"{it['id']}: время в пути не соответствует расстоянию")
            continue
        good.append(it)
    return good, problems


def recommend(req, pois, index=None):
    parsed = parse_query(req.query)
    lang = req.lang if req.lang in ("ru", "en") else ("en" if parsed.language == "en" else "ru")
    result = {"ok": True, "mode": "template", "lang": lang, "items": [], "route": None, "notes": [],
              "data_used": [], "message": "", "excluded": {}, "llm_status": "", "origin": None,
              "parsed": asdict(parsed)}
    notes = result["notes"]

    if not parsed.supported:
        return _fail(result, L(lang, "Не удалось распознать язык запроса. Я понимаю русский, английский и частично казахский — переформулируйте, пожалуйста.",
                              "I could not recognise the language of the request. I understand Russian, English and partly Kazakh — please rephrase."))
    if not (req.query or "").strip() and not req.interests:
        return _fail(result, L(lang, "Опишите, что вы ищете, или выберите интересы в боковой панели.",
                              "Describe what you are looking for or pick interests in the sidebar."))
    if not pois:
        return _fail(result, L(lang, "База POI пуста. Запустите collect_poi.py и process_data.py (см. README).",
                              "The POI database is empty. Run collect_poi.py and process_data.py (see README)."))
    if parsed.language == "kk":
        notes.append(L(lang, "Запрос на казахском понят по ключевым словам; ответ дан на русском.",
                        "Kazakh request understood by keywords; the answer is given in Russian."))

    if parsed.landmark:
        lm = get_landmark(parsed.landmark)
        lat, lon, origin = lm["lat"], lm["lon"], lm[lang if lang in lm else "ru"]
        notes.append(L(lang, f"Локация взята из вашего запроса: {origin} (координаты ориентира приблизительные).",
                        f"Location taken from your request: {origin} (landmark coordinates are approximate)."))
    elif req.lat is not None and req.lon is not None:
        lat, lon, origin = req.lat, req.lon, L(lang, "точка, выбранная в интерфейсе", "point chosen in the UI")
    else:
        return _fail(result, L(lang, "Укажите, где вы находитесь: выберите точку в боковой панели или назовите ориентир в запросе.",
                              "Tell me where you are: pick a point in the sidebar or name a landmark in your request."))
    if not in_astana_area(lat, lon):
        return _fail(result, L(lang, "Координаты некорректны или находятся вне Астаны. Проверьте широту и долготу (Астана ≈ 51.1° с.ш., 71.4° в.д.).",
                              "Coordinates are invalid or outside Astana. Check latitude/longitude (Astana ≈ 51.1°N, 71.4°E)."))
    result["origin"] = {"name": origin, "lat": lat, "lon": lon}

    minutes = parsed.minutes or req.minutes or 90
    usable = minutes
    if parsed.flight:
        usable = minutes - req.flight_buffer_min
        notes.append(L(lang, f"Вы упомянули вылет: из {minutes} мин закладываю {req.flight_buffer_min} мин на дорогу в аэропорт и регистрацию. На прогулку остаётся {max(usable, 0)} мин.",
                        f"You mentioned a flight: out of {minutes} min I reserve {req.flight_buffer_min} min for getting to the airport and check-in. {max(usable, 0)} min left for a walk."))
        if usable < 25:
            return _fail(result, L(lang, f"До вылета слишком мало времени для безопасной прогулки (свободно {max(usable, 0)} мин). Лучше остаться в аэропорту.",
                                   f"Too little time before departure for a safe walk ({max(usable, 0)} min free). It is better to stay at the airport."))
    now = req.now or datetime.now(timezone(timedelta(hours=TZ_HOURS)))
    group = parsed.group_size or req.group_size
    wheelchair = parsed.wheelchair or req.wheelchair
    free_only = parsed.free or req.budget == "free"
    radius = max(MIN_RADIUS_M, min(MAX_RADIUS_M, 0.5 * usable * WALK_SPEED_M_MIN / DETOUR_FACTOR))

    cat_w = dict(parsed.categories)
    for c in req.interests:
        cat_w[c] = max(cat_w.get(c, 0), 1.0)
    general = not cat_w
    if general:
        cat_w = dict(DEFAULT_CATS)
        notes.append(L(lang, "Запрос общий — показываю типичные места для прогулки (парки, достопримечательности, смотровые).",
                        "The request is generic — showing typical walking spots (parks, sights, viewpoints)."))
    if parsed.events:
        notes.append(L(lang, "Актуальных данных о мероприятиях и выставках у системы нет — не утверждаю, что что-то проходит сейчас; проверьте афишу.",
                        "The system has no live event data — I do not claim anything is on right now; please check the programme."))
    if parsed.car:
        notes.append(L(lang, "Поддерживаются только пешие прогулки — рассчитано пешком.", "Only walking is supported — everything is calculated on foot."))
    if free_only:
        notes.append(L(lang, "«Бесплатно» определено по категории (эвристика) и тегу fee=no; цен в базе нет.",
                        "“Free” is inferred from category (heuristic) and the fee=no tag; the database has no prices."))

    result["data_used"] = [
        L(lang, f"Локация: {origin} ({lat:.4f}, {lon:.4f}) — используется только в этом запросе и не сохраняется",
          f"Location: {origin} ({lat:.4f}, {lon:.4f}) — used for this request only, not stored"),
        L(lang, f"Время на прогулку: {usable} мин; радиус поиска ≈ {radius:.0f} м (по прямой)",
          f"Walking time: {usable} min; search radius ≈ {radius:.0f} m (straight line)"),
        L(lang, "Категории: " + ", ".join(category_label(c, "ru") for c in cat_w),
          "Categories: " + ", ".join(category_label(c, "en") for c in cat_w)),
        L(lang, f"Время для проверки часов работы: {now:%d.%m.%Y %H:%M} (UTC+{TZ_HOURS})",
          f"Time used to check opening hours: {now:%d.%m.%Y %H:%M} (UTC+{TZ_HOURS})"),
        L(lang, "Источник мест: OpenStreetMap (данные из базы POI)", "Place source: OpenStreetMap (POI database)"),
    ]
    if group and group >= 3:
        result["data_used"].append(L(lang, f"Группа: {group} чел.", f"Group: {group} people"))

    within = within_radius(pois, lat, lon, radius)
    if not within:
        return _fail(result, L(lang, f"В радиусе {radius:.0f} м не найдено ни одного места в базе. Увеличьте время или выберите другую локацию.",
                              f"No places in the database within {radius:.0f} m. Increase the time or choose another location."))
    excluded = {"closed": 0, "wheelchair_no": 0, "paid": 0}
    cands = []
    for idx, d in within:
        p = pois[idx]
        if free_only and p["category"] in PAID_LIKELY and p.get("fee") != "no":
            excluded["paid"] += 1
            continue
        state, _ = check_open(p.get("opening_hours"), now)
        if state == "closed":
            excluded["closed"] += 1
            continue
        if wheelchair and (p.get("wheelchair") or "").lower() == "no":
            excluded["wheelchair_no"] += 1
            continue
        cands.append((idx, d, state))
    result["excluded"] = excluded
    if excluded["closed"]:
        notes.append(L(lang, f"Исключено закрытых по данным OSM мест: {excluded['closed']}.", f"Places closed by OSM hours excluded: {excluded['closed']}."))

    matched = [c for c in cands if cat_w.get(pois[c[0]]["category"], 0) > 0]
    relaxed = False
    if matched:
        cands = matched
    elif cands:
        relaxed = True
        notes.append(L(lang, "Точных совпадений по категории нет — показываю ближайшие подходящие по тексту варианты.",
                        "No exact category matches — showing nearby text-based matches."))
    if not cands:
        return _fail(result, L(lang, "Подходящих мест с учётом ограничений (часы работы, доступность, бюджет) не найдено. Попробуйте смягчить условия.",
                              "No places match the constraints (hours, accessibility, budget). Try relaxing them."))

    index = index or POIIndex(pois)
    expansion = " ".join(normalize(req.query).split())
    text_scores = index.scores(expansion, [c[0] for c in cands])
    tmax = max(text_scores.values()) or 1.0
    ranked = []
    for idx, d, state in cands:
        p = pois[idx]
        cat = p["category"]
        cat_score = cat_w.get(cat, 0.2 if relaxed else 0.0)
        s = 0.40 * cat_score + 0.30 * (text_scores[idx] / tmax) + 0.20 * (1 - d / radius) + 0.10 * _completeness(p) / 4
        if state == "unknown":
            s -= 0.25 if parsed.night else 0.05
        elif state == "open" and parsed.night:
            s += 0.15
        if wheelchair:
            wc = (p.get("wheelchair") or "").lower()
            s += 0.2 if wc in ("yes", "designated") else 0.05 if wc == "limited" else -0.1
        if parsed.work and p.get("internet_access") in ("wlan", "wifi", "yes"):
            s += 0.2
        if group and group >= 3:
            s += GROUP_BONUS.get(cat, 0)
        ranked.append((s, idx, d, state))
    ranked.sort(key=lambda x: x[0], reverse=True)

    osrm_on = req.use_osrm
    pool = []
    for s, idx, d, state in ranked[:8]:
        p = pois[idx]
        walk_m, method = route_planner.walk_distance((lat, lon), (p["lat"], p["lon"]), osrm_on)
        if osrm_on and method == "estimate":
            osrm_on = False
            notes.append(L(lang, "Сервис пеших маршрутов недоступен — расстояния рассчитаны приблизительно.",
                            "The walking-route service is unavailable — distances are estimated."))
        item = _make_item(p, d, walk_m, method, state, parsed, cat_w, lang, now, s, wheelchair)
        pool.append(item)
    fit = [it for it in pool if it["total_min"] <= usable]
    if not fit:
        pool.sort(key=lambda it: it["total_min"])
        fit = pool[:1]
        notes.append(L(lang, f"Ни одно место не укладывается в {usable} мин (дорога + посещение); показываю ближайшее — оно займёт больше времени.",
                        f"No place fits into {usable} min (walk + visit); showing the closest one — it will take longer."))

    chosen, per_cat = [], {}
    wide = len(cat_w) >= 3
    for it in fit:
        if wide and per_cat.get(it["category"], 0) >= 2:
            continue
        chosen.append(it)
        per_cat[it["category"]] = per_cat.get(it["category"], 0) + 1
        if len(chosen) == req.max_results:
            break

    pois_by_id = {p["id"]: p for p in pois}
    chosen, problems = verify_items(chosen, pois_by_id)
    if problems:
        notes.append(L(lang, f"Проверка отбросила {len(problems)} некорректных результатов.", f"Verification dropped {len(problems)} invalid results."))
    if not chosen:
        return _fail(result, L(lang, "Не удалось сформировать проверенные рекомендации.", "Could not build verified recommendations."))
    result["items"] = chosen

    can_route = (req.want_route or parsed.route_words) and not parsed.work and usable >= 60 \
        and len(fit) >= 2 and len({it["category"] for it in fit}) >= 2
    if can_route:
        by_id = {it["id"]: it for it in fit}
        plan = route_planner.plan_route((lat, lon), [{"id": it["id"], "lat": it["lat"], "lon": it["lon"], "score": it["score"],
                                                    "category": it["category"], "visit_min": it["visit_min"]} for it in fit],
                                        usable, use_osrm=osrm_on, max_stops=3)
        if plan:
            plan["stops"] = [by_id[i] for i in plan["stops"]]
            plan["note"] = L(lang, "Время приблизительное: ходьба ≈ 4.8 км/ч плюс типичное время визита по категории.",
                             "Times are approximate: walking ≈ 4.8 km/h plus typical visit time per category.")
            result["route"] = plan

    if req.use_llm:
        texts, status = llm.explain(req.query, chosen, lang)
        result["llm_status"] = status
        if texts:
            for it in chosen:
                it["ai_text"] = texts.get(it["id"], "")
            result["mode"] = "llm_verified"
        else:
            result["mode"] = "template_after_llm_fail"
            notes.append(L(lang, "Языковая модель недоступна или её ответ не прошёл проверку — использован режим шаблонов.",
                            "The language model is unavailable or its answer failed verification — template mode used."))
    return result
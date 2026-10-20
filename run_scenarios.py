import argparse
import json
from datetime import datetime, timedelta, timezone

import route_planner
from config import BASE_DIR, CLEAN_FILE, TZ_HOURS
from geo import haversine_m
from landmarks import LANDMARKS
from recommender import Request, build_index, recommend

NOW = datetime.now(timezone(timedelta(hours=TZ_HOURS)))
EVENING = NOW.replace(hour=21, minute=30)


def pt(key):
    return LANDMARKS[key]["lat"], LANDMARKS[key]["lon"]


SCENARIOS = [
    ("S1", "Прогулка у EXPO на 1–2 часа", "Я возле EXPO 2017. Хочу что-то необычное на 1–2 часа, пешком.", pt("expo"), {},
     "1–3 места из «необычных» категорий (достопримечательности, смотровые, арт, музеи), в пределах времени; мини-маршрут."),
    ("S2", "Тихое кафе для работы", "Хочу тихое место с кофе и розеткой, где можно поработать.", pt("megasilkway"), {},
     "Кафе/библиотеки; розетки и тишина НЕ обещаются без данных; Wi-Fi только если есть тег."),
    ("S3", "Группа из четырёх человек", "Нас четверо, у нас два часа. Хотим погулять и сделать красивые фотографии.", pt("baiterek"), {},
     "Парки/смотровые/достопримечательности; мини-маршрут из 2–3 мест в пределах 2 часов; пометка о вместимости."),
    ("S4", "Места с ребёнком", "Я с ребёнком. Что интересного есть рядом?", pt("megasilkway"), {},
     "Детские площадки/парки/зоопарк/музеи; пометка, что возраст и безопасность не проверены."),
    ("S5a", "Турист, 4 часа до вылета", "Я турист, у меня четыре часа до вылета. Что можно посмотреть поблизости?", pt("station"), {},
     "Достопримечательности; из 4 ч закладывается 90 мин на аэропорт; время визита в пределах остатка."),
    ("S5b", "Турист, 2 часа до вылета", "Я турист, у меня два часа до вылета. Что можно посмотреть поблизости?", pt("station"), {},
     "Осторожное поведение: остаётся ≈30 мин — только самые близкие места либо совет остаться в аэропорту."),
]
EDGE = [
    ("E1", "Ночная активность (вечер)", "Ищу необычную ночную активность на пару часов.", pt("expo"), {"now": EVENING}, "Закрытые по часам места исключены; неизвестные часы — с пометкой и штрафом."),
    ("E2", "Запрос про мероприятия", "Что за выставка идёт сейчас рядом?", pt("expo"), {}, "Нет утверждения, что что-то идёт сейчас; пометка об отсутствии данных о событиях."),
    ("E3", "Неправильные координаты", "Хочу кофе", (999.0, 71.4), {}, "Понятная ошибка, без падения."),
    ("E4", "Точка вне Астаны (Алматы)", "Хочу кофе", (43.238, 76.945), {}, "Сообщение, что точка вне Астаны."),
    ("E5", "Неподдерживаемый язык", "我想喝咖啡", pt("expo"), {}, "Сообщение о неподдерживаемом языке."),
    ("E6", "Нет подходящих мест (пустой радиус)", "Хочу кофе", (51.2600, 71.6400), {"minutes": 20}, "Честное «ничего не найдено»."),
    ("E7", "Сервис маршрутов недоступен", "Хочу кофе рядом", pt("expo"), {"use_osrm": True}, "Откат на оценку расстояния + пометка."),
    ("E8", "Доступность (коляска)", "Хочу погулять, я на коляске", pt("baiterek"), {}, "Исключены места с wheelchair=no; для остальных «не подтверждено», если нет тега."),
]


def check_result(res, usable_hint=None):
    checks = []
    if not res["ok"]:
        checks.append(("ошибка/пустой результат сообщена текстом", bool(res["message"])))
        return checks
    items = res["items"]
    checks.append(("есть хотя бы одно место", len(items) >= 1))
    checks.append(("у каждого места есть ссылка на источник", all(i["source"]["url"].startswith("http") for i in items)))
    org = res["origin"]
    checks.append(("расстояния по прямой совпадают с пересчётом",
                   all(abs(haversine_m(org["lat"], org["lon"], i["lat"], i["lon"]) - i["straight_m"]) <= 6 for i in items)))
    checks.append(("пешее время = расстояние / скорость", all(abs(i["walk_min"] - i["distance_m"] / 80) <= 2 for i in items)))
    checks.append(("неизвестные часы помечены UNKNOWN",
                   all(any(w["kind"] == "UNKNOWN" for w in i["why"]) for i in items if i["open_state"] == "unknown")))
    checks.append(("нет «открыто» без подтверждения по данным",
                   all(not any("сейчас открыто" in w["text"] for w in i["why"]) for i in items if i["open_state"] != "open")))
    if res["route"]:
        checks.append(("маршрут укладывается в бюджет времени", res["route"]["total_min"] <= res["route"]["budget_min"]))
    return checks


def render(sid, title, query, loc, expected, res):
    out = [f"### {sid}. {title}", f"**Запрос:** «{query}»  ", f"**Точка (если не названа в запросе):** {loc[0]}, {loc[1]}  ",
           f"**Ожидаемое поведение:** {expected}  ", f"**Режим ответа:** {res['mode']}  "]
    if not res["ok"]:
        out.append(f"**Фактический ответ:** {res['message']}")
    else:
        out.append(f"**Локация системы:** {res['origin']['name']}")
        out.append("**Найденные POI:**")
        for n, i in enumerate(res["items"], 1):
            out.append(f"{n}. **{i['name']}** ({i['category_label']}) — ≈{i['straight_m']:.0f} м по прямой, пешком ≈{i['walk_min']} мин "
                       f"({i['walk_method']}), визит ≈{i['visit_min']} мин, часы: {i['opening_hours'] or 'нет данных'}, "
                       f"полнота данных: {i['confidence']}, источник: {i['source']['url']}")
            for w in i["why"]:
                if w["kind"] == "UNKNOWN":
                    out.append(f"   - ВНИМАНИЕ: {w['text']}")
        if res["route"]:
            r = res["route"]
            names = " → ".join(s["name"] for s in r["stops"])
            out.append(f"**Мини-маршрут:** {names} (≈{r['total_min']} из {r['budget_min']} мин: ходьба {r['walk_min']}, визиты {r['visit_min']})")
    if res["notes"]:
        out.append("**Заметки системы:** " + " | ".join(res["notes"]))
    out.append("**Автопроверки:**")
    for name, ok in check_result(res):
        out.append(f"- {'[OK]' if ok else '[ПРОВАЛ]'} {name}")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(CLEAN_FILE))
    args = ap.parse_args()
    pois = json.loads(open(args.data, encoding="utf-8").read())
    index = build_index(pois) if pois else None
    lines = ["# Результаты тестовых сценариев (сгенерировано автоматически)", "",
             f"Дата прогона: {NOW:%d.%m.%Y %H:%M} (UTC+{TZ_HOURS}); POI в базе: {len(pois)}. "
             "Файл создаётся скриптом `run_scenarios.py` из реальных ответов системы.", "",
             "## Основные сценарии", ""]
    failed = 0

    def run_one(sid, title, query, loc, kw, exp, db, idx):
        nonlocal failed
        kwargs = dict(kw)
        kwargs.setdefault("now", NOW)
        original = route_planner.OSRM_URL
        if sid == "E7":
            route_planner.OSRM_URL = "http://127.0.0.1:9/none"
        try:
            res = recommend(Request(query=query, lat=loc[0], lon=loc[1], **kwargs), db, idx)
        finally:
            route_planner.OSRM_URL = original
        route_planner._osrm_distance.cache_clear()
        bad = [n for n, ok in check_result(res) if not ok]
        failed += len(bad)
        print(f"{sid}: {'OK' if not bad else 'ПРОВАЛ ' + str(bad)}  ->  {'ok' if res['ok'] else res['message'][:70]}")
        return render(sid, title, query, loc, exp, res)

    for s in SCENARIOS:
        lines.append(run_one(*s[:5], s[5], pois, index))
    lines += ["## Граничные случаи", ""]
    for s in EDGE:
        lines.append(run_one(*s[:5], s[5], pois, index))
    lines.append("### E9. Пустая база данных")
    res = recommend(Request(query="Хочу кофе", lat=pt("expo")[0], lon=pt("expo")[1]), [], None)
    lines.append(f"**Ожидаемо:** понятное сообщение без падения. **Фактически:** {res['message']}\n")
    lines.append("## Итог\n")
    lines.append(f"Не прошло автопроверок: **{failed}**. Если есть [ПРОВАЛ] — это реальные ошибки/ограничения: опишите их в документе ограничений или исправьте код.")
    out = BASE_DIR / "docs" / "TEST_RESULTS.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nЗаписано: {out}")


if __name__ == "__main__":
    main()
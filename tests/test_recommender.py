import route_planner
import llm
from recommender import Request, build_index, recommend, verify_items
from tests.fixtures import EXPO, NIGHT, NOW, make_pois

POIS = make_pois()
INDEX = build_index(POIS)


def run(query, **kw):
    kw.setdefault("lat", EXPO[0]); kw.setdefault("lon", EXPO[1]); kw.setdefault("now", NOW)
    return recommend(Request(query=query, **kw), POIS, INDEX)


def names(res):
    return [i["name"] for i in res["items"]]


def test_ranking_prefers_requested_category_and_excludes_closed():
    res = run("хочу кофе")
    assert res["ok"] and names(res)
    assert all(i["category"] == "cafe" for i in res["items"])
    assert "Закрытое Кафе" not in names(res)                  # закрыто по часам OSM
    assert res["items"][0]["name"] == "Тест Кофе"             # есть часы + Wi-Fi + ближе


def test_unknown_hours_is_honest():
    res = run("хочу кофе")
    item = next(i for i in res["items"] if i["name"] == "Тест Кафе без часов")
    kinds = [w["kind"] for w in item["why"]]
    assert "UNKNOWN" in kinds
    assert not any("открыто" in w["text"].lower() and w["kind"] == "POI" for w in item["why"])


def test_work_query_does_not_promise_outlets():
    res = run("тихое место с кофе и розеткой, поработать")
    for i in res["items"]:
        assert any("Розетки" in w["text"] and w["kind"] == "UNKNOWN" for w in i["why"])


def test_time_limit_respected():
    res = run("прогулка", minutes=60)
    for i in res["items"]:
        assert i["total_min"] <= 60 or res["notes"]


def test_wheelchair_excludes_inaccessible():
    res = run("хочу посмотреть достопримечательности и смотровую", wheelchair=True, minutes=120)
    assert "Тест Смотровая" not in names(res)
    assert res["excluded"]["wheelchair_no"] >= 1


def test_night_penalises_unknown_and_excludes_closed():
    res = run("ищу необычную ночную активность", now=NIGHT, minutes=120)
    assert res["ok"]
    assert names(res)[0] == "Тест Бар"                        # открыт ночью по часам


def test_route_is_built_for_long_walk():
    res = run("Нас четверо, два часа, погулять и сделать красивые фотографии", minutes=120)
    assert res["ok"]
    if res["route"]:
        assert res["route"]["total_min"] <= 120
        assert len(res["route"]["stops"]) >= 2


def test_empty_database():
    res = recommend(Request(query="кофе", lat=EXPO[0], lon=EXPO[1]), [], None)
    assert not res["ok"] and "пуста" in res["message"]


def test_no_places_in_radius():
    res = run("кофе", lat=51.20, lon=71.60, minutes=30)
    assert not res["ok"] and res["items"] == []


def test_invalid_and_missing_location():
    assert not run("кофе", lat=999, lon=71.4)["ok"]
    assert not run("кофе", lat=43.2, lon=76.9)["ok"]          # Алматы — вне Астаны
    assert not recommend(Request(query="кофе"), POIS, INDEX)["ok"]


def test_unsupported_language_and_empty_query():
    assert not run("我想喝咖啡")["ok"]
    assert not run("")["ok"]


def test_landmark_in_query_overrides_ui_point():
    res = run("Я возле Mega Silk Way, хочу кофе", lat=51.20, lon=71.60)
    assert res["origin"]["name"].startswith("Mega Silk Way")


def test_events_not_claimed():
    res = run("есть ли сейчас выставка?")
    assert any("мероприят" in n.lower() or "афиш" in n.lower() for n in res["notes"])


def test_flight_buffer_and_tight_time():
    res = run("я турист, два часа до вылета", flight_buffer_min=100)
    assert not res["ok"] and "аэропорт" in res["message"].lower()
    res0 = run("я турист, два часа до вылета")                      # буфер по умолчанию 90 мин -> 30 мин на прогулку
    assert any("30 мин" in n for n in res0["notes"])
    res2 = run("я турист, четыре часа до вылета")
    assert res2["ok"] and any("вылет" in n.lower() for n in res2["notes"])


def test_osrm_failure_falls_back_to_estimate():
    original = route_planner._osrm_distance
    def boom(*a, **k): raise ConnectionError("offline")
    route_planner._osrm_distance = boom
    try:
        res = run("кофе", use_osrm=True)
    finally:
        route_planner._osrm_distance = original
    assert res["ok"] and all(i["walk_method"] == "estimate" for i in res["items"])
    assert any("недоступен" in n for n in res["notes"])


def test_verify_items_rejects_fabricated_place():
    res = run("кофе")
    fake = dict(res["items"][0]); fake["id"] = "osm/node/999999"
    renamed = dict(res["items"][0]); renamed["name"] = "Выдуманное место"
    good, problems = verify_items([fake, renamed, res["items"][0]], {p["id"]: p for p in POIS})
    assert len(good) == 1 and len(problems) == 2


def test_llm_verification_rejects_invented_claims():
    res = run("кофе")
    item = res["items"][0]
    ok_text = f"Кофейня в {item['walk_min']} мин ходьбы."
    data = {item["id"]: ok_text, "osm/node/0": "выдумка"}
    clean, problems = llm.verify(data, res["items"])
    assert item["id"] in clean and len(problems) == 1
    for bad in ("Здесь 777 мест и есть розетки", "Сейчас идёт выставка", "Сейчас открыто до ночи"):
        clean, problems = llm.verify({item["id"]: bad}, [dict(item, open_state="unknown", has_power=False)])
        assert not clean and problems


def test_llm_off_means_template_mode():
    res = run("кофе", use_llm=False)
    assert res["mode"] == "template"

import process_data
from query_parser import detect_language, parse_query
from tests.fixtures import make_pois


def test_minutes_parsing():
    assert parse_query("Я возле EXPO 2017, хочу что-то необычное на 1–2 часа, пешком").minutes == 120
    assert parse_query("хочу прогуляться 30–60 минут").minutes == 60
    assert parse_query("у меня два часа до вылета").minutes == 120
    assert parse_query("I have 45 minutes").minutes == 45
    assert parse_query("просто кофе").minutes is None


def test_group_child_work_flags():
    q = parse_query("Нас четверо, у нас два часа. Хотим погулять и сделать красивые фотографии")
    assert q.group_size == 4 and q.photo and "park" in q.categories and "viewpoint" in q.categories
    assert parse_query("Я с ребёнком. Что интересного есть рядом?").child
    w = parse_query("Хочу тихое место с кофе и розеткой, где можно поработать")
    assert w.work and w.quiet and "cafe" in w.categories
    assert parse_query("Я турист, два часа до вылета").flight


def test_landmark_and_language():
    assert parse_query("Я возле Mega Silk Way").landmark == "megasilkway"
    assert parse_query("я у здания экспо 2017").landmark == "expo"
    assert detect_language("Привет") == "ru"
    assert detect_language("coffee near me") == "en"
    assert detect_language("қайда кофе ішуге болады") == "kk"
    assert detect_language("我想喝咖啡") == "unsupported"
    assert not parse_query("我想喝咖啡").supported


def test_process_cleaning():
    pois = make_pois()
    names = [p["name"] for p in pois]
    assert names.count("Тест Кофе") == 1                       # дубликат удалён
    assert "Далёкое Кафе" not in names                         # вне Астаны
    assert "Нулевые координаты" not in names                   # неверные координаты
    assert "Не наша категория" not in names
    assert any(p["category"] == "playground" for p in pois)    # безымянная площадка сохранена
    assert not any(p["category"] == "cafe" and p["name"] == "" for p in pois)
    cafe = next(p for p in pois if p["name"] == "Тест Кафе без часов")
    assert cafe["opening_hours"] == ""                         # пустое поле не ломает запись
    assert cafe["source_url"].startswith("https://www.openstreetmap.org/")
    assert cafe["description_source"] == "generated_from_tags"
    assert process_data.category_from_tags({"amenity": "cafe"}) == "cafe"
    assert process_data.category_from_tags({"shop": "bakery"}) is None

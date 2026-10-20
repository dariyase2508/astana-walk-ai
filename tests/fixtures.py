"""Синтетические данные ТОЛЬКО для автотестов (в демо и рекомендациях не используются)."""
from datetime import datetime, timedelta, timezone

import process_data

NOW = datetime(2026, 10, 20, 15, 0, tzinfo=timezone(timedelta(hours=5)))      # вторник, 15:00
NIGHT = datetime(2026, 10, 20, 23, 30, tzinfo=timezone(timedelta(hours=5)))

EXPO = (51.0894, 71.4162)


def el(i, lat, lon, tags, typ="node"):
    return {"type": typ, "id": i, "lat": lat, "lon": lon, "tags": tags, "_fetched_at": NOW.isoformat()}


def make_pois():
    elements = [
        el(1, 51.0900, 71.4170, {"amenity": "cafe", "name": "Тест Кофе", "opening_hours": "Mo-Su 08:00-22:00",
                                  "internet_access": "wlan"}),
        el(2, 51.0905, 71.4175, {"amenity": "cafe", "name": "Тест Кафе без часов"}),
        el(3, 51.0910, 71.4180, {"amenity": "cafe", "name": "Закрытое Кафе", "opening_hours": "Mo-Su 02:00-04:00"}),
        el(4, 51.0920, 71.4190, {"tourism": "museum", "name": "Тест Музей", "opening_hours": "Tu-Su 10:00-18:00"}),
        el(5, 51.0930, 71.4200, {"leisure": "park", "name": "Тест Парк"}),
        el(6, 51.0940, 71.4210, {"leisure": "playground"}),
        el(7, 51.0950, 71.4220, {"tourism": "viewpoint", "name": "Тест Смотровая", "wheelchair": "no"}),
        el(8, 51.0960, 71.4230, {"tourism": "attraction", "name": "Тест Достопримечательность", "wheelchair": "yes"}),
        el(9, 51.0970, 71.4240, {"amenity": "bar", "name": "Тест Бар", "opening_hours": "Mo-Su 18:00-04:00"}),
        el(10, 51.3000, 71.9000, {"amenity": "cafe", "name": "Далёкое Кафе"}),       # вне рамки Астаны
        el(11, 0, 0, {"amenity": "cafe", "name": "Нулевые координаты"}),                  # неверные координаты
        el(12, 51.0901, 71.4171, {"amenity": "cafe", "name": "Тест Кофе"}),               # дубликат №1
        el(13, 51.0980, 71.4250, {"shop": "bakery", "name": "Не наша категория"}),
        el(14, 51.0990, 71.4260, {"amenity": "cafe"}),                                     # без названия
    ]
    records, _ = process_data.process(elements)
    return records

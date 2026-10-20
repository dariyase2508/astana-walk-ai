from datetime import datetime, timedelta, timezone

from geo import haversine_m, in_astana_area, valid_coords, within_radius
from hours import check_open

TZ = timezone(timedelta(hours=5))


def test_haversine_basic():
    assert haversine_m(51.1, 71.4, 51.1, 71.4) == 0
    assert abs(haversine_m(51.0, 71.0, 52.0, 71.0) - 111195) < 600          # 1° широты ≈ 111 км
    a, b = (51.1283, 71.4305), (51.1327, 71.4037)                            # Байтерек — Хан Шатыр
    assert 1500 < haversine_m(*a, *b) < 2500
    assert abs(haversine_m(*a, *b) - haversine_m(*b, *a)) < 1e-6


def test_valid_coords():
    assert valid_coords(51.1, 71.4)
    assert not valid_coords(None, 71.4)
    assert not valid_coords("abc", 1)
    assert not valid_coords(91, 0)
    assert not valid_coords(float("nan"), 0)
    assert in_astana_area(51.09, 71.41)
    assert not in_astana_area(43.2, 76.9)       # Алматы


def test_within_radius_filters_and_sorts():
    pois = [{"lat": 51.1000, "lon": 71.4000}, {"lat": 51.1050, "lon": 71.4000}, {"lat": 51.2000, "lon": 71.4000},
            {"lat": None, "lon": None}]
    res = within_radius(pois, 51.1, 71.4, 1000)
    assert [i for i, _ in res] == [0, 1]
    assert res[0][1] <= res[1][1]


def test_hours_open_closed_unknown():
    tue_15 = datetime(2026, 10, 20, 15, 0, tzinfo=TZ)
    assert check_open("Mo-Su 08:00-22:00", tue_15)[0] == "open"
    assert check_open("Mo-Su 02:00-04:00", tue_15)[0] == "closed"
    assert check_open("24/7", tue_15)[0] == "open"
    assert check_open("", tue_15)[0] == "unknown"
    assert check_open("Mo-Fr sunrise-sunset", tue_15)[0] == "unknown"      # не гадаем
    assert check_open("Mo-Fr 09:00-18:00; Tu off", tue_15)[0] == "closed"
    assert check_open("Mo-Fr 09:00-13:00,14:00-18:00", tue_15)[0] == "open"


def test_hours_after_midnight():
    wed_01 = datetime(2026, 10, 21, 1, 0, tzinfo=TZ)
    assert check_open("Mo-Su 18:00-04:00", wed_01)[0] == "open"             # открыто с вечера вторника
    wed_10 = datetime(2026, 10, 21, 10, 0, tzinfo=TZ)
    assert check_open("Mo-Su 18:00-04:00", wed_10)[0] == "closed"

import ui_html as ui
from recommender import Request, build_index, recommend
from tests.fixtures import EXPO, NOW, make_pois


def test_cards_are_escaped_and_have_no_emoji():
    pois = make_pois()
    pois[0]["name"] = '<script>alert(1)</script> Кафе'
    res = recommend(Request(query="хочу кофе", lat=EXPO[0], lon=EXPO[1], now=NOW), pois, build_index(pois))
    assert res["ok"]
    out = ui.card_html(res["items"][0], 1) + ui.legend_html() + ui.CSS
    assert "<script>" not in out and "&lt;script&gt;" in out or "alert" not in out
    assert not any(ord(c) > 0x1F000 or 0x2600 <= ord(c) <= 0x27BF for c in out)
    assert 'class="chip unknown"' in out or 'class="chip poi"' in out


def test_unsafe_links_dropped():
    assert ui.safe_url("javascript:alert(1)") == ""
    assert ui.safe_url("https://www.openstreetmap.org/node/1").startswith("https://")

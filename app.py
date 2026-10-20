"""Astana Walk AI — интерфейс (Streamlit). Команда Unsurprised.
Запуск: python -m streamlit run app.py   (через .venv, см. README)"""
import json
from datetime import datetime, time, timedelta, timezone

import pandas as pd
import streamlit as st

import llm
import ui_html as ui
from categories import CATEGORY_INFO
from config import CLEAN_FILE, FLIGHT_BUFFER_MIN, TZ_HOURS
from landmarks import LANDMARKS
from recommender import Request, build_index, recommend

st.set_page_config(page_title="Astana Walk AI", layout="wide")
st.markdown(ui.CSS, unsafe_allow_html=True)

INTERESTS = {"Кафе и кофе": "cafe", "Еда": "restaurant", "Парки": "park", "Музеи": "museum", "Детям": "playground",
             "Смотровые и фото": "viewpoint", "Достопримечательности": "attraction", "Ночная жизнь": "nightlife",
             "Кино и театр": "cinema"}
EXAMPLES = [
    "Я возле EXPO 2017. Хочу что-то необычное на 1–2 часа, пешком.",
    "Хочу тихое место с кофе и розеткой, где можно поработать.",
    "Нас четверо, у нас два часа. Хотим погулять и сделать красивые фотографии.",
    "Я с ребёнком. Что интересного есть рядом?",
    "Я турист, у меня четыре часа до вылета. Что можно посмотреть поблизости?",
]


@st.cache_resource(show_spinner="Загружаем базу мест...")
def load_data():
    if not CLEAN_FILE.exists():
        return [], None
    pois = json.loads(CLEAN_FILE.read_text(encoding="utf-8"))
    return pois, (build_index(pois) if pois else None)


def set_example(text):
    st.session_state["query"] = text


pois, index = load_data()
tz = timezone(timedelta(hours=TZ_HOURS))

# ------------------------------------------------------------------ боковая панель
with st.sidebar:
    st.header("Параметры")
    loc_mode = st.radio("Где вы находитесь?", ["Ориентир из списка", "Свои координаты"])
    if loc_mode == "Ориентир из списка":
        key = st.selectbox("Ориентир", list(LANDMARKS), format_func=lambda k: LANDMARKS[k]["ru"])
        lat, lon = LANDMARKS[key]["lat"], LANDMARKS[key]["lon"]
        st.caption("Координаты ориентиров приблизительные. Название ориентира в тексте запроса важнее этого выбора.")
    else:
        lat = st.number_input("Широта", value=51.0894, format="%.5f")
        lon = st.number_input("Долгота", value=71.4162, format="%.5f")
    minutes = st.slider("Время на прогулку, мин", 20, 240, 90, 10,
                        help="Если время указано в тексте запроса («на 1–2 часа»), используется оно.")
    budget_label = st.selectbox("Бюджет", ["Любой", "Только бесплатное"])
    interests_sel = st.multiselect("Интересы", list(INTERESTS))
    wheelchair = st.checkbox("Нужна доступность для коляски")
    group = st.number_input("Сколько вас человек", 1, 10, 1)
    lang_label = st.selectbox("Язык ответа", ["Авто", "Русский", "English"])
    with st.expander("Дополнительно"):
        use_now = st.checkbox("Текущее время Астаны для часов работы", value=True)
        sim_time = st.time_input("Или своё время", time(15, 0), disabled=use_now)
        want_route = st.checkbox("Предлагать мини-маршрут", value=True)
        use_osrm = st.checkbox("Реальные пешие маршруты (OSRM, нужен интернет)", value=False)
        key_ok = llm.is_available()
        use_llm = st.checkbox("Генерация текста ИИ (Gemini, с проверкой)", value=False, disabled=not key_ok,
                              help="Нужен бесплатный ключ GEMINI_API_KEY в файле .env. Без него работает режим шаблонов.")
        flight_buffer = st.number_input("Запас до вылета, мин", 30, 240, FLIGHT_BUFFER_MIN, 10,
                                        help="Сколько минут нужно на дорогу в аэропорт и регистрацию.")
    with st.expander("Приватность"):
        st.write("Координаты используются только для текущего поиска и нигде не сохраняются и не логируются. "
                 "В языковую модель (если включена) уходит только текст запроса и данные найденных мест — без координат.")

# ------------------------------------------------------------------ основная часть
st.markdown(ui.brand_html(), unsafe_allow_html=True)
if not pois:
    st.error("База мест пуста. Выполните `collect_poi.py`, затем `process_data.py` (см. README).")
    st.stop()
st.markdown(f'<div class="lead">В базе {len(pois)} реальных мест из OpenStreetMap (© участники OSM, ODbL). '
            'Часы работы, розетки и доступность показываются только если они есть в данных.</div>', unsafe_allow_html=True)

st.markdown("**Примеры запросов:**")
cols = st.columns(len(EXAMPLES))
for c, ex in zip(cols, EXAMPLES):
    c.button(ex[:38] + "…", on_click=set_example, args=(ex,), use_container_width=True)

st.text_area("Опишите, что хотите", key="query", height=90,
             placeholder="Например: Я возле Mega Silk Way, хочу прогуляться 30–60 минут")
go = st.button("Найти", type="primary")

if go:
    now = datetime.now(tz) if use_now else datetime.combine(datetime.now(tz).date(), sim_time, tzinfo=tz)
    req = Request(query=st.session_state.get("query", ""), lat=lat, lon=lon, minutes=minutes,
                  budget="free" if budget_label.startswith("Только") else "any",
                  interests=[INTERESTS[i] for i in interests_sel], wheelchair=wheelchair,
                  group_size=int(group) if group > 1 else None,
                  lang={"Русский": "ru", "English": "en"}.get(lang_label), now=now, use_osrm=use_osrm,
                  use_llm=use_llm, want_route=want_route, flight_buffer_min=int(flight_buffer))
    with st.spinner("Ищем подходящие места..."):
        st.session_state["result"] = recommend(req, pois, index)

res = st.session_state.get("result")
if res:
    st.divider()
    if not res["ok"]:
        st.markdown(ui.note_html(res["message"], warn=True), unsafe_allow_html=True)
        for n in res["notes"]:
            st.markdown(ui.note_html(n), unsafe_allow_html=True)
    else:
        mode_text = {"template": "Режим: поиск по данным и шаблонные объяснения, языковая модель не используется",
                     "llm_verified": "Режим: поиск по данным и текст языковой модели с проверкой",
                     "template_after_llm_fail": "Режим: шаблоны (ответ языковой модели недоступен или не прошёл проверку)"}
        st.markdown(f'<span class="mode">{ui.esc(mode_text.get(res["mode"], res["mode"]))}</span>', unsafe_allow_html=True)
        with st.expander("Какие данные использованы"):
            for line in res["data_used"]:
                st.write("• " + line)
        for n in res["notes"]:
            st.markdown(ui.note_html(n), unsafe_allow_html=True)
        for n, it in enumerate(res["items"], 1):
            st.markdown(ui.card_html(it, n), unsafe_allow_html=True)
        if res["route"]:
            st.markdown(ui.route_html(res["route"]), unsafe_allow_html=True)
        pts = [{"lat": res["origin"]["lat"], "lon": res["origin"]["lon"]}] + [{"lat": i["lat"], "lon": i["lon"]} for i in res["items"]]
        st.map(pd.DataFrame(pts), zoom=13)
        st.markdown(ui.legend_html(), unsafe_allow_html=True)

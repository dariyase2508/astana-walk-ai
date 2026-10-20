import html

CSS = """
<style>
:root{--ink:#1D2125;--muted:#6B7177;--line:#DAD6CB;--paper:#FFFFFF;--bg:#F6F4EF;--accent:#1F4E5F;--accent-soft:#E3ECEE;--warn:#9A6A12;--warn-soft:#F8F0DD}
html,body,[class*="css"]{font-family:"Segoe UI","Helvetica Neue",Arial,sans-serif}
.block-container{padding-top:2.2rem;max-width:1080px}
#MainMenu,footer{visibility:hidden}
h1,h2,h3{letter-spacing:-0.01em}
.brand{display:flex;align-items:baseline;gap:14px;border-bottom:1px solid var(--line);padding-bottom:14px;margin-bottom:6px}
.brand .name{font-size:1.9rem;font-weight:700;color:var(--ink)}
.brand .tag{font-size:.9rem;color:var(--muted)}
.lead{color:var(--muted);font-size:.95rem;margin:8px 0 18px}
.card{background:var(--paper);border:1px solid var(--line);border-radius:6px;padding:20px 22px;margin:0 0 16px}
.card-head{display:flex;gap:14px;align-items:flex-start}
.idx{flex:0 0 30px;height:30px;border:1.5px solid var(--accent);color:var(--accent);border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:.9rem}
.name{font-size:1.2rem;font-weight:650;line-height:1.25}
.sub{color:var(--muted);font-size:.86rem;margin-top:2px}
.stats{display:flex;gap:0;margin:16px 0 14px;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
.stat{flex:1;padding:10px 0 10px 14px;border-left:1px solid var(--line)}
.stat:first-child{border-left:none;padding-left:0}
.stat b{display:block;font-size:1.15rem;font-weight:650}
.stat span{font-size:.78rem;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
.label{font-size:.75rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:600;margin:12px 0 6px}
ul.why{list-style:none;margin:0;padding:0}
ul.why li{padding:6px 0 6px 12px;border-left:2px solid var(--line);margin:0 0 4px;font-size:.93rem;line-height:1.4}
ul.why li.unknown{border-left-color:var(--warn);background:var(--warn-soft)}
.chip{display:inline-block;margin-left:8px;padding:1px 7px;border-radius:3px;font-size:.68rem;font-weight:600;letter-spacing:.05em;text-transform:uppercase;background:var(--accent-soft);color:var(--accent);vertical-align:1px}
.chip.calc{background:#ECECEC;color:#4A4F55}
.chip.idea{background:#EFE9F5;color:#5B4678}
.chip.unknown{background:#F1E2B8;color:var(--warn)}
.chip.ai{background:#DDEBDD;color:#2F5D32}
.todo{margin-top:12px;font-size:.93rem}
.aitext{margin-top:10px;font-size:.93rem;padding:8px 12px;background:#EEF4EE;border-radius:4px}
.src{margin-top:14px;font-size:.78rem;color:var(--muted)}
.src a{color:var(--accent)}
.note{border-left:3px solid var(--accent);background:var(--accent-soft);padding:9px 14px;margin:0 0 8px;font-size:.9rem;border-radius:0 4px 4px 0}
.note.warn{border-left-color:var(--warn);background:var(--warn-soft)}
.mode{display:inline-block;font-size:.78rem;color:var(--muted);border:1px solid var(--line);border-radius:20px;padding:2px 12px;margin-bottom:12px}
.route{background:var(--paper);border:1px solid var(--line);border-radius:6px;padding:18px 22px;margin:6px 0 16px}
.step{position:relative;padding:0 0 16px 28px;border-left:2px solid var(--accent);margin-left:6px}
.step:last-child{border-left-color:transparent;padding-bottom:0}
.step::before{content:"";position:absolute;left:-7px;top:3px;width:12px;height:12px;background:var(--accent);border-radius:50%}
.step .t{font-weight:600}
.step .d{color:var(--muted);font-size:.85rem}
.legend{font-size:.78rem;color:var(--muted);margin-top:10px}
.stButton>button{border-radius:4px;border:1px solid var(--line);font-weight:500}
.stButton>button[kind="primary"]{background:var(--accent);border-color:var(--accent);color:#fff}
</style>
"""

KIND_CHIP = {"POI": ("OSM", "poi"), "CALC": ("расчёт", "calc"), "IDEA": ("идея", "idea"),
             "AI": ("ИИ", "ai"), "UNKNOWN": ("нет данных", "unknown")}
CONF_LABEL = {"high": "высокая", "medium": "средняя", "low": "низкая"}


def esc(x):
    return html.escape(str(x or ""), quote=True)


def chip(kind):
    label, cls = KIND_CHIP[kind]
    return f'<span class="chip {cls}">{label}</span>'


def safe_url(url):
    return esc(url) if str(url or "").startswith(("http://", "https://")) else ""


def brand_html():
    return ('<div class="brand"><span class="name">Astana Walk AI</span>'
            '<span class="tag">Помощник по прогулкам в Астане · команда Unsurprised</span></div>')


def note_html(text, warn=False):
    return f'<div class="note{" warn" if warn else ""}">{esc(text)}</div>'


def card_html(it, n):
    sub = esc(it["category_label"]) + (f" · {esc(it['address'])}" if it.get("address") else "")
    sub += f" · полнота данных: {CONF_LABEL.get(it['confidence'], '')}"
    why = "".join(f'<li class="{"unknown" if w["kind"] == "UNKNOWN" else ""}">{esc(w["text"])}{chip(w["kind"])}</li>'
                  for w in it["why"])
    ai = f'<div class="aitext">{esc(it["ai_text"])}{chip("AI")}</div>' if it.get("ai_text") else ""
    src = it["source"]
    url = safe_url(src.get("url"))
    site = safe_url(it.get("website"))
    src_html = (f'Источник: <a href="{url}" target="_blank" rel="noopener">{esc(src.get("name"))}</a>, '
                f'получено {esc((src.get("fetched_at") or "")[:10])}') if url else "Источник: не указан"
    if site:
        src_html += f' · <a href="{site}" target="_blank" rel="noopener">сайт места</a>'
    return f"""<div class="card">
<div class="card-head"><div class="idx">{n}</div><div><div class="name">{esc(it['name'])}</div><div class="sub">{sub}</div></div></div>
<div class="stats">
<div class="stat"><b>≈{it['straight_m']:.0f} м</b><span>по прямой</span></div>
<div class="stat"><b>≈{it['walk_min']} мин</b><span>пешком</span></div>
<div class="stat"><b>≈{it['visit_min']} мин</b><span>на месте</span></div></div>
<div class="label">Почему это место</div><ul class="why">{why}</ul>{ai}
<div class="todo"><span class="label">Что делать</span><br>{esc(it['what_to_do']['text'])}{chip('IDEA')}</div>
<div class="src">{src_html}</div></div>"""


def route_html(route):
    steps = []
    for leg, stop in zip(route["legs"], route["stops"]):
        how = "маршрут OSRM" if leg["method"] == "osrm" else "оценка"
        steps.append(f'<div class="step"><div class="t">{esc(stop["name"])}</div>'
                     f'<div class="d">дорога ≈{leg["distance_m"]:.0f} м, ≈{leg["walk_min"]} мин ({how}); на месте ≈{stop["visit_min"]} мин</div></div>')
    total = (f'Итого ≈ {route["total_min"]} мин из {route["budget_min"]}: ходьба {route["walk_min"]}, визиты {route["visit_min"]}. '
             f'{esc(route.get("note", ""))}')
    return f'<div class="route"><div class="label" style="margin-top:0">Мини-маршрут</div>{"".join(steps)}<div class="legend">{total}</div></div>'


def legend_html():
    return ('<div class="legend">Метки: ' + " ".join(chip(k) for k in ("POI", "CALC", "IDEA", "AI", "UNKNOWN")) +
            ' Расстояние — по прямой или оценка, а не точный маршрут, если не указано «OSRM».</div>')
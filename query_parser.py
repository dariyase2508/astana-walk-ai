import re
from dataclasses import dataclass, field
from typing import Optional

from landmarks import find_landmark

KK_ONLY = set("әіңғүұқөһ")

INTENTS = [
    ("coffee", r"кофе|кофейн|\bкафе\b|coffee|\bcafe\b|\bчай\b|\btea\b|кофехаус", {"cafe": 1.0}, {}),
    ("food", r"поесть|покушать|обед|ужин|завтрак|ресторан|голод|\beat\b|\bfood\b|lunch|dinner|restaurant|hungry|тамақ",
     {"restaurant": 1.0, "cafe": 0.6}, {}),
    ("work", r"поработ|работать|ноутбук|розетк|wi-?fi|вай-?фай|laptop|\bwork\b|remote|учит|study|жұмыс",
     {"cafe": 1.0, "library": 0.9}, {"work": True}),
    ("quiet", r"\bтих|спокойн|quiet|\bcalm|без шума|тыныш", {"cafe": 0.4, "library": 0.8, "park": 0.5}, {"quiet": True}),
    ("park", r"\bпарк|сквер|погуля|прогулк|\bwalk|stroll|\bpark\b|nature|природ|саябақ|серуен",
     {"park": 1.0, "viewpoint": 0.5, "monument": 0.4}, {}),
    ("museum", r"музе|museum|выставк|exhibit|gallery|галере|мұражай", {"museum": 1.0, "gallery": 0.9, "culture": 0.5}, {}),
    ("kids", r"ребен|дет[еи]\b|детск|дочь|\bсын|\bkid|child|\bbaby|toddler|бала",
     {"playground": 1.0, "zoo": 0.9, "entertainment": 0.9, "museum": 0.6, "park": 0.7}, {"child": True}),
    ("unusual", r"необычн|уникальн|unusual|unique|weird|hidden|скрыт|нестандарт|something different|особенн",
     {"attraction": 1.0, "viewpoint": 0.8, "artwork": 0.8, "gallery": 0.7, "museum": 0.6, "monument": 0.5}, {"unusual": True}),
    ("photo", r"фото|снимк|красив|instagram|photo|\bview\b|\bвид\b|панорам|закат|sunset|сурет",
     {"viewpoint": 1.0, "attraction": 0.9, "monument": 0.7, "artwork": 0.6, "park": 0.5}, {"photo": True}),
    ("tourist", r"турист|достопримечат|посмотреть|sightsee|tourist|осмотр|экскурс|көрікті|see in",
     {"attraction": 1.0, "monument": 0.9, "museum": 0.8, "viewpoint": 0.8, "park": 0.3}, {"tourist": True}),
    ("night", r"ноч|вечер|поздно|\bnight|\blate\b|tonight|\bбар\b|\bклуб|\bclub|кино|cinema|movie",
     {"nightlife": 1.0, "cinema": 0.9, "restaurant": 0.4, "culture": 0.4}, {"night": True}),
    ("shopping", r"магазин|шопинг|торговый|\bmall\b|shopping", {"mall": 1.0}, {}),
    ("fun", r"развлеч|веселить|\bfun\b|entertain|аттракцион", {"entertainment": 1.0, "cinema": 0.6, "attraction": 0.5}, {}),
]

GROUP_WORDS = {"двое": 2, "двоих": 2, "вдвоем": 2, "трое": 3, "троих": 3, "втроем": 3, "четверо": 4,
               "четверых": 4, "вчетвером": 4, "пятеро": 5, "пятерых": 5, "впятером": 5, "шестеро": 6}
WORD_NUM = {"полтора": 1.5, "два": 2, "две": 2, "три": 3, "четыре": 4, "пять": 5,
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5}


@dataclass
class ParsedQuery:
    raw: str = ""
    language: str = "ru"
    supported: bool = True
    categories: dict = field(default_factory=dict)
    intents: list = field(default_factory=list)
    minutes: Optional[int] = None
    group_size: Optional[int] = None
    landmark: Optional[str] = None
    work: bool = False
    quiet: bool = False
    child: bool = False
    unusual: bool = False
    photo: bool = False
    tourist: bool = False
    night: bool = False
    wheelchair: bool = False
    free: bool = False
    flight: bool = False
    events: bool = False
    car: bool = False
    route_words: bool = False


def normalize(text):
    return (text or "").lower().replace("ё", "е").strip()


def detect_language(text):
    letters = [c for c in normalize(text) if c.isalpha()]
    if not letters:
        return "unknown"
    cyr = sum(("а" <= c <= "я") or c in KK_ONLY for c in letters)
    lat = sum("a" <= c <= "z" for c in letters)
    if cyr == 0 and lat == 0:
        return "unsupported"
    if cyr >= lat:
        return "kk" if any(c in KK_ONLY for c in letters) else "ru"
    return "en"


def parse_minutes(t):
    m = re.search(r"(?<![\d.])(\d{1,3})\s*[-–—]\s*(\d{1,3})\s*(?:мин|min)", t)
    if m:
        return int(m.group(2))
    m = re.search(r"(?<![\d.])(\d{1,2}(?:[.,]\d)?)\s*[-–—]\s*(\d{1,2}(?:[.,]\d)?)\s*(?:час|ч\b|hour|hr|h\b|сағат)", t)
    if m:
        return int(float(m.group(2).replace(",", ".")) * 60)
    m = re.search(r"(?<![\d.])(\d{1,2}(?:[.,]\d)?)\s*(?:час|ч\b|hours?\b|hrs?\b|h\b|сағат)", t)
    if m:
        return int(float(m.group(1).replace(",", ".")) * 60)
    m = re.search(r"(?<![\d.])(\d{1,3})\s*(?:мин|min)", t)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(полтора|два|две|три|четыре|пять|one|two|three|four|five)\s+(?:час|hour)", t)
    if m:
        return int(WORD_NUM[m.group(1)] * 60)
    if re.search(r"полчаса|half an hour|half hour", t):
        return 30
    if re.search(r"\bна час\b|\bчас\b|an hour|one hour", t):
        return 60
    return None


def parse_group(t):
    m = re.search(r"\bнас\s+(\d{1,2})\b", t) or re.search(r"(\d{1,2})\s*(?:человек|чел\b|люд|people|persons|друз|friends)", t) \
        or re.search(r"group of (\d{1,2})", t) or re.search(r"\bwe are (\d{1,2})\b", t)
    if m:
        n = int(m.group(1))
        return n if 1 <= n <= 30 else None
    for word, n in GROUP_WORDS.items():
        if re.search(r"\b" + word + r"\b", t):
            return n
    return None


def parse_query(text):
    t = normalize(text)
    lang = detect_language(text)
    pq = ParsedQuery(raw=text or "", language=lang if lang not in ("unknown", "unsupported") else "ru")
    if lang == "unsupported":
        pq.supported = False
        return pq
    for name, rx, cats, flags in INTENTS:
        if re.search(rx, t):
            pq.intents.append(name)
            for c, w in cats.items():
                pq.categories[c] = max(pq.categories.get(c, 0), w)
            for f, v in flags.items():
                setattr(pq, f, v)
    pq.minutes = parse_minutes(t)
    pq.group_size = parse_group(t)
    pq.landmark = find_landmark(t)
    pq.wheelchair = bool(re.search(r"коляск|инвалид|маломобил|wheelchair|accessible|ограниченн\w+ подвижн|мүгедек", t))
    pq.free = bool(re.search(r"бесплатн|\bfree\b|даром|тегін", t))
    pq.flight = bool(re.search(r"вылет|рейс|самолет|\bflight|departure|before my plane|до посадки", t))
    pq.events = bool(re.search(r"мероприят|концерт|фестивал|\bevent|concert|festival|афиш|выставк|сейчас идет|идет сейчас|exhibition", t))
    pq.car = bool(re.search(r"на машине|на авто|такси|\bby car|\bdriving|\buber", t))
    pq.route_words = bool(re.search(r"маршрут|\broute|itinerary|план прогулки", t))
    if pq.minutes is not None:
        pq.minutes = max(10, min(480, pq.minutes))
    return pq
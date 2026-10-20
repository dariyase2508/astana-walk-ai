"""Разбор часов работы OSM (opening_hours). Поддерживаем простые форматы.
Всё, что не удалось разобрать надёжно, возвращает "unknown" — мы не гадаем."""
import re

DAYS = ["mo", "tu", "we", "th", "fr", "sa", "su"]
_TIMES_RE = re.compile(r"\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}(?:\s*,\s*\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2})*")
_INTERVAL_RE = re.compile(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})")


def _expand_days(spec):
    days = set()
    for part in spec.split(","):
        part = part.strip().lower()
        if not part:
            return None
        if "-" in part:
            a, b = [x.strip() for x in part.split("-", 1)]
            if a not in DAYS or b not in DAYS:
                return None
            k, j = DAYS.index(a), DAYS.index(b)
            while True:
                days.add(k)
                if k == j:
                    break
                k = (k + 1) % 7
        else:
            if part not in DAYS:
                return None
            days.add(DAYS.index(part))
    return days


def parse_hours(text):
    """Возвращает "always", словарь {день: [(старт, конец), ...]} (минуты) или None."""
    s = (text or "").strip()
    if not s:
        return None
    if s.lower() == "24/7":
        return "always"
    table = {d: [] for d in range(7)}
    for rule in s.split(";"):
        rule = rule.strip()
        if not rule:
            continue
        if rule[0].isdigit():
            days, times = set(range(7)), rule
        else:
            parts = rule.split(None, 1)
            if len(parts) < 2:
                return None
            days = _expand_days(parts[0])
            times = parts[1].strip()
            if days is None:
                return None
        if times.lower() in ("off", "closed"):
            intervals = []
        elif _TIMES_RE.fullmatch(times):
            intervals = []
            for h1, m1, h2, m2 in _INTERVAL_RE.findall(times):
                start = int(h1) * 60 + int(m1)
                end = int(h2) * 60 + int(m2)
                if end <= start:
                    end += 1440  # заканчивается после полуночи
                intervals.append((start, end))
        else:
            return None
        for d in days:
            table[d] = intervals
    return table


def check_open(opening_hours, when):
    """Возвращает (состояние, пояснение). Состояние: open | closed | unknown."""
    if not opening_hours:
        return "unknown", "no_hours"
    table = parse_hours(opening_hours)
    if table is None:
        return "unknown", "unparsed"
    if table == "always":
        return "open", "24/7"
    day = when.weekday()
    t = when.hour * 60 + when.minute
    for s, e in table[day]:
        if s <= t < e:
            return "open", "ok"
    for s, e in table[(day - 1) % 7]:
        if e > 1440 and s <= t + 1440 < e:
            return "open", "ok"
    return "closed", "ok"

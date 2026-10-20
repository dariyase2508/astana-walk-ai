"""Необязательная генерация текста языковой моделью (Google Gemini, бесплатный ключ).
Без ключа проект работает в режиме шаблонов — это честно показывается в интерфейсе.

Что уходит во внешний сервис: ТОЛЬКО текст запроса и данные найденных мест
(название, категория, расстояние, время). Координаты пользователя НЕ отправляются.

Любой ответ модели проходит проверку (verify): выдуманные числа и неподтверждённые
утверждения отбрасываются, и для такого места остаётся шаблонное объяснение."""
import json
import os
import re

import requests

from config import BASE_DIR

DEFAULT_MODEL = "gemini-2.5-flash"


def _load_env():
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def api_key():
    _load_env()
    return os.environ.get("GEMINI_API_KEY", "").strip()


def is_available():
    return bool(api_key())


def build_prompt(query, items, lang):
    ctx = [{"id": i["id"], "name": i["name"], "category": i["category_label"], "distance_m": i["distance_m"],
            "walk_min": i["walk_min"], "visit_min": i["visit_min"], "open_state": i["open_state"],
            "opening_hours": i["opening_hours"] or "unknown"} for i in items]
    language = "English" if lang == "en" else "русском языке"
    return (
        "You are a careful city-walk assistant for Astana. Use ONLY the facts in CONTEXT.\n"
        "Rules: do not invent places, numbers, prices, events, power outlets, Wi-Fi or opening status. "
        "If something is not in CONTEXT, do not mention it. Use only numbers that appear in CONTEXT.\n"
        f"Write for each place 1-2 short sentences on why it fits the request, in {language}.\n"
        'Reply with JSON only: {"<id>": "<text>", ...}\n'
        f"REQUEST: {query}\nCONTEXT: {json.dumps(ctx, ensure_ascii=False)}"
    )


def call_gemini(prompt, timeout=20):
    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"}}
    r = requests.post(url, json=body, headers={"x-goog-api-key": api_key()}, timeout=timeout)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


_NUM_RE = re.compile(r"\d+")
_SOCKET_RE = re.compile(r"розетк|socket|outlet|power plug|charging", re.I)
_EVENT_RE = re.compile(r"сейчас идёт|сейчас идет|проходит выставк|today.s (event|exhibition)|currently (showing|on)", re.I)
_OPEN_RE = re.compile(r"открыт|сейчас работает|\bis open\b|open now|работает до", re.I)


def verify(data, items):
    """Проверяет JSON модели. Возвращает ({id: текст}, [проблемы]). Плохие тексты отбрасываются."""
    problems, clean = [], {}
    if not isinstance(data, dict):
        return {}, ["ответ модели — не JSON-объект"]
    by_id = {i["id"]: i for i in items}
    for pid, text in data.items():
        item = by_id.get(pid)
        if item is None:
            problems.append(f"неизвестный id: {pid}")
            continue
        if not isinstance(text, str) or not text.strip() or len(text) > 500:
            problems.append(f"{pid}: пустой или слишком длинный текст")
            continue
        allowed = {str(item["distance_m"]), str(item["walk_min"]), str(item["visit_min"])}
        allowed |= set(_NUM_RE.findall(item["name"])) | set(_NUM_RE.findall(item["opening_hours"] or ""))
        bad = [n for n in _NUM_RE.findall(text) if n not in allowed]
        if bad:
            problems.append(f"{pid}: числа вне данных: {bad}")
            continue
        if _SOCKET_RE.search(text) and not item.get("has_power"):
            problems.append(f"{pid}: утверждение про розетки без данных")
            continue
        if _EVENT_RE.search(text):
            problems.append(f"{pid}: утверждение о событиях без данных")
            continue
        if _OPEN_RE.search(text) and item["open_state"] != "open":
            problems.append(f"{pid}: утверждение об открытости без данных")
            continue
        clean[pid] = text.strip()
    return clean, problems


def explain(query, items, lang):
    """Возвращает ({id: текст}, статус). Любая ошибка -> пустой словарь (будет шаблонный режим)."""
    if not is_available():
        return {}, "no_key"
    try:
        raw = call_gemini(build_prompt(query, items, lang))
        data = json.loads(re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip())
    except Exception as exc:
        return {}, f"error:{exc.__class__.__name__}"
    clean, problems = verify(data, items)
    status = "ok" if clean and not problems else ("partial" if clean else "rejected")
    return clean, status

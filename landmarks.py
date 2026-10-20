LANDMARKS = {
    "expo": {"ru": "EXPO 2017 (Нур-Алем)", "en": "EXPO 2017 (Nur Alem)", "lat": 51.0894, "lon": 71.4162,
             "aliases": ["expo 2017", "expo", "экспо", "нур-алем", "нур алем", "nur alem", "nur-alem"]},
    "megasilkway": {"ru": "Mega Silk Way", "en": "Mega Silk Way", "lat": 51.0890, "lon": 71.4034,
                    "aliases": ["mega silk way", "мега силк вей", "мега силк вэй", "мега сил вей", "silk way"]},
    "baiterek": {"ru": "Байтерек", "en": "Baiterek", "lat": 51.1283, "lon": 71.4305,
                 "aliases": ["байтерек", "baiterek"]},
    "khanshatyr": {"ru": "Хан Шатыр", "en": "Khan Shatyr", "lat": 51.1327, "lon": 71.4037,
                    "aliases": ["хан шатыр", "khan shatyr"]},
    "airport": {"ru": "Аэропорт Астаны", "en": "Astana Airport", "lat": 51.0222, "lon": 71.4669,
                "aliases": ["аэропорт", "airport"]},
    "station": {"ru": "Вокзал Нурлы Жол", "en": "Nurly Zhol station", "lat": 51.1427, "lon": 71.4094,
                "aliases": ["нурлы жол", "nurly zhol", "вокзал", "railway station"]},
}


def get_landmark(key):
    return LANDMARKS.get(key)


def find_landmark(text):
    low = (text or "").lower().replace("ё", "е")
    best_key, best_len = None, 0
    for key, info in LANDMARKS.items():
        for alias in info["aliases"]:
            if alias in low and len(alias) > best_len:
                best_key, best_len = key, len(alias)
    return best_key
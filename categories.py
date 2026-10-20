"""Единый справочник категорий: подписи, ключевые слова для поиска, время визита, идеи."""

CATEGORY_INFO = {
    "cafe": {"ru": "Кафе", "en": "Cafe", "kk": "Кафе",
             "keywords": "кафе кофейня кофе coffee cafe чай tea", "visit_min": 40,
             "idea_ru": "Возьмите напиток и посидите; тишину, Wi-Fi и розетки проверьте на месте, если они важны.",
             "idea_en": "Grab a drink and sit down; check quietness, Wi-Fi and power outlets on site if they matter."},
    "restaurant": {"ru": "Ресторан / фастфуд", "en": "Restaurant / fast food", "kk": "Мейрамхана",
                   "keywords": "ресторан еда поесть обед ужин restaurant food lunch dinner", "visit_min": 60,
                   "idea_ru": "Поешьте на месте; меню и цены смотрите на месте.",
                   "idea_en": "Eat on site; check the menu and prices there."},
    "park": {"ru": "Парк / сквер", "en": "Park / garden", "kk": "Саябақ",
             "keywords": "парк сквер сад прогулка гулять природа park garden walk nature", "visit_min": 45,
             "idea_ru": "Неспешная прогулка по территории парка.",
             "idea_en": "A relaxed stroll around the park."},
    "playground": {"ru": "Детская площадка", "en": "Playground", "kk": "Балалар алаңы",
                   "keywords": "детская площадка дети ребенок playground kids children", "visit_min": 30,
                   "idea_ru": "Дайте ребёнку поиграть; безопасность и возрастные ограничения оценивайте на месте.",
                   "idea_en": "Let the child play; judge safety and age suitability on site."},
    "museum": {"ru": "Музей", "en": "Museum", "kk": "Мұражай",
               "keywords": "музей выставка экспозиция museum exhibition", "visit_min": 60,
               "idea_ru": "Осмотрите экспозицию; расписание и билеты уточните на сайте или по телефону.",
               "idea_en": "Explore the exhibition; check schedule and tickets on the website or by phone."},
    "gallery": {"ru": "Галерея", "en": "Gallery", "kk": "Галерея",
                "keywords": "галерея искусство выставка gallery art", "visit_min": 40,
                "idea_ru": "Посмотрите экспозицию; расписание уточните заранее.",
                "idea_en": "See the exhibition; check opening details in advance."},
    "attraction": {"ru": "Достопримечательность", "en": "Attraction", "kk": "Көрікті жер",
                   "keywords": "достопримечательность необычное архитектура attraction sight landmark unique", "visit_min": 30,
                   "idea_ru": "Осмотрите объект и сделайте фотографии.",
                   "idea_en": "See the site and take photos."},
    "viewpoint": {"ru": "Смотровая площадка", "en": "Viewpoint", "kk": "Көру алаңы",
                  "keywords": "смотровая площадка вид панорама фото закат viewpoint view panorama photo sunset", "visit_min": 20,
                  "idea_ru": "Насладитесь видом и сделайте фотографии; лучше в светлое время суток.",
                  "idea_en": "Enjoy the view and take photos; best in daylight."},
    "monument": {"ru": "Памятник / мемориал", "en": "Monument / memorial", "kk": "Ескерткіш",
                 "keywords": "памятник монумент мемориал monument memorial statue", "visit_min": 15,
                 "idea_ru": "Короткая остановка: осмотрите и прочитайте табличку.",
                 "idea_en": "A short stop: take a look and read the plaque."},
    "artwork": {"ru": "Арт-объект", "en": "Artwork", "kk": "Өнер туындысы",
                "keywords": "арт объект скульптура искусство artwork sculpture art", "visit_min": 10,
                "idea_ru": "Быстрая остановка для фото.", "idea_en": "A quick photo stop."},
    "zoo": {"ru": "Зоопарк / аквариум", "en": "Zoo / aquarium", "kk": "Хайуанаттар бағы",
            "keywords": "зоопарк аквариум животные дети zoo aquarium animals kids", "visit_min": 90,
            "idea_ru": "Планируйте длинное посещение; билеты и часы уточните заранее.",
            "idea_en": "Plan a long visit; check tickets and hours in advance."},
    "entertainment": {"ru": "Развлечения", "en": "Entertainment", "kk": "Ойын-сауық",
                      "keywords": "развлечения аттракционы парк аттракционов дети fun entertainment theme park kids", "visit_min": 90,
                      "idea_ru": "Проверьте цены и режим работы заранее.",
                      "idea_en": "Check prices and opening hours in advance."},
    "cinema": {"ru": "Кинотеатр", "en": "Cinema", "kk": "Кинотеатр",
               "keywords": "кино кинотеатр фильм вечер cinema movie night", "visit_min": 120,
               "idea_ru": "Актуального расписания сеансов в базе нет — проверьте афишу на сайте.",
               "idea_en": "There is no live showtime data in our database — check the cinema's website."},
    "culture": {"ru": "Театр / арт-центр", "en": "Theatre / arts centre", "kk": "Театр / өнер орталығы",
                "keywords": "театр арт центр культура спектакль theatre arts centre culture", "visit_min": 90,
                "idea_ru": "Афишу и билеты проверьте на сайте — актуальных данных о событиях в базе нет.",
                "idea_en": "Check the programme and tickets online — we have no live event data."},
    "library": {"ru": "Библиотека", "en": "Library", "kk": "Кітапхана",
                "keywords": "библиотека тихо читать работать library quiet study work", "visit_min": 60,
                "idea_ru": "Тихое место для работы или чтения; правила посещения уточните.",
                "idea_en": "A quiet place to work or read; check visiting rules."},
    "nightlife": {"ru": "Бар / ночной клуб", "en": "Bar / nightclub", "kk": "Бар / түнгі клуб",
                  "keywords": "бар паб клуб ночь вечер bar pub club night nightlife", "visit_min": 90,
                  "idea_ru": "Проверьте часы работы и возрастные ограничения (18+) заранее.",
                  "idea_en": "Check opening hours and age limits (18+) in advance."},
    "mall": {"ru": "Торговый центр", "en": "Shopping mall", "kk": "Сауда орталығы",
             "keywords": "торговый центр молл магазины mall shopping", "visit_min": 60,
             "idea_ru": "Прогулка по торговому центру; режим работы уточните.",
             "idea_en": "A walk through the mall; check opening hours."},
    "market": {"ru": "Рынок", "en": "Market", "kk": "Базар",
               "keywords": "рынок базар market bazaar", "visit_min": 40,
               "idea_ru": "Прогулка по рынку; режим работы уточните.",
               "idea_en": "Browse the market; check opening hours."},
}

# Категории, которые мы считаем "обычно бесплатными" (это эвристика, не факт!)
FREE_LIKELY = {"park", "playground", "viewpoint", "monument", "artwork", "attraction"}
PAID_LIKELY = {"cafe", "restaurant", "cinema", "nightlife", "mall", "zoo", "entertainment"}


def category_label(cat, lang="ru"):
    info = CATEGORY_INFO.get(cat)
    if not info:
        return cat
    return info.get(lang) or info["ru"]


def visit_minutes(cat):
    return CATEGORY_INFO.get(cat, {}).get("visit_min", 30)


def idea_text(cat, lang="ru"):
    info = CATEGORY_INFO.get(cat, {})
    return info.get("idea_en" if lang == "en" else "idea_ru", "")

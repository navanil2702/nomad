"""Offline local-knowledge tables: phrases, emergency numbers, FX, plugs."""

from __future__ import annotations

from typing import Any

# Indicative rates from 1 USD. Replaced by a live FX call if one is wired up.
CURRENCY_RATES: dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.78,
    "JPY": 151.0,
    "IDR": 15800.0,
    "INR": 83.2,
    "AUD": 1.52,
    "CAD": 1.36,
    "THB": 36.0,
    "SGD": 1.34,
}

CURRENCY_SYMBOLS: dict[str, str] = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "IDR": "Rp",
    "INR": "₹",
    "AUD": "A$",
    "CAD": "C$",
    "THB": "฿",
    "SGD": "S$",
}

PHRASES: dict[str, list[dict[str, str]]] = {
    "Japanese": [
        {"english": "Hello", "local": "こんにちは", "pronunciation": "kon-nichi-wa"},
        {"english": "Thank you", "local": "ありがとうございます", "pronunciation": "a-ri-ga-to go-zai-mas"},
        {"english": "Excuse me", "local": "すみません", "pronunciation": "su-mi-ma-sen"},
        {"english": "How much is this?", "local": "いくらですか", "pronunciation": "i-ku-ra des-ka"},
        {"english": "I'm vegetarian", "local": "ベジタリアンです", "pronunciation": "be-ji-ta-ri-an des"},
        {"english": "Where is the station?", "local": "駅はどこですか", "pronunciation": "eki wa doko des-ka"},
        {"english": "Help!", "local": "助けて", "pronunciation": "tas-ke-te"},
        {"english": "The bill, please", "local": "お会計お願いします", "pronunciation": "o-kai-kei o-ne-gai shi-mas"},
    ],
    "French": [
        {"english": "Hello", "local": "Bonjour", "pronunciation": "bon-zhoor"},
        {"english": "Thank you", "local": "Merci", "pronunciation": "mair-see"},
        {"english": "Excuse me", "local": "Excusez-moi", "pronunciation": "ex-kew-zay mwah"},
        {"english": "How much is this?", "local": "C'est combien ?", "pronunciation": "say kom-bee-en"},
        {"english": "I'm vegetarian", "local": "Je suis végétarien", "pronunciation": "zhuh swee vay-zhay-ta-ree-en"},
        {"english": "Where is the metro?", "local": "Où est le métro ?", "pronunciation": "oo ay luh may-tro"},
        {"english": "Help!", "local": "Au secours !", "pronunciation": "oh suh-koor"},
        {"english": "The bill, please", "local": "L'addition, s'il vous plaît", "pronunciation": "la-dee-syon seel voo play"},
    ],
    "Indonesian": [
        {"english": "Hello", "local": "Halo", "pronunciation": "ha-lo"},
        {"english": "Thank you", "local": "Terima kasih", "pronunciation": "tuh-ree-ma ka-see"},
        {"english": "Excuse me", "local": "Permisi", "pronunciation": "per-mee-see"},
        {"english": "How much is this?", "local": "Berapa harganya?", "pronunciation": "buh-ra-pa har-ga-nya"},
        {"english": "I'm vegetarian", "local": "Saya vegetarian", "pronunciation": "sa-ya ve-ge-ta-ri-an"},
        {"english": "Where is the beach?", "local": "Di mana pantai?", "pronunciation": "dee ma-na pan-tai"},
        {"english": "Help!", "local": "Tolong!", "pronunciation": "to-long"},
        {"english": "Too expensive", "local": "Terlalu mahal", "pronunciation": "ter-la-lu ma-hal"},
    ],
    "Italian": [
        {"english": "Hello", "local": "Ciao", "pronunciation": "chow"},
        {"english": "Thank you", "local": "Grazie", "pronunciation": "grat-see-eh"},
        {"english": "Excuse me", "local": "Scusi", "pronunciation": "skoo-zee"},
        {"english": "How much is this?", "local": "Quanto costa?", "pronunciation": "kwan-to kos-ta"},
        {"english": "I'm vegetarian", "local": "Sono vegetariano", "pronunciation": "so-no ve-je-ta-ree-a-no"},
        {"english": "Where is the station?", "local": "Dov'è la stazione?", "pronunciation": "do-veh la stat-see-o-neh"},
        {"english": "Help!", "local": "Aiuto!", "pronunciation": "ah-yoo-to"},
        {"english": "The bill, please", "local": "Il conto, per favore", "pronunciation": "eel kon-to per fa-vo-reh"},
    ],
    "Spanish": [
        {"english": "Hello", "local": "Hola", "pronunciation": "o-la"},
        {"english": "Thank you", "local": "Gracias", "pronunciation": "gra-see-as"},
        {"english": "Excuse me", "local": "Perdón", "pronunciation": "per-don"},
        {"english": "How much is this?", "local": "¿Cuánto cuesta?", "pronunciation": "kwan-to kwes-ta"},
        {"english": "I'm vegetarian", "local": "Soy vegetariano", "pronunciation": "soy ve-he-ta-ree-a-no"},
        {"english": "Where is the beach?", "local": "¿Dónde está la playa?", "pronunciation": "don-de es-ta la pla-ya"},
        {"english": "Help!", "local": "¡Ayuda!", "pronunciation": "a-yoo-da"},
        {"english": "The bill, please", "local": "La cuenta, por favor", "pronunciation": "la kwen-ta por fa-vor"},
    ],
    "Portuguese": [
        {"english": "Hello", "local": "Olá", "pronunciation": "o-la"},
        {"english": "Thank you", "local": "Obrigado", "pronunciation": "o-bri-ga-doo"},
        {"english": "Excuse me", "local": "Com licença", "pronunciation": "kong li-sen-sa"},
        {"english": "How much is this?", "local": "Quanto custa?", "pronunciation": "kwan-too koosh-ta"},
        {"english": "I'm vegetarian", "local": "Sou vegetariano", "pronunciation": "soh ve-zhe-ta-ree-a-noo"},
        {"english": "Where is the tram?", "local": "Onde é o elétrico?", "pronunciation": "on-de eh oo e-le-tri-koo"},
        {"english": "Help!", "local": "Socorro!", "pronunciation": "soo-ko-rroo"},
        {"english": "The bill, please", "local": "A conta, por favor", "pronunciation": "a kon-ta por fa-vor"},
    ],
    "Hindi": [
        {"english": "Hello", "local": "नमस्ते", "pronunciation": "na-mas-tay"},
        {"english": "Thank you", "local": "धन्यवाद", "pronunciation": "dhan-ya-vaad"},
        {"english": "Excuse me", "local": "सुनिए", "pronunciation": "su-ni-ye"},
        {"english": "How much is this?", "local": "यह कितने का है?", "pronunciation": "yeh kit-ne ka hai"},
        {"english": "Too expensive", "local": "बहुत महंगा है", "pronunciation": "ba-hut ma-hen-ga hai"},
        {"english": "I'm vegetarian", "local": "मैं शाकाहारी हूँ", "pronunciation": "main shaa-ka-haa-ree hoon"},
        {"english": "No spice, please", "local": "मिर्च मत डालिए", "pronunciation": "mirch mat daa-li-ye"},
        {"english": "Where is the station?", "local": "स्टेशन कहाँ है?", "pronunciation": "station ka-haan hai"},
        {"english": "Water, please", "local": "पानी दीजिए", "pronunciation": "paa-nee dee-ji-ye"},
        {"english": "Help!", "local": "मदद कीजिए", "pronunciation": "ma-dad kee-ji-ye"},
    ],
    "English": [
        {"english": "Hello", "local": "Hello", "pronunciation": "heh-loh"},
        {"english": "Thank you", "local": "Thank you", "pronunciation": "thank-yoo"},
        {"english": "Excuse me", "local": "Excuse me", "pronunciation": "ex-kyooz mee"},
        {"english": "How much is this?", "local": "How much is this?", "pronunciation": "how much iz this"},
        {"english": "I'm vegetarian", "local": "I'm vegetarian", "pronunciation": "im vej-uh-tair-ee-uhn"},
        {"english": "Help!", "local": "Help!", "pronunciation": "help"},
    ],
}

EMERGENCY: dict[str, list[dict[str, str]]] = {
    "Japan": [
        {"label": "Police", "number": "110", "note": "Free from any phone"},
        {"label": "Ambulance & Fire", "number": "119", "note": "Say 'kyukyusha' for ambulance"},
        {"label": "Japan Visitor Hotline", "number": "050-3816-2787", "note": "24/7, English"},
    ],
    "France": [
        {"label": "All emergencies (EU)", "number": "112", "note": "Works from any EU phone"},
        {"label": "Police", "number": "17", "note": ""},
        {"label": "Ambulance (SAMU)", "number": "15", "note": ""},
    ],
    "Indonesia": [
        {"label": "Police", "number": "110", "note": ""},
        {"label": "Ambulance", "number": "118", "note": ""},
        {"label": "Bali Tourist Police", "number": "+62 361 754599", "note": "English speaking"},
    ],
    "Italy": [
        {"label": "All emergencies (EU)", "number": "112", "note": "Works from any EU phone"},
        {"label": "Ambulance", "number": "118", "note": ""},
        {"label": "Tourist Police Rome", "number": "+39 06 46861", "note": ""},
    ],
    "Spain": [
        {"label": "All emergencies (EU)", "number": "112", "note": "English available"},
        {"label": "National Police", "number": "091", "note": ""},
        {"label": "Barcelona Tourist Attention", "number": "+34 932 562 430", "note": "Theft reports"},
    ],
    "Portugal": [
        {"label": "All emergencies (EU)", "number": "112", "note": "English available"},
        {"label": "Tourist Police Lisbon", "number": "+351 213 421 634", "note": "Praça dos Restauradores"},
        {"label": "Health line SNS24", "number": "808 24 24 24", "note": ""},
    ],
    "India": [
        {"label": "All emergencies (ERSS)", "number": "112", "note": "Single number, works from any phone incl. locked SIM"},
        {"label": "Police", "number": "100", "note": ""},
        {"label": "Fire", "number": "101", "note": ""},
        {"label": "Ambulance", "number": "102", "note": "108 in most states, and usually faster"},
        {"label": "Tourist helpline", "number": "1800-11-1363", "note": "24/7, Ministry of Tourism, 12 languages"},
        {"label": "Women's helpline", "number": "1091", "note": "24/7, nationwide"},
        {"label": "Railway helpline", "number": "139", "note": "Enquiries, delays and on-train emergencies"},
        {"label": "Disaster / NDRF", "number": "1078", "note": "Floods, landslides, cyclones"},
    ],
}

EMERGENCY["India"] = [
    {
        "label": "All emergencies (ERSS)",
        "number": "112",
        "note": "One number for police, fire and ambulance, nationwide",
    },
    {"label": "Police", "number": "100", "note": ""},
    {
        "label": "Ambulance",
        "number": "102",
        "note": "108 also reaches emergency medical services in most states",
    },
    {"label": "Fire", "number": "101", "note": ""},
    {
        "label": "Tourist helpline",
        "number": "1800-11-1363",
        "note": "Ministry of Tourism, 24/7, multilingual",
    },
    {"label": "Women's helpline", "number": "1091", "note": ""},
    {
        "label": "Railway helpline",
        "number": "139",
        "note": "Enquiries, and emergencies on a train",
    },
]

# Countries beyond the curated six. Without these a live destination falls
# through to the generic list, which tells an Indian trip to dial 911.
EMERGENCY.update(
    {
        "United States": [
            {"label": "All emergencies", "number": "911", "note": ""},
        ],
        "USA": [{"label": "All emergencies", "number": "911", "note": ""}],
        "Canada": [{"label": "All emergencies", "number": "911", "note": ""}],
        "Mexico": [{"label": "All emergencies", "number": "911", "note": ""}],
        "United Kingdom": [
            {"label": "All emergencies", "number": "999", "note": "112 also works"},
            {"label": "Non-emergency police", "number": "101", "note": ""},
            {"label": "Non-emergency medical", "number": "111", "note": "NHS advice"},
        ],
        "Australia": [
            {"label": "All emergencies", "number": "000", "note": "112 from a mobile"},
        ],
        "New Zealand": [{"label": "All emergencies", "number": "111", "note": ""}],
        "Thailand": [
            {"label": "Tourist police", "number": "1155", "note": "English speaking"},
            {"label": "Police", "number": "191", "note": ""},
            {"label": "Ambulance", "number": "1669", "note": ""},
        ],
        "Singapore": [
            {"label": "Police", "number": "999", "note": ""},
            {"label": "Ambulance & Fire", "number": "995", "note": ""},
        ],
        "Malaysia": [
            {"label": "All emergencies", "number": "999", "note": "112 from a mobile"},
        ],
        "Vietnam": [
            {"label": "Police", "number": "113", "note": ""},
            {"label": "Fire", "number": "114", "note": ""},
            {"label": "Ambulance", "number": "115", "note": ""},
        ],
        "Nepal": [
            {"label": "Police", "number": "100", "note": ""},
            {"label": "Ambulance", "number": "102", "note": ""},
            {"label": "Tourist police", "number": "1144", "note": "Kathmandu"},
        ],
        "Sri Lanka": [
            {"label": "Police emergency", "number": "119", "note": ""},
            {"label": "Ambulance", "number": "1990", "note": "Suwa Seriya, free"},
        ],
        "United Arab Emirates": [
            {"label": "Police", "number": "999", "note": ""},
            {"label": "Ambulance", "number": "998", "note": ""},
            {"label": "Fire", "number": "997", "note": ""},
        ],
        "Turkey": [
            {"label": "All emergencies", "number": "112", "note": ""},
        ],
        "Egypt": [
            {"label": "Police", "number": "122", "note": ""},
            {"label": "Ambulance", "number": "123", "note": ""},
            {"label": "Tourist police", "number": "126", "note": ""},
        ],
        "Brazil": [
            {"label": "Police", "number": "190", "note": ""},
            {"label": "Ambulance", "number": "192", "note": ""},
        ],
        "Germany": [
            {"label": "All emergencies (EU)", "number": "112", "note": ""},
            {"label": "Police", "number": "110", "note": ""},
        ],
        "Netherlands": [
            {"label": "All emergencies (EU)", "number": "112", "note": ""},
        ],
        "Greece": [{"label": "All emergencies (EU)", "number": "112", "note": ""}],
        "Switzerland": [
            {"label": "Police", "number": "117", "note": ""},
            {"label": "Ambulance", "number": "144", "note": ""},
            {"label": "All emergencies", "number": "112", "note": ""},
        ],
    }
)

# Region-level contacts, for the cases where a state or city genuinely runs a
# service the national numbers do not reach.
#
# Deliberately sparse. Most countries — India especially — have centralised
# emergency dispatch, so there is no separate local number to publish: 112
# (ERSS) reaches police, fire and ambulance in every Indian state. Inventing a
# plausible-looking city number would be far worse than showing none, so this
# only carries services that verifiably exist and are separately reachable.
# The location-specific part travellers actually need is *where* the nearest
# hospital and police station are, which is derived from the trip's own
# coordinates in services/trips.py.
REGIONAL_EMERGENCY: dict[str, dict[str, list[dict[str, str]]]] = {
    "India": {
        # 108 is the free emergency-ambulance service, run state by state and
        # the number locals actually dial for a medical emergency.
        "*": [
            {
                "label": "Ambulance (108 service)",
                "number": "108",
                "note": "Free state-run emergency ambulance, dispatched locally",
            },
        ],
    },
    "Indonesia": {
        "Bali": [
            {
                "label": "Bali tourist police",
                "number": "+62 361 754599",
                "note": "English speaking",
            },
        ],
    },
    "Nepal": {
        "*": [
            {
                "label": "Tourist police",
                "number": "1144",
                "note": "Kathmandu, English speaking",
            },
        ],
    },
}


def regional_emergency(country: str, region: str, city: str) -> list[dict[str, str]]:
    """Contacts specific to a state or city, most specific first.

    Returns an empty list when nothing verified exists for the location, which
    is the common case and the correct answer.
    """
    by_region = REGIONAL_EMERGENCY.get(country)
    if not by_region:
        return []

    out: list[dict[str, str]] = []
    for key in (city, region):
        if key and key in by_region:
            out.extend(by_region[key])
    out.extend(by_region.get("*", []))

    # Preserve order while dropping duplicates.
    seen: set[str] = set()
    return [c for c in out if not (c["number"] in seen or seen.add(c["number"]))]


DEFAULT_EMERGENCY = [
    {"label": "International emergency", "number": "112", "note": "Routes to local services in most countries"},
    {"label": "US emergency", "number": "911", "note": "US, Canada and several others"},
    {"label": "Your embassy", "number": "Check before you fly", "note": "Save it offline on arrival"},
]

COUNTRY_META: dict[str, dict[str, Any]] = {
    "Japan": {"plug": "Type A/B, 100V", "tipping": "No tipping. It can cause genuine offence."},
    "France": {"plug": "Type E, 230V", "tipping": "Service is included. Round up for good service."},
    "Indonesia": {"plug": "Type C/F, 230V", "tipping": "10% in restaurants, small notes for drivers."},
    "Italy": {"plug": "Type F/L, 230V", "tipping": "Coperto is a cover charge, not a tip. 5-10% is generous."},
    "Spain": {"plug": "Type F, 230V", "tipping": "Rounding up is normal. 10% only for a big meal."},
    "Portugal": {"plug": "Type F, 230V", "tipping": "5-10% in restaurants, nothing in cafés."},
}

# Country -> absolute cost level, where 1.0 is a mid-priced Western European or
# US city.
#
# This exists because Google's `priceLevel` is *relative to the local market*:
# a "moderate" restaurant in Udaipur and one in Zurich are both PRICE_LEVEL_
# MODERATE despite differing by roughly ten times. Deriving a destination's
# cost level from price levels alone therefore prices every city as if it were
# in Western Europe. These are rough cost-of-living ratios, good enough to put
# an estimate in the right order of magnitude.
COUNTRY_COST_INDEX: dict[str, float] = {
    "Switzerland": 1.55, "Norway": 1.45, "Iceland": 1.40, "Denmark": 1.30,
    "United States": 1.15, "USA": 1.15, "Ireland": 1.15, "Australia": 1.10,
    "Singapore": 1.10, "United Kingdom": 1.10, "UK": 1.10, "Sweden": 1.05,
    "Netherlands": 1.05, "France": 1.05, "Austria": 1.00, "Belgium": 1.00,
    "Germany": 0.98, "Canada": 0.98, "New Zealand": 0.98, "Japan": 0.92,
    "Italy": 0.90, "Spain": 0.82, "South Korea": 0.80, "Greece": 0.78,
    "Portugal": 0.75, "Czechia": 0.68, "Croatia": 0.66, "Poland": 0.60,
    "United Arab Emirates": 0.90, "Israel": 1.05, "China": 0.55,
    "Turkey": 0.42, "Brazil": 0.42, "Mexico": 0.45, "South Africa": 0.42,
    "Malaysia": 0.38, "Thailand": 0.38, "Morocco": 0.36, "Peru": 0.36,
    "Colombia": 0.33, "Egypt": 0.28, "Vietnam": 0.30, "Indonesia": 0.32,
    "Philippines": 0.32, "Sri Lanka": 0.28, "India": 0.28, "Nepal": 0.26,
    "Pakistan": 0.25, "Bangladesh": 0.26,
}

DEFAULT_COUNTRY_COST_INDEX = 0.85

# Country -> (language, currency). Used when a destination comes from a live
# provider rather than the curated catalog, which carries its own values.
COUNTRY_PROFILE: dict[str, tuple[str, str]] = {
    "Japan": ("Japanese", "JPY"),
    "France": ("French", "EUR"),
    "Indonesia": ("Indonesian", "IDR"),
    "Italy": ("Italian", "EUR"),
    "Spain": ("Spanish", "EUR"),
    "Portugal": ("Portuguese", "EUR"),
    "Germany": ("German", "EUR"),
    "Netherlands": ("Dutch", "EUR"),
    "Greece": ("Greek", "EUR"),
    "Austria": ("German", "EUR"),
    "Belgium": ("Dutch", "EUR"),
    "Ireland": ("English", "EUR"),
    "United Kingdom": ("English", "GBP"),
    "UK": ("English", "GBP"),
    "United States": ("English", "USD"),
    "USA": ("English", "USD"),
    "Canada": ("English", "CAD"),
    "Australia": ("English", "AUD"),
    "New Zealand": ("English", "NZD"),
    "India": ("Hindi", "INR"),
    "Thailand": ("Thai", "THB"),
    "Singapore": ("English", "SGD"),
    "Vietnam": ("Vietnamese", "VND"),
    "Mexico": ("Spanish", "MXN"),
    "Brazil": ("Portuguese", "BRL"),
    "Turkey": ("Turkish", "TRY"),
    "Morocco": ("Arabic", "MAD"),
    "Egypt": ("Arabic", "EGP"),
    "South Africa": ("English", "ZAR"),
    "United Arab Emirates": ("Arabic", "AED"),
    "Switzerland": ("German", "CHF"),
    "Norway": ("Norwegian", "NOK"),
    "Sweden": ("Swedish", "SEK"),
    "Denmark": ("Danish", "DKK"),
    "Iceland": ("Icelandic", "ISK"),
    "Czechia": ("Czech", "CZK"),
    "Poland": ("Polish", "PLN"),
    "South Korea": ("Korean", "KRW"),
    "China": ("Chinese", "CNY"),
}

DEFAULT_COUNTRY_META = {
    "plug": "Check a universal adapter covers Type A/C/G",
    "tipping": "Look up local norms — they vary a lot.",
}

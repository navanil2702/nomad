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
}

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

DEFAULT_COUNTRY_META = {
    "plug": "Check a universal adapter covers Type A/C/G",
    "tipping": "Look up local norms — they vary a lot.",
}

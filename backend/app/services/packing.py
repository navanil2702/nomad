"""Packing list generation, derived from forecast + destination + activities."""

from __future__ import annotations

from ..models.schemas import DayPlan, Interest, PackingItem, TripPreferences, WeatherDay
from .places import Destination

_ESSENTIALS = [
    ("Passport & visa", "Photograph it and email yourself a copy.", True),
    ("Travel insurance details", "Policy number saved offline.", True),
    ("Debit / credit cards", "Tell your bank you're travelling.", True),
    ("Phone + charger", "", True),
    ("Power bank", "Full days out drain a phone by 4pm.", False),
    ("Reusable water bottle", "", False),
    ("Day bag", "Something that zips, worn in front on transit.", False),
]


def _weather_items(forecast: list[WeatherDay]) -> list[tuple[str, str, str]]:
    """Returns (label, category, reason)."""
    if not forecast:
        return []

    items: list[tuple[str, str, str]] = []
    max_temp = max(f.temp_max_c for f in forecast)
    min_temp = min(f.temp_min_c for f in forecast)
    wet_days = [f for f in forecast if f.condition in ("rain", "storm")]
    max_precip = max(f.precipitation_chance for f in forecast)

    if wet_days or max_precip >= 45:
        label = f"{len(wet_days)} wet day{'s' if len(wet_days) != 1 else ''} in the forecast"
        items.append(("Rain jacket (packable)", "weather", label))
        items.append(("Compact umbrella", "weather", label))
        items.append(("Dry bag for electronics", "weather", label))
    if max_temp >= 27:
        items.append(("Sunscreen SPF 50", "health", f"Highs of {max_temp:.0f}°C"))
        items.append(("Sunglasses & hat", "clothing", f"Highs of {max_temp:.0f}°C"))
        items.append(("Light breathable shirts", "clothing", f"Highs of {max_temp:.0f}°C"))
    if min_temp <= 10:
        items.append(("Warm mid-layer", "clothing", f"Lows of {min_temp:.0f}°C"))
    if min_temp <= 2:
        items.append(("Gloves, hat and scarf", "clothing", f"Lows of {min_temp:.0f}°C"))
    if any(f.condition == "snow" for f in forecast):
        items.append(("Waterproof boots", "clothing", "Snow forecast"))
    if max_temp - min_temp >= 12:
        items.append(("Layers you can shed", "clothing", "Big day-to-night temperature swing"))
    return items


def _activity_items(
    prefs: TripPreferences, days: list[DayPlan]
) -> list[tuple[str, str, str]]:
    items: list[tuple[str, str, str]] = []
    interests = set(prefs.interests)
    tags = {t for d in days for a in d.activities for t in a.place.tags}
    total_walk = sum(a.place.walking_intensity for d in days for a in d.activities)

    if Interest.adventure in interests or {"climb", "cycling", "surf", "hike"} & tags:
        items.append(("Trekking / trail shoes", "activity", "Adventure days on the plan"))
        items.append(("Quick-dry towel", "activity", "Adventure days on the plan"))
    if Interest.nature in interests or {"beach", "swim"} & tags:
        items.append(("Swimwear", "activity", "Beach and water stops"))
    if Interest.nightlife in interests:
        items.append(("One smart outfit", "clothing", "Evening venues with a dress code"))
    if Interest.history in interests or {"temple", "shrine", "unesco"} & tags:
        items.append(("Shoulder & knee cover", "clothing", "Religious sites enforce dress codes"))
    if total_walk / max(len(days), 1) >= 9:
        items.append(("Broken-in walking shoes", "clothing", "This is a high-mileage itinerary"))
        items.append(("Blister plasters", "health", "This is a high-mileage itinerary"))
    return items


def _destination_items(dest: Destination) -> list[tuple[str, str, str]]:
    from ..data.knowledge import COUNTRY_META, DEFAULT_COUNTRY_META

    meta = COUNTRY_META.get(dest.country, DEFAULT_COUNTRY_META)
    items = [
        (f"Travel adapter ({meta['plug']})", "electronics", f"Standard in {dest.country}"),
        ("Offline maps downloaded", "electronics", "Data can be patchy between stops"),
        ("Basic medicines", "health", "Painkillers, rehydration salts, plasters"),
    ]
    if dest.climate == "tropical":
        items.append(("Insect repellent (DEET)", "health", "Tropical climate"))
        items.append(("Electrolyte sachets", "health", "Tropical climate"))
    if dest.currency != "USD":
        items.append((f"Some {dest.currency} cash", "essentials", "Small vendors are often cash-only"))
    return items


def generate(
    prefs: TripPreferences,
    dest: Destination,
    days: list[DayPlan],
    forecast: list[WeatherDay],
) -> list[PackingItem]:
    items: list[PackingItem] = [
        PackingItem(label=label, category="essentials", reason=reason, essential=essential)
        for label, reason, essential in _ESSENTIALS
    ]

    seen = {i.label.lower() for i in items}
    for label, category, reason in (
        _weather_items(forecast) + _activity_items(prefs, days) + _destination_items(dest)
    ):
        if label.lower() in seen:
            continue
        seen.add(label.lower())
        items.append(PackingItem(label=label, category=category, reason=reason))  # type: ignore[arg-type]

    return items

"""Live destination catalogs from the Google Places API (New).

The planner reasons about attributes Google does not return directly —
whether a place is indoor (rain swaps), how much walking it demands (fatigue
swaps), how long you'd spend there, what entry costs. Those are derived from
the place's `types` and price level here, so the rest of the app cannot tell
whether a catalog came from Google or from the curated data.

Everything is best-effort: any failure returns None and the caller falls back
to the curated catalog.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..core.config import get_settings
from ..models.schemas import Coordinates, Interest, Place

log = logging.getLogger(__name__)

SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
TIMEZONE_URL = "https://maps.googleapis.com/maps/api/timezone/json"

FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.rating",
        "places.userRatingCount",
        "places.priceLevel",
        "places.types",
        "places.regularOpeningHours",
        "places.photos",
        "places.editorialSummary",
    ]
)

# One query per interest, so a traveller's stated interests decide what the
# catalog is actually made of rather than a single generic "things to do".
INTEREST_QUERIES: dict[Interest, list[str]] = {
    Interest.history: ["museums and historic landmarks in {dest}"],
    Interest.nature: ["parks and gardens in {dest}", "scenic viewpoints in {dest}"],
    Interest.food: ["famous food markets in {dest}"],
    Interest.shopping: ["shopping districts and markets in {dest}"],
    Interest.nightlife: ["bars and live music venues in {dest}"],
    Interest.adventure: ["outdoor activities and attractions in {dest}"],
}

BASE_QUERIES = ["top tourist attractions in {dest}"]
MEAL_QUERIES = [
    "best restaurants in {dest}",
    "vegetarian restaurants in {dest}",
    "cheap eats in {dest}",
    "cafes in {dest}",
]

# --------------------------------------------------------------------------
# Type interpretation
# --------------------------------------------------------------------------

_INDOOR_TYPES = {
    "museum", "art_gallery", "shopping_mall", "aquarium", "movie_theater",
    "library", "restaurant", "cafe", "bar", "night_club", "casino",
    "book_store", "clothing_store", "department_store", "spa", "bakery",
    "performing_arts_theater", "concert_hall",
}

_OUTDOOR_TYPES = {
    "park", "national_park", "beach", "hiking_area", "campground", "zoo",
    "garden", "plaza", "marina", "dog_park", "botanical_garden",
}

_CATEGORY_TYPES: list[tuple[Interest, set[str]]] = [
    (Interest.nightlife, {"night_club", "bar", "casino", "pub", "wine_bar"}),
    (Interest.shopping, {
        "shopping_mall", "department_store", "clothing_store", "book_store",
        "market", "store", "gift_shop", "jewelry_store",
    }),
    (Interest.history, {
        "museum", "art_gallery", "historical_landmark", "church", "mosque",
        "synagogue", "hindu_temple", "monument", "cultural_landmark",
        "historical_place", "performing_arts_theater",
    }),
    (Interest.nature, {
        "park", "national_park", "beach", "garden", "botanical_garden", "zoo",
        "aquarium", "plaza", "marina", "wildlife_park",
    }),
    (Interest.adventure, {
        "amusement_park", "hiking_area", "water_park", "adventure_sports_center",
        "sports_complex", "ski_resort", "observation_deck", "off_roading_area",
    }),
    (Interest.food, {"food_court", "farmers_market", "market"}),
]

_MEAL_TYPES = {
    "restaurant", "cafe", "bakery", "meal_takeaway", "meal_delivery",
    "coffee_shop", "ice_cream_shop", "sandwich_shop", "fast_food_restaurant",
}

_PRICE_LEVELS = {
    "PRICE_LEVEL_FREE": 0,
    "PRICE_LEVEL_INEXPENSIVE": 1,
    "PRICE_LEVEL_MODERATE": 2,
    "PRICE_LEVEL_EXPENSIVE": 3,
    "PRICE_LEVEL_VERY_EXPENSIVE": 4,
}

# Roughly how long people spend, and how much legwork it costs, by category.
_DURATION = {
    Interest.history: 105,
    Interest.nature: 90,
    Interest.shopping: 90,
    Interest.nightlife: 135,
    Interest.adventure: 120,
    Interest.food: 75,
    "meal": 60,
}

_WALK = {
    Interest.history: 3,
    Interest.nature: 4,
    Interest.shopping: 3,
    Interest.nightlife: 2,
    Interest.adventure: 4,
    Interest.food: 2,
    "meal": 1,
}


def _classify(types: list[str]) -> Interest | str:
    lowered = {t.lower() for t in types}
    # A restaurant that is also a "tourist_attraction" is still a meal.
    if lowered & _MEAL_TYPES and not (lowered & {"museum", "park", "shopping_mall"}):
        return "meal"
    for interest, matches in _CATEGORY_TYPES:
        if lowered & matches:
            return interest
    return Interest.history


def _derived_tags(types: list[str], price_level: int, category: Interest | str) -> list[str]:
    """Translate Google's type vocabulary into the one the planner speaks.

    The rest of the app asks questions like "is this vegetarian" and "is this a
    café I can rest in" by looking for specific tags. Google answers with
    `vegetarian_restaurant` and `coffee_shop`, so the mapping happens here
    rather than teaching every call site both vocabularies.
    """
    lowered = {t.lower() for t in types}
    tags: list[str] = list(types[:6])

    if lowered & {"vegetarian_restaurant", "vegan_restaurant"}:
        tags += ["vegetarian", "vegan"]
    if lowered & {"cafe", "coffee_shop", "tea_house", "bakery"}:
        tags += ["cafe", "rest"]
    if lowered & {"bar", "night_club", "pub", "wine_bar", "casino"}:
        tags += ["late", "evening", "bars"]
    if lowered & {"observation_deck", "scenic_lookout", "beach", "park"}:
        tags.append("sunset")
    if lowered & {"museum", "art_gallery", "aquarium", "library"}:
        tags.append("rainy-day")
    if lowered & {"hiking_area", "national_park"}:
        tags.append("hike")
    if lowered & {"market", "farmers_market"}:
        tags.append("market")
    if category == "meal" and price_level <= 1:
        tags += ["cheap", "quick"]
    if category == "meal" and price_level >= 2:
        tags.append("dinner")

    return list(dict.fromkeys(tags))


def _is_indoor(types: list[str], category: Interest | str) -> bool:
    lowered = {t.lower() for t in types}
    if lowered & _OUTDOOR_TYPES:
        return False
    if lowered & _INDOOR_TYPES:
        return True
    return category in (Interest.shopping, Interest.nightlife) or category == "meal"


def _opening_hours(raw: dict | None) -> str:
    """Collapse Google's weekly periods into the planner's "HH:MM - HH:MM"."""
    if not raw:
        return "09:00 - 18:00"
    periods = raw.get("periods") or []
    if not periods:
        # Some places only return descriptions; 24h ones say so.
        text = " ".join(raw.get("weekdayDescriptions") or [])
        return "24 hours" if "24 hours" in text else "09:00 - 18:00"

    opens: list[int] = []
    closes: list[int] = []
    for p in periods:
        o, c = p.get("open"), p.get("close")
        if not o:
            continue
        if c is None:
            return "24 hours"  # open period with no close
        opens.append(o.get("hour", 9) * 60 + o.get("minute", 0))
        closes.append(c.get("hour", 18) * 60 + c.get("minute", 0))

    if not opens:
        return "09:00 - 18:00"

    # The median day is more representative than any single one.
    opens.sort()
    closes.sort()
    o = opens[len(opens) // 2]
    c = closes[len(closes) // 2]
    if c <= o:
        c = 24 * 60 - 1
    return f"{o // 60:02d}:{o % 60:02d} - {c // 60:02d}:{c % 60:02d}"


def _estimated_cost(category: Interest | str, price_level: int, indoor: bool) -> float:
    if category == "meal":
        return [6.0, 12.0, 22.0, 38.0, 60.0][price_level]
    if category in (Interest.nature,) and price_level <= 1:
        return 0.0
    return [0.0, 8.0, 16.0, 26.0, 40.0][price_level]


def _to_place(raw: dict) -> Place | None:
    try:
        loc = raw["location"]
        types = raw.get("types") or []
        category = _classify(types)
        price_level = _PRICE_LEVELS.get(raw.get("priceLevel", ""), 2)
        indoor = _is_indoor(types, category)
        photos = raw.get("photos") or []

        return Place(
            id=raw["id"],
            name=raw["displayName"]["text"],
            category=category,
            description=(raw.get("editorialSummary") or {}).get("text", ""),
            coordinates=Coordinates(lat=loc["latitude"], lng=loc["longitude"]),
            rating=float(raw.get("rating") or 4.2),
            review_count=int(raw.get("userRatingCount") or 0),
            price_level=price_level,
            indoor=indoor,
            walking_intensity=_WALK.get(category, 3),
            opening_hours=_opening_hours(raw.get("regularOpeningHours")),
            # Resolved through our own proxy so the API key never ships to a
            # browser. See routers/places.py.
            photo=f"/api/places/photo?name={photos[0]['name']}" if photos else "",
            tags=_derived_tags(types, price_level, category),
            address=raw.get("formattedAddress", ""),
        )
    except (KeyError, TypeError, ValueError) as exc:
        log.debug("skipping unusable place result: %s", exc)
        return None


# --------------------------------------------------------------------------
# API calls
# --------------------------------------------------------------------------


def _search(client: httpx.Client, query: str, limit: int = 12) -> list[dict]:
    r = client.post(
        SEARCH_URL,
        headers={"X-Goog-FieldMask": FIELD_MASK},
        json={"textQuery": query, "maxResultCount": limit},
    )
    r.raise_for_status()
    return r.json().get("places", [])


def fetch_catalog(
    destination: str, interests: list[Interest] | None = None
) -> dict[str, Any] | None:
    """Build a live destination catalog. Returns None if unusable."""
    settings = get_settings()
    key = settings.google_maps_api_key
    if not key:
        return None

    queries = list(BASE_QUERIES)
    for interest in interests or []:
        queries += INTEREST_QUERIES.get(interest, [])
    if not interests:
        queries += [q for qs in INTEREST_QUERIES.values() for q in qs[:1]]
    queries += MEAL_QUERIES

    places: dict[str, Place] = {}
    meta: dict[str, Any] = {}

    with httpx.Client(
        headers={"X-Goog-Api-Key": key, "Content-Type": "application/json"},
        timeout=12.0,
    ) as client:
        for template in queries:
            query = template.format(dest=destination)
            try:
                results = _search(client, query)
            except Exception as exc:
                log.warning("Places query failed (%s): %s", query, exc)
                continue

            for raw in results:
                place = _to_place(raw)
                if place and place.id not in places:
                    places[place.id] = place
                    if not meta and raw.get("formattedAddress"):
                        meta["country"] = _country_from_address(raw["formattedAddress"])

        # A catalog too thin to plan against is worse than the curated one.
        attractions = [p for p in places.values() if p.category != "meal"]
        meals = [p for p in places.values() if p.category == "meal"]
        if len(attractions) < 8 or len(meals) < 3:
            log.warning(
                "Places returned too little for %s (%d attractions, %d meals)",
                destination, len(attractions), len(meals),
            )
            return None

        centre = _centre(list(places.values()))
        tz = _timezone(client, centre, key)

    country = meta.get("country") or destination.split(",")[-1].strip().title()
    return {
        "places": list(places.values()),
        "center": centre,
        "country": country,
        "timezone": tz.get("id", "UTC"),
        "utc_offset_hours": tz.get("offset_hours", 0.0),
        "source": "google-places",
    }


def estimated_cost(category: Interest | str, price_level: int, indoor: bool) -> float:
    """Per-person cost of visiting, in USD before the destination cost index."""
    return _estimated_cost(category, price_level, indoor)


def visit_duration(category: Interest | str) -> int:
    """Typical minutes spent at a place of this kind."""
    return _DURATION.get(category, 90)


def _country_from_address(address: str) -> str:
    parts = [p.strip() for p in address.split(",") if p.strip()]
    return parts[-1] if parts else ""


def _centre(places: list[Place]) -> Coordinates:
    lats = [p.coordinates.lat for p in places]
    lngs = [p.coordinates.lng for p in places]
    return Coordinates(lat=sum(lats) / len(lats), lng=sum(lngs) / len(lngs))


def _timezone(client: httpx.Client, centre: Coordinates, key: str) -> dict[str, Any]:
    """Google Time Zone API. Falls back to UTC, which only affects display."""
    import time

    try:
        r = client.get(
            TIMEZONE_URL,
            params={
                "location": f"{centre.lat},{centre.lng}",
                "timestamp": int(time.time()),
                "key": key,
            },
        )
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "OK":
            return {}
        offset = (data.get("rawOffset", 0) + data.get("dstOffset", 0)) / 3600
        return {"id": data.get("timeZoneId", "UTC"), "offset_hours": offset}
    except Exception as exc:
        log.debug("timezone lookup failed: %s", exc)
        return {}


def photo_uri(photo_name: str, max_width: int = 900) -> str | None:
    """Resolve a Places photo resource to a signed, key-less image URL."""
    key = get_settings().google_maps_api_key
    if not key:
        return None
    try:
        r = httpx.get(
            f"https://places.googleapis.com/v1/{photo_name}/media",
            params={
                "maxWidthPx": max_width,
                "key": key,
                "skipHttpRedirect": "true",
            },
            timeout=8.0,
        )
        r.raise_for_status()
        return r.json().get("photoUri")
    except Exception as exc:
        log.warning("photo lookup failed: %s", exc)
        return None

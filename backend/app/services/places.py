"""Place lookup.

Resolves a free-text destination to a catalog of Places. Known cities come
from the curated catalog; anything else gets a plausible generated catalog so
the product never dead-ends on an unrecognised destination.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

from ..data.destinations import DESTINATIONS, GENERIC_TEMPLATE
from ..data.knowledge import CURRENCY_RATES
from ..models.schemas import Coordinates, Interest, Place

_MEAL_CATEGORIES = {"meal"}


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _stable_float(seed: str, lo: float, hi: float) -> float:
    """Deterministic pseudo-random in [lo, hi] so generated cities are stable."""
    h = int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16)
    return lo + (h % 10_000) / 10_000 * (hi - lo)


class Destination:
    """A resolved destination plus its place catalog."""

    def __init__(self, key: str, meta: dict, places: list[Place]) -> None:
        self.key = key
        self.name: str = meta["name"]
        self.country: str = meta["country"]
        self.language: str = meta["language"]
        self.currency: str = meta["currency"]
        self.timezone: str = meta["timezone"]
        self.utc_offset_hours: float = meta["utc_offset_hours"]
        self.climate: str = meta["climate"]
        self.cost_index: float = meta["daily_cost_index"]
        self.blurb: str = meta.get("blurb", "")
        self.center = Coordinates(**meta["center"])
        self.places = places
        self.is_curated: bool = meta.get("curated", False)

    # -- filtered views ----------------------------------------------------
    @property
    def meals(self) -> list[Place]:
        return [p for p in self.places if p.category in _MEAL_CATEGORIES]

    @property
    def attractions(self) -> list[Place]:
        return [p for p in self.places if p.category not in _MEAL_CATEGORIES]

    def by_id(self, place_id: str) -> Place | None:
        return next((p for p in self.places if p.id == place_id), None)

    def indoor_attractions(self) -> list[Place]:
        return [p for p in self.attractions if p.indoor]

    def low_effort_attractions(self) -> list[Place]:
        return [p for p in self.attractions if p.walking_intensity <= 2]

    def cheap_meals(self) -> list[Place]:
        return sorted(
            [p for p in self.meals if p.price_level <= 1],
            key=lambda p: p.price_level,
        )

    def vegetarian_meals(self) -> list[Place]:
        return [
            p
            for p in self.meals
            if {"vegetarian", "vegan", "veg-friendly", "veg-option", "veg-options"}
            & set(p.tags)
        ]

    def restful_meals(self) -> list[Place]:
        return [p for p in self.meals if "cafe" in p.tags or "rest" in p.tags]


def _build_place(raw: dict, cost_index: float) -> Place:
    category = raw["category"]
    return Place(
        id=raw["id"],
        name=raw["name"],
        category=category if category in _MEAL_CATEGORIES else Interest(category),
        description=raw.get("tip", ""),
        coordinates=Coordinates(lat=raw["lat"], lng=raw["lng"]),
        rating=raw.get("rating", 4.4),
        review_count=raw.get("reviews", 0),
        price_level=raw.get("price", 2),
        indoor=raw.get("indoor", False),
        walking_intensity=raw.get("walk", 3),
        opening_hours=raw.get("hours", "09:00 - 18:00"),
        tags=raw.get("tags", []),
        address=raw.get("address", ""),
    )


def _generated_catalog(name: str) -> dict:
    """Invent a coherent destination for a city we have no catalog for."""
    key = slugify(name) or "somewhere"
    lat = _stable_float(key + "lat", -45, 60)
    lng = _stable_float(key + "lng", -120, 140)
    display = name.strip().title()

    places: list[dict] = []
    for i, tpl in enumerate(GENERIC_TEMPLATE):
        jitter_lat = _stable_float(f"{key}{i}lat", -0.035, 0.035)
        jitter_lng = _stable_float(f"{key}{i}lng", -0.045, 0.045)
        places.append(
            {
                "id": f"{key}-{i}",
                "name": f"{display} {tpl['suffix']}",
                "category": tpl["category"],
                "lat": round(lat + jitter_lat, 5),
                "lng": round(lng + jitter_lng, 5),
                "rating": round(_stable_float(f"{key}{i}r", 4.0, 4.8), 1),
                "reviews": int(_stable_float(f"{key}{i}v", 800, 45000)),
                "price": tpl["price"],
                "indoor": tpl["indoor"],
                "walk": tpl["walk"],
                "hours": tpl["hours"],
                "cost": tpl["cost"],
                "duration": tpl["duration"],
                "tags": tpl["tags"],
                "address": f"{display} city centre",
                "tip": tpl["tip"],
            }
        )

    return {
        "name": display,
        "country": display,
        "language": "English",
        "currency": "USD",
        "timezone": "UTC",
        "utc_offset_hours": round(_stable_float(key + "tz", -8, 10)),
        "center": {"lat": round(lat, 5), "lng": round(lng, 5)},
        "climate": "temperate",
        "daily_cost_index": round(_stable_float(key + "ci", 0.6, 1.2), 2),
        "blurb": f"{display}, planned around what you actually want to do.",
        "places": places,
        "curated": False,
    }


# Per-place planning metadata that does not belong on the Place model.
_PLACE_COST: dict[str, float] = {}
_PLACE_DURATION: dict[str, int] = {}


def resolve(destination: str) -> Destination:
    """Resolve free text like 'tokyo, japan' to a Destination."""
    query = slugify(destination)

    meta: dict | None = None
    key = query
    for cat_key, cat in DESTINATIONS.items():
        if cat_key in query or slugify(cat["name"]) in query:
            meta, key = {**cat, "curated": True}, cat_key
            break

    if meta is None:
        meta = _generated_catalog(destination)

    places = [_build_place(raw, meta["daily_cost_index"]) for raw in meta["places"]]
    for raw in meta["places"]:
        _PLACE_COST[raw["id"]] = raw.get("cost", 0) * meta["daily_cost_index"]
        _PLACE_DURATION[raw["id"]] = raw.get("duration", 90)

    return Destination(key, meta, places)


def base_cost(place: Place) -> float:
    return round(_PLACE_COST.get(place.id, 10.0), 2)


def base_duration(place: Place) -> int:
    return _PLACE_DURATION.get(place.id, 90)


def currency_rate(currency: str) -> float:
    return CURRENCY_RATES.get(currency.upper(), 1.0)


def maps_url(place: Place) -> str:
    """A Google Maps deep link. Works without an API key."""
    q = f"{place.name}, {place.address}".strip(", ").replace(" ", "+")
    return f"https://www.google.com/maps/search/?api=1&query={q}"


def directions_url(origin: Place, destination: Place, mode: str = "walking") -> str:
    o = f"{origin.coordinates.lat},{origin.coordinates.lng}"
    d = f"{destination.coordinates.lat},{destination.coordinates.lng}"
    return (
        "https://www.google.com/maps/dir/?api=1"
        f"&origin={o}&destination={d}&travelmode={mode}"
    )


def haversine_km(a: Coordinates, b: Coordinates) -> float:
    from math import asin, cos, radians, sin, sqrt

    lat1, lon1, lat2, lon2 = map(radians, [a.lat, a.lng, b.lat, b.lng])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371 * 2 * asin(sqrt(h))


def travel_estimate(a: Place, b: Place) -> tuple[int, str]:
    """Minutes and mode between two places."""
    km = haversine_km(a.coordinates, b.coordinates)
    if km < 1.2:
        return max(5, int(km * 13)), "walk"
    if km < 12:
        return max(10, int(km * 3.2) + 6), "transit"
    return max(15, int(km * 1.9) + 8), "taxi"

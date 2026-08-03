"""Place lookup.

Resolves a free-text destination to a catalog of Places. Known cities come
from the curated catalog; anything else gets a plausible generated catalog so
the product never dead-ends on an unrecognised destination.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

from ..core.config import get_settings
from ..data.destinations import DESTINATIONS, GENERIC_TEMPLATE
from ..data.knowledge import CURRENCY_RATES
from ..models.schemas import Coordinates, DestinationCatalog, Interest, Place
from . import google_places, providers

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
        # "google-places", "curated" or "generated" — surfaced so the UI can
        # be honest about where the plan's places came from.
        self.source: str = meta.get("source", "curated")

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


def _climate_for(lat: float) -> str:
    """Rough climate band from latitude, for the offline forecast model."""
    a = abs(lat)
    if a < 23.5:
        return "tropical"
    if a < 35:
        return "mediterranean"
    if a < 45:
        return "humid-subtropical"
    if a < 60:
        return "oceanic"
    return "temperate"


def _live_meta(destination: str, catalog: dict) -> dict:
    """Turn a live Places catalog into the meta a Destination expects."""
    from ..data.knowledge import COUNTRY_PROFILE

    country = catalog.get("country") or destination.split(",")[-1].strip().title()
    language, currency = COUNTRY_PROFILE.get(country, ("English", "USD"))
    centre = catalog["center"]

    live_places: list[Place] = catalog["places"]
    # Price levels across the catalog stand in for how expensive the city is.
    levels = [p.price_level for p in live_places] or [2]
    cost_index = round(0.55 + (sum(levels) / len(levels)) * 0.28, 2)

    return {
        "name": destination.split(",")[0].strip().title(),
        "country": country,
        "language": language,
        "currency": currency,
        "timezone": catalog.get("timezone", "UTC"),
        "utc_offset_hours": catalog.get("utc_offset_hours", 0.0),
        "center": {"lat": centre.lat, "lng": centre.lng},
        "climate": _climate_for(centre.lat),
        "daily_cost_index": cost_index,
        "blurb": f"{destination.split(',')[0].strip().title()}, planned from live Google Places data.",
        "curated": False,
        "source": "google-places",
    }


# Resolving is on the hot path of nearly every request, and the same
# destination must always produce the same place ids — otherwise a trip saved
# earlier could not be matched back to its places. So the catalog is cached
# and never varies by traveller.
_DESTINATION_CACHE = providers.TTLCache(ttl_seconds=6 * 60 * 60, maxsize=64)


def _curated_or_generated(destination: str) -> tuple[str, dict]:
    query = slugify(destination)
    for cat_key, cat in DESTINATIONS.items():
        if cat_key in query or slugify(cat["name"]) in query:
            return cat_key, {**cat, "curated": True, "source": "curated"}
    return query, {**_generated_catalog(destination), "source": "generated"}


def _register(place_id: str, cost: float, duration: int) -> None:
    _PLACE_COST[place_id] = cost
    _PLACE_DURATION[place_id] = duration


def to_catalog(dest: Destination) -> DestinationCatalog:
    """Freeze a resolved Destination so it can be stored with a trip."""
    return DestinationCatalog(
        key=dest.key,
        name=dest.name,
        country=dest.country,
        language=dest.language,
        currency=dest.currency,
        timezone=dest.timezone,
        utc_offset_hours=dest.utc_offset_hours,
        climate=dest.climate,
        daily_cost_index=dest.cost_index,
        blurb=dest.blurb,
        source=dest.source,
        center=dest.center,
        places=dest.places,
        costs={p.id: base_cost(p) for p in dest.places},
        durations={p.id: base_duration(p) for p in dest.places},
    )


def from_catalog(catalog: DestinationCatalog) -> Destination:
    """Rebuild a Destination from stored data. Never touches the network."""
    for place_id, cost in catalog.costs.items():
        _PLACE_COST[place_id] = cost
    for place_id, duration in catalog.durations.items():
        _PLACE_DURATION[place_id] = duration

    meta = {
        "name": catalog.name,
        "country": catalog.country,
        "language": catalog.language,
        "currency": catalog.currency,
        "timezone": catalog.timezone,
        "utc_offset_hours": catalog.utc_offset_hours,
        "climate": catalog.climate,
        "daily_cost_index": catalog.daily_cost_index,
        "blurb": catalog.blurb,
        "source": catalog.source,
        "curated": catalog.source == "curated",
        "center": {"lat": catalog.center.lat, "lng": catalog.center.lng},
    }
    return Destination(catalog.key, meta, catalog.places)


def for_trip(trip) -> Destination:
    """The Destination a trip was planned against.

    This is what request handlers should use. It reads the catalog saved on
    the trip, so a chat message or an alert scan costs nothing upstream no
    matter how many serverless instances handle it.
    """
    if getattr(trip, "catalog", None):
        return from_catalog(trip.catalog)
    # Trips created before catalogs were stored.
    return resolve(trip.preferences.destination)


def resolve(destination: str, *, allow_live: bool = True) -> Destination:
    """Resolve free text like 'tokyo, japan' to a Destination.

    Live Google Places first; the curated catalog is the fallback. Callers
    that only need cheap metadata should pass allow_live=False rather than
    trigger a paid lookup.
    """
    query = slugify(destination) or "somewhere"

    cached = _DESTINATION_CACHE.get(f"dest:{query}")
    if cached is not None:
        # Re-register planning metadata: the module-level maps are not part of
        # the cached object and a fresh process may not have them.
        for place, cost, duration in cached[1]:
            _register(place.id, cost, duration)
        return cached[0]

    settings = get_settings()
    dest: Destination | None = None
    registry_entries: list[tuple[Place, float, int]] = []

    if allow_live and settings.google_maps_api_key:
        catalog = providers.cached_call(
            _DESTINATION_CACHE,
            f"catalog:{query}",
            "places",
            live=lambda: google_places.fetch_catalog(destination),
            fallback=lambda: None,
        )
        if catalog:
            meta = _live_meta(destination, catalog)
            live_places: list[Place] = catalog["places"]
            for place in live_places:
                cost = google_places.estimated_cost(
                    place.category, place.price_level, place.indoor
                ) * meta["daily_cost_index"]
                duration = google_places.visit_duration(place.category)
                registry_entries.append((place, round(cost, 2), duration))
                _register(place.id, round(cost, 2), duration)
            dest = Destination(query, meta, live_places)

    if dest is None:
        key, meta = _curated_or_generated(destination)
        places = [_build_place(raw, meta["daily_cost_index"]) for raw in meta["places"]]
        by_id = {p.id: p for p in places}
        for raw in meta["places"]:
            cost = raw.get("cost", 0) * meta["daily_cost_index"]
            duration = raw.get("duration", 90)
            _register(raw["id"], cost, duration)
            if raw["id"] in by_id:
                registry_entries.append((by_id[raw["id"]], cost, duration))
        dest = Destination(key, meta, places)

    _DESTINATION_CACHE.set(f"dest:{query}", (dest, registry_entries))
    return dest


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

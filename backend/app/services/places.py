"""Place lookup.

Resolves a free-text destination to a catalog of Places. Known cities come
from the curated catalog; anything else gets a plausible generated catalog so
the product never dead-ends on an unrecognised destination.
"""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata

from ..core.config import get_settings
from ..data.destinations import DESTINATIONS, GENERIC_TEMPLATE
from ..data.knowledge import CURRENCY_RATES
from ..models.schemas import Coordinates, DestinationCatalog, Interest, Place
from . import google_places, providers

log = logging.getLogger(__name__)

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
        # "researched" | "estimated" | "price-band" | "template"
        self.pricing: str = meta.get("pricing", "researched")

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
        # Unknown city: UTC rather than an invented offset. A random
        # timezone reads as authoritative and is wrong; UTC is at least
        # obviously a default. Live resolution supplies the real one.
        "utc_offset_hours": 0.0,
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
    from ..data.knowledge import COUNTRY_PROFILE, canonical_country

    country = canonical_country(
        catalog.get("country") or destination.split(",")[-1].strip().title()
    )
    language, currency = COUNTRY_PROFILE.get(country, ("English", "USD"))
    centre = catalog["center"]

    live_places: list[Place] = catalog["places"]

    # Anchor on the country's absolute cost level. Google's price levels are
    # relative to the local market, so on their own they would price Udaipur
    # like Vienna; they are only used to nudge within the country, for the
    # difference between a resort town and a provincial one.
    from ..data.knowledge import COUNTRY_COST_INDEX, DEFAULT_COUNTRY_COST_INDEX

    base_index = COUNTRY_COST_INDEX.get(country, DEFAULT_COUNTRY_COST_INDEX)
    levels = [p.price_level for p in live_places] or [2]
    local_skew = 0.85 + (sum(levels) / len(levels)) * 0.075  # ~0.85–1.15
    cost_index = round(base_index * local_skew, 2)

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


# How far an estimated price may sit from the band it replaces before it is
# treated as a hallucination. Generous on purpose — the whole reason to ask is
# that the bands are crude — but it still stops a $400 temple ticket from
# reshaping an itinerary through the budget-pressure score.
_PRICE_SANITY_FLOOR = 0.1
_PRICE_SANITY_CEILING = 8.0


def _apply_estimated_costs(
    places: list[Place],
    baseline: dict[str, float],
    destination: str,
    country: str,
    currency: str = "",
) -> tuple[dict[str, float], bool]:
    """Replace crude cost estimates with model estimates where they look sane.

    `baseline` must already be in local terms — the destination cost index
    applied — because rejected estimates fall back to it and the result of this
    function is used as-is. Returns the costs and whether the model was
    actually used.
    """
    from . import llm

    estimates = llm.estimate_place_costs(
        destination=destination,
        country=country,
        local_currency=currency,
        places=[
            {
                "id": p.id,
                "name": p.name,
                "kind": str(getattr(p.category, "value", p.category)),
                "price_level": p.price_level,
                "free_hint": bool({"free", "park", "plaza"} & set(p.tags)),
            }
            for p in places
        ],
    )
    if not estimates:
        return baseline, False

    costs = dict(baseline)
    accepted = 0
    for place in places:
        estimate = estimates.get(place.id)
        if estimate is None:
            continue
        band = baseline.get(place.id, 0.0)

        # "This is free" is a common, correct and harmless answer — bazaars,
        # temples and squares routinely charge nothing while sitting in a
        # non-zero price band. A zero can never blow a budget, so take it.
        if estimate == 0:
            costs[place.id] = 0.0
            accepted += 1
            continue

        # A free band is no anchor to sanity-check against, so fall back to an
        # absolute ceiling for a plausible entry fee.
        if band <= 0:
            if estimate <= 30:
                costs[place.id] = estimate
                accepted += 1
            continue

        if _PRICE_SANITY_FLOOR * band <= estimate <= _PRICE_SANITY_CEILING * band:
            costs[place.id] = estimate
            accepted += 1

    if accepted < len(places) * 0.5:
        # Too many rejects to trust the batch; keep the bands.
        log.warning(
            "estimated prices rejected for %s (%d/%d accepted)",
            destination, accepted, len(places),
        )
        return baseline, False

    return costs, True


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
        pricing=dest.pricing,
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
        "pricing": catalog.pricing,
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

            # Scale the bands to the destination first, so they are directly
            # comparable to a model estimate and usable as its fallback.
            bands = {
                p.id: google_places.estimated_cost(
                    p.category, p.price_level, p.indoor
                ) * meta["daily_cost_index"]
                for p in live_places
            }
            costs, estimated = _apply_estimated_costs(
                live_places, bands, destination, meta["country"], meta["currency"]
            )
            meta["pricing"] = "estimated" if estimated else "price-band"

            for place in live_places:
                cost = round(costs[place.id], 2)
                duration = google_places.visit_duration(place.category)
                registry_entries.append((place, cost, duration))
                _register(place.id, cost, duration)
            dest = Destination(query, meta, live_places)

    if dest is None:
        key, meta = _curated_or_generated(destination)
        places = [_build_place(raw, meta["daily_cost_index"]) for raw in meta["places"]]
        by_id = {p.id: p for p in places}
        # The cost index scales *generic* figures — the price-level bands used
        # for live places, and the template costs in a generated catalog — to
        # the local market. Curated costs are already researched local prices,
        # so applying it there would double-count the destination and quietly
        # halve every price in a cheap city.
        curated = meta.get("source") == "curated"
        index = 1.0 if curated else meta["daily_cost_index"]
        costs = {raw["id"]: raw.get("cost", 0) * index for raw in meta["places"]}

        # A generated catalog's costs are template placeholders, so they are
        # worth replacing with estimates. Curated costs are researched real
        # prices and are left alone — a model guess would be a downgrade.
        if not curated:
            costs, are_local = _apply_estimated_costs(
                places, costs, destination, meta["country"], meta["currency"]
            )
            meta["pricing"] = "estimated" if are_local else "template"
        else:
            meta["pricing"] = "researched"

        for raw in meta["places"]:
            cost = costs.get(raw["id"], 0.0)
            duration = raw.get("duration", 90)
            _register(raw["id"], cost, duration)
            if raw["id"] in by_id:
                registry_entries.append((by_id[raw["id"]], cost, duration))
        dest = Destination(key, meta, places)

    _DESTINATION_CACHE.set(f"dest:{query}", (dest, registry_entries))
    return dest


def base_cost(place: Place) -> float:
    """Per-person cost of visiting, in USD."""
    return round(_PLACE_COST.get(place.id, 10.0), 2)


def to_currency(usd: float, currency: str) -> float:
    """USD -> the trip's currency.

    Every figure in the catalogs is USD so destinations stay comparable. The
    traveller's budget and their logged expenses are in *their* currency, so
    planned costs have to be converted or none of the budget arithmetic means
    anything.
    """
    return round(usd * currency_rate(currency), 2)


def activity_cost(place: Place, prefs) -> float:
    """What a stop costs the whole party, in the trip's currency."""
    return to_currency(base_cost(place) * prefs.travelers, prefs.currency)


def base_duration(place: Place) -> int:
    return _PLACE_DURATION.get(place.id, 90)


def currency_rate(currency: str) -> float:
    """Units of `currency` per 1 USD. Live when available, table otherwise."""
    from . import fx

    return fx.rate(currency)


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

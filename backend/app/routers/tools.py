"""Bonus utilities: currency, time zones, shared trips, destination search."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from ..core.config import get_settings
from ..data.destinations import DESTINATIONS
from ..data.knowledge import CURRENCY_RATES, CURRENCY_SYMBOLS
from ..models.schemas import Trip
from ..services import (
    fx,
    google_places,
    places as places_svc,
    providers,
    trips as trips_svc,
)
from ..store import get_store

router = APIRouter(prefix="/api", tags=["tools"])


@router.get("/destinations")
def destinations(q: str | None = None) -> list[dict]:
    """Curated destinations, for the setup autocomplete."""
    rows = [
        {
            "key": key,
            "name": meta["name"],
            "country": meta["country"],
            "label": f"{meta['name']}, {meta['country']}",
            "blurb": meta["blurb"],
            "currency": meta["currency"],
            "cost_index": meta["daily_cost_index"],
            "places": len(meta["places"]),
        }
        for key, meta in DESTINATIONS.items()
    ]
    if q:
        needle = q.lower()
        rows = [r for r in rows if needle in r["label"].lower()]
    return rows


# Autocomplete is billed per request and fires on keystrokes, so the same
# prefix is only ever asked once an hour.
_SUGGEST_CACHE = providers.TTLCache(ttl_seconds=60 * 60, maxsize=512)


@router.get("/destinations/search")
def search_destinations(q: str = Query("", max_length=80), limit: int = 6) -> list[dict]:
    """Type-ahead for the destination field.

    Live Google suggestions when a Places key is configured; otherwise the
    curated cities, matched loosely so two letters are enough.
    """
    query = q.strip()
    if len(query) < 2:
        return []

    def curated() -> list[dict]:
        needle = query.lower()
        return [
            {
                "label": f"{meta['name']}, {meta['country']}",
                "primary": meta["name"],
                "secondary": meta["country"],
                "curated": True,
            }
            for meta in DESTINATIONS.values()
            if needle in meta["name"].lower() or needle in meta["country"].lower()
        ][:limit]

    suggestions = providers.cached_call(
        _SUGGEST_CACHE,
        f"suggest:{query.lower()}:{limit}",
        "places",
        live=lambda: google_places.autocomplete_cities(query, limit),
        fallback=curated,
        enabled=bool(get_settings().google_maps_api_key),
    )

    # Curated cities that match go first either way — they have hand-checked
    # catalogs, which is genuinely a better trip than a generated one.
    known = {c["label"] for c in curated()}
    ranked = curated() + [s for s in suggestions if s["label"] not in known]
    return ranked[:limit]


@router.get("/currency/convert")
def convert(amount: float, base: str = "USD", target: str = "EUR") -> dict:
    base, target = base.upper(), target.upper()
    table, source = fx.rates()
    if base not in table or target not in table:
        raise HTTPException(status_code=400, detail="Unsupported currency")
    usd = amount / table[base]
    converted = usd * table[target]
    return {
        "amount": amount,
        "base": base,
        "target": target,
        "rate": round(table[target] / table[base], 6),
        "converted": round(converted, 2),
        "base_symbol": CURRENCY_SYMBOLS.get(base, ""),
        "target_symbol": CURRENCY_SYMBOLS.get(target, ""),
        "source": source,
    }


@router.get("/currency/rates")
def rates() -> dict:
    table, source = fx.rates()
    return {
        "base": "USD",
        "rates": table,
        "symbols": CURRENCY_SYMBOLS,
        "source": source,
    }


@router.get("/timezone")
def timezone_convert(destination: str, home_offset_hours: float = 0.0) -> dict:
    dest = places_svc.resolve(destination, allow_live=False)
    now_utc = datetime.now(timezone.utc)
    local = now_utc + timedelta(hours=dest.utc_offset_hours)
    home = now_utc + timedelta(hours=home_offset_hours)
    delta = dest.utc_offset_hours - home_offset_hours
    return {
        "destination": dest.name,
        "timezone": dest.timezone,
        "utc_offset_hours": dest.utc_offset_hours,
        "local_time": local.strftime("%H:%M"),
        "local_date": local.strftime("%a %d %b"),
        "home_time": home.strftime("%H:%M"),
        "difference_hours": delta,
        "summary": (
            f"{dest.name} is {abs(delta):.0f}h "
            f"{'ahead of' if delta >= 0 else 'behind'} you"
            if delta
            else f"{dest.name} is in your time zone"
        ),
    }


@router.get("/shared/{token}")
def shared_trip(token: str) -> dict:
    """Read-only view of a trip, for a share link."""
    trip: Trip | None = get_store().get_by_share_token(token)
    if not trip:
        raise HTTPException(status_code=404, detail="Shared trip not found")
    return {
        "title": trip.title,
        "destination": trip.preferences.destination,
        "start_date": trip.preferences.start_date,
        "end_date": trip.preferences.end_date,
        "travelers": trip.preferences.travelers,
        "interests": [i.value for i in trip.preferences.interests],
        "pace": trip.preferences.pace.value,
        "center": trip.center,
        "days": trip.days,
        "weather": trip.weather,
        "budget_breakdown": trip.budget_breakdown,
        "markers": trips_svc.map_places(trip),
    }

"""Bonus utilities: currency, time zones, shared trips, destination search."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException

from ..data.destinations import DESTINATIONS
from ..data.knowledge import CURRENCY_RATES, CURRENCY_SYMBOLS
from ..models.schemas import Trip
from ..services import places as places_svc, trips as trips_svc
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


@router.get("/currency/convert")
def convert(amount: float, base: str = "USD", target: str = "EUR") -> dict:
    base, target = base.upper(), target.upper()
    if base not in CURRENCY_RATES or target not in CURRENCY_RATES:
        raise HTTPException(status_code=400, detail="Unsupported currency")
    usd = amount / CURRENCY_RATES[base]
    converted = usd * CURRENCY_RATES[target]
    return {
        "amount": amount,
        "base": base,
        "target": target,
        "rate": round(CURRENCY_RATES[target] / CURRENCY_RATES[base], 6),
        "converted": round(converted, 2),
        "base_symbol": CURRENCY_SYMBOLS.get(base, ""),
        "target_symbol": CURRENCY_SYMBOLS.get(target, ""),
        "source": "indicative offline rates",
    }


@router.get("/currency/rates")
def rates() -> dict:
    return {"base": "USD", "rates": CURRENCY_RATES, "symbols": CURRENCY_SYMBOLS}


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

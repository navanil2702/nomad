"""Trip orchestration: create, enrich, and derive views over a trip."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from ..models.schemas import (
    Expense,
    ExpenseStats,
    LocalInfo,
    Trip,
    TripCreate,
)
from . import itinerary, packing, places as places_svc, proactive, weather as weather_svc


def create_trip(payload: TripCreate) -> Trip:
    if payload.end_date < payload.start_date:
        payload.end_date = payload.start_date

    # Keep trips to a sane length; the planner degrades past a fortnight.
    if (payload.end_date - payload.start_date).days > 20:
        payload.end_date = payload.start_date + timedelta(days=20)

    days, budget, dest, forecast = itinerary.generate(payload)
    payload.currency = payload.currency or dest.currency

    trip = Trip(
        title=itinerary.trip_title(payload, dest),
        preferences=payload,
        center=dest.center,
        # Freeze the catalog onto the trip. Every later request reads it from
        # here instead of resolving again, which keeps chat and alert scans off
        # the paid Places API entirely.
        catalog=places_svc.to_catalog(dest),
        timezone=dest.timezone,
        country=dest.country,
        language=dest.language,
        days=days,
        budget_breakdown=budget,
        weather=forecast,
        weather_alerts=weather_svc.build_alerts(forecast),
        packing_list=packing.generate(payload, dest, days, forecast),
    )

    # Run the proactive pass immediately so the traveller opens the trip and
    # the companion has already handled the first problem.
    proactive.scan(trip, today=min(date.today(), payload.start_date))
    return trip


def expense_stats(trip: Trip) -> ExpenseStats:
    by_category: dict[str, float] = defaultdict(float)
    by_day_map: dict[str, float] = defaultdict(float)

    for e in trip.expenses:
        by_category[e.category.value] += e.amount
        by_day_map[e.date.isoformat()] += e.amount

    for category in ("food", "transport", "shopping", "hotels", "activities"):
        by_category.setdefault(category, 0.0)

    by_day = [
        {
            "date": d.date.isoformat(),
            "label": f"Day {d.day_number}",
            "day_number": d.day_number,
            "amount": round(by_day_map.get(d.date.isoformat(), 0.0), 2),
            "planned": d.estimated_cost,
        }
        for d in trip.days
    ]

    spent = trip.total_spent()
    elapsed = max(sum(1 for d in trip.days if d.date <= date.today()), 1)
    daily_average = round(spent / elapsed, 2)
    projected = round(daily_average * max(len(trip.days), 1), 2)

    return ExpenseStats(
        budget=trip.preferences.budget,
        spent=spent,
        remaining=trip.remaining_budget(),
        by_category={k: round(v, 2) for k, v in by_category.items()},
        by_day=by_day,
        daily_average=daily_average,
        projected_total=projected,
        over_budget=spent > trip.preferences.budget,
    )


def add_expense(trip: Trip, expense: Expense) -> Trip:
    trip.expenses.append(expense)
    trip.expenses.sort(key=lambda e: (e.date, e.created_at))
    return trip


def local_info(trip: Trip) -> LocalInfo:
    from ..data.knowledge import (
        COUNTRY_META,
        CURRENCY_RATES,
        DEFAULT_COUNTRY_META,
        DEFAULT_EMERGENCY,
        EMERGENCY,
        PHRASES,
    )

    dest = places_svc.for_trip(trip)
    meta = COUNTRY_META.get(dest.country, DEFAULT_COUNTRY_META)

    return LocalInfo(
        country=dest.country,
        language=dest.language,
        currency=dest.currency,
        currency_rate_from_usd=CURRENCY_RATES.get(dest.currency, 1.0),
        timezone=dest.timezone,
        utc_offset_hours=dest.utc_offset_hours,
        phrases=PHRASES.get(dest.language, PHRASES["English"]),  # type: ignore[arg-type]
        emergency=EMERGENCY.get(dest.country, DEFAULT_EMERGENCY),  # type: ignore[arg-type]
        plug_type=meta["plug"],
        tipping=meta["tipping"],
    )


def map_places(trip: Trip) -> list[dict]:
    """Every place on the itinerary, flattened for the map view."""
    out: list[dict] = []
    seen: set[str] = set()
    for day in trip.days:
        for act in day.activities:
            if act.place.id in seen:
                # Same place on two days: record the extra day rather than dupe.
                for row in out:
                    if row["place"]["id"] == act.place.id:
                        row["days"].append(day.day_number)
                continue
            seen.add(act.place.id)
            out.append(
                {
                    "place": act.place.model_dump(),
                    "days": [day.day_number],
                    "slot": act.slot.value,
                    "start_time": act.start_time,
                    "estimated_cost": act.estimated_cost,
                    "travel_time_minutes": act.travel_time_minutes,
                    "travel_mode": act.travel_mode,
                    "maps_url": places_svc.maps_url(act.place),
                    "is_meal": act.is_meal,
                }
            )
    return out


def nearby(trip: Trip, place_id: str, limit: int = 5) -> list[dict]:
    dest = places_svc.for_trip(trip)
    anchor = dest.by_id(place_id)
    if not anchor:
        return []
    ranked = sorted(
        (p for p in dest.places if p.id != place_id),
        key=lambda p: places_svc.haversine_km(anchor.coordinates, p.coordinates),
    )[:limit]
    return [
        {
            "place": p.model_dump(),
            "distance_km": round(
                places_svc.haversine_km(anchor.coordinates, p.coordinates), 2
            ),
            "walk_minutes": max(
                3, int(places_svc.haversine_km(anchor.coordinates, p.coordinates) * 13)
            ),
            "maps_url": places_svc.maps_url(p),
        }
        for p in ranked
    ]

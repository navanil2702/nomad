"""The proactive engine.

This is the difference between a chatbot and a companion: nobody asks it
anything. It scans the trip against the forecast, the budget and the shape of
each day, and either fixes what it can or raises a specific, actionable alert.

Weather swaps are applied immediately -- a traveller who finds out at 2pm that
it is raining has already lost the afternoon. Every auto-applied alert carries
its own diff so the UI can offer a one-click undo.
"""

from __future__ import annotations

from datetime import date

from ..models.schemas import (
    DayPlan,
    ItineraryChange,
    ProactiveAlert,
    Trip,
    WeatherDay,
)
from . import companion
from . import places as places_svc
from .places import Destination


def _hour_label(hour: int) -> str:
    suffix = "AM" if hour < 12 else "PM"
    display = hour % 12 or 12
    return f"{display} {suffix}"


def _relative_day(day: DayPlan, today: date) -> str:
    delta = (day.date - today).days
    if delta == 0:
        return "today"
    if delta == 1:
        return "tomorrow"
    if 1 < delta <= 6:
        return f"on {day.date:%A}"
    return f"on {day.date:%a %d %b}"


# --------------------------------------------------------------------------
# Scanners
# --------------------------------------------------------------------------


def _scan_weather(
    trip: Trip, dest: Destination, today: date, existing: set[str]
) -> list[ProactiveAlert]:
    """Rain or storms on a day with outdoor stops -> swap them, then say so."""
    alerts: list[ProactiveAlert] = []
    by_date: dict[date, WeatherDay] = {w.date: w for w in trip.weather}

    for day in trip.days:
        if day.date < today:
            continue
        forecast = by_date.get(day.date)
        if not forecast or forecast.condition not in ("rain", "storm", "snow"):
            continue
        if forecast.precipitation_chance < 50:
            continue

        key = f"weather:{day.date.isoformat()}"
        if key in existing:
            continue

        outdoor = [a for a in day.activities if not a.place.indoor and not a.is_meal]
        if not outdoor:
            continue

        changes, _ = companion.handle_rain(trip, dest, day)
        if not changes:
            continue
        changes += companion.enforce_hours(trip)

        when = (
            f" from {_hour_label(forecast.onset_hour)}"
            if forecast.onset_hour is not None
            else ""
        )
        swap = next((c for c in changes if c.kind == "replaced"), None)
        moved = next((c for c in changes if c.kind == "moved"), None)

        message = (
            f"Looks like {forecast.description.lower()} "
            f"{_relative_day(day, today)}{when}, {forecast.precipitation_chance}% chance. "
        )
        if swap:
            message += f"I've swapped {swap.before} for {swap.after}"
        if moved:
            target = trip.day(moved.to_day_number or 0)
            when_moved = f" to day {moved.to_day_number}" + (
                f" ({target.date:%A} morning)" if target else ""
            )
            lead = " and moved" if swap else "I've moved"
            message += f"{lead} {moved.after or moved.before}{when_moved}"
        message += "."

        alerts.append(
            ProactiveAlert(
                trigger="weather",
                dedupe_key=key,
                severity="severe" if forecast.condition == "storm" else "warning",
                title=f"{forecast.description} {_relative_day(day, today)}",
                message=message,
                day_number=day.day_number,
                changes=changes,
                applied=True,
            )
        )

    return alerts


def _scan_budget(trip: Trip, today: date, existing: set[str]) -> list[ProactiveAlert]:
    """Burn rate ahead of trip progress -> offer cheaper days."""
    total_days = len(trip.days)
    if not total_days or trip.preferences.budget <= 0:
        return []

    elapsed = sum(1 for d in trip.days if d.date <= today)
    if elapsed == 0:
        return []

    spent = trip.total_spent()
    if spent == 0:
        return []

    progress = elapsed / total_days
    burn = spent / trip.preferences.budget
    if burn < progress + 0.15:
        return []

    key = f"budget:{today.isoformat()}"
    if key in existing:
        return []

    cur = trip.preferences.currency
    projected = spent / max(elapsed, 1) * total_days
    over = projected - trip.preferences.budget

    return [
        ProactiveAlert(
            trigger="budget",
            dedupe_key=key,
            severity="warning" if over < trip.preferences.budget * 0.2 else "severe",
            title=f"Spending is running {int((burn - progress) * 100)}% ahead",
            message=(
                f"You're {int(progress * 100)}% through the trip and {int(burn * 100)}% "
                f"through the budget. At this rate you'll finish about {cur} {over:,.0f} over. "
                f"Say the word and I'll swap the remaining meals for cheaper ones."
            ),
            applied=False,
        )
    ]


def _scan_pace(trip: Trip, today: date, existing: set[str]) -> list[ProactiveAlert]:
    """Two brutal days back to back -> suggest a breather."""
    alerts: list[ProactiveAlert] = []
    upcoming = [d for d in trip.days if d.date >= today]

    for a, b in zip(upcoming, upcoming[1:]):
        load_a = sum(x.place.walking_intensity for x in a.activities) + a.total_travel_minutes / 30
        load_b = sum(x.place.walking_intensity for x in b.activities) + b.total_travel_minutes / 30
        if load_a < 16 or load_b < 16:
            continue
        key = f"pace:{b.date.isoformat()}"
        if key in existing:
            continue
        alerts.append(
            ProactiveAlert(
                trigger="pace",
                dedupe_key=key,
                severity="info",
                title=f"Days {a.day_number} and {b.day_number} are both heavy",
                message=(
                    f"Back-to-back high-mileage days with {len(a.activities)} and "
                    f"{len(b.activities)} stops. Tell me if you're flagging and I'll "
                    f"thin out day {b.day_number}."
                ),
                day_number=b.day_number,
            )
        )
        break

    return alerts


def _scan_closing(trip: Trip, today: date, existing: set[str]) -> list[ProactiveAlert]:
    """An activity scheduled to run past its venue's closing time."""
    for day in trip.days:
        if day.date < today:
            continue
        for act in day.activities:
            if act.place.opening_hours == "24 hours":
                continue
            if not companion._closes_before(act):
                continue
            key = f"closing:{act.id}"
            if key in existing:
                continue
            closing = act.place.opening_hours.split("-")[-1].strip()
            return [
                ProactiveAlert(
                    trigger="closing",
                    dedupe_key=key,
                    severity="info",
                    title=f"{act.place.name} closes before you'd finish",
                    message=(
                        f"Day {day.day_number} has you at {act.place.name} until "
                        f"{act.end_time}, but it shuts at {closing}. Worth starting "
                        f"the day earlier or letting me move it."
                    ),
                    day_number=day.day_number,
                )
            ]
    return []


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------


def scan(trip: Trip, today: date | None = None) -> list[ProactiveAlert]:
    """Run every scanner, apply what should be applied, return new alerts."""
    today = today or date.today()
    dest = places_svc.for_trip(trip)

    # Alerts carry the key they were raised under, so this never has to
    # reconstruct it and get the format subtly wrong.
    existing = {a.dedupe_key for a in trip.alerts if a.dedupe_key}

    new_alerts: list[ProactiveAlert] = []
    new_alerts += _scan_weather(trip, dest, today, existing)
    new_alerts += _scan_budget(trip, today, existing)
    new_alerts += _scan_pace(trip, today, existing)
    new_alerts += _scan_closing(trip, today, existing)

    if any(a.applied for a in new_alerts):
        from .itinerary import build_budget

        trip.budget_breakdown = build_budget(trip.days, trip.preferences, dest)

    trip.alerts = new_alerts + trip.alerts
    return new_alerts


def apply(trip: Trip, alert: ProactiveAlert) -> ProactiveAlert:
    """Apply a suggestion the traveller accepted."""
    if alert.applied:
        return alert

    dest = places_svc.for_trip(trip)
    today = date.today()
    day = companion.active_day(trip, alert.day_number, today)

    if alert.trigger == "budget":
        changes, _ = companion.handle_over_budget(trip, dest, day)
    elif alert.trigger == "pace":
        changes, _ = companion.handle_tired(trip, dest, day)
    elif alert.trigger == "weather":
        changes, _ = companion.handle_rain(trip, dest, day)
    elif alert.trigger == "closing":
        changes, _ = companion.handle_delayed(trip, dest, day, lost_minutes=0)
    else:
        changes = []

    alert.changes = changes + (companion.enforce_hours(trip) if changes else [])
    alert.applied = True

    from .itinerary import build_budget

    trip.budget_breakdown = build_budget(trip.days, trip.preferences, dest)
    return alert


def undo(trip: Trip, alert: ProactiveAlert) -> ProactiveAlert:
    """Roll back an auto-applied alert."""
    if not alert.applied:
        return alert
    companion.revert(trip, alert.changes)
    alert.applied = False
    alert.dismissed = True
    return alert

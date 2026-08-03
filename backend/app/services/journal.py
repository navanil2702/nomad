"""Memory journal: per-day entries and the end-of-trip retrospective."""

from __future__ import annotations

from datetime import date

from ..models.schemas import DayPlan, JournalEntry, Mood, Trip
from . import llm

_MOOD_BY_SIGNAL: list[tuple[str, Mood]] = [
    ("over", Mood.stressed),
    ("long", Mood.tired),
    ("easy", Mood.calm),
]


def _infer_mood(day: DayPlan, spend: float, daily_budget: float) -> Mood:
    walking = sum(a.place.walking_intensity for a in day.activities)
    if daily_budget and spend > daily_budget * 1.35:
        return Mood.stressed
    if walking >= 16 or day.total_travel_minutes >= 150:
        return Mood.tired
    if len(day.activities) <= 3:
        return Mood.calm
    if day.activities and sum(a.place.rating for a in day.activities) / len(day.activities) >= 4.55:
        return Mood.delighted
    return Mood.happy


def _highlights(day: DayPlan) -> list[str]:
    ranked = sorted(day.activities, key=lambda a: a.place.rating, reverse=True)
    out = []
    for act in ranked[:3]:
        if act.is_meal:
            out.append(f"Ate at {act.place.name}")
        else:
            out.append(f"{act.place.name} — rated {act.place.rating}")
    return out


def build_entry(
    trip: Trip, day: DayPlan, mood: Mood | None = None, note: str | None = None
) -> JournalEntry:
    spend = round(
        sum(e.amount for e in trip.expenses if e.date == day.date), 2
    )
    if spend == 0:
        spend = day.estimated_cost

    daily_budget = trip.preferences.budget / max(len(trip.days), 1)
    places = [a.place.name for a in day.activities]
    meals = [a.place.name for a in day.activities if a.is_meal]
    non_meals = [a.place.name for a in day.activities if not a.is_meal]

    fallback = _template_summary(day, non_meals, meals, spend, trip.preferences.currency)
    summary = llm.narrate_journal(
        destination=trip.preferences.destination,
        day_context={
            "date": day.date.isoformat(),
            "title": day.title,
            "places": non_meals,
            "meals": meals,
            "walking_minutes": day.total_travel_minutes,
            "spend": spend,
            "note_from_traveller": note,
        },
        fallback=fallback,
    )

    return JournalEntry(
        day_number=day.day_number,
        date=day.date,
        title=day.title or f"Day {day.day_number}",
        summary=summary + (f" {note}" if note else ""),
        places_visited=places,
        highlights=_highlights(day),
        spend=spend,
        mood=mood or _infer_mood(day, spend, daily_budget),
    )


def _template_summary(
    day: DayPlan, places: list[str], meals: list[str], spend: float, currency: str
) -> str:
    if not places and not meals:
        return "A quiet day with nothing on the plan."

    parts: list[str] = []
    if places:
        head = places[0]
        rest = places[1:]
        if rest:
            parts.append(
                f"Started at {head}, then {', then '.join(rest)}."
            )
        else:
            parts.append(f"The day was really about {head}.")
    if meals:
        parts.append(
            f"Ate at {meals[0]}" + (f" and {meals[-1]}" if len(meals) > 1 else "") + "."
        )
    if day.total_travel_minutes:
        parts.append(f"About {day.total_travel_minutes} minutes moving between stops.")
    return " ".join(parts)


def ensure_entries_up_to(trip: Trip, today: date) -> list[JournalEntry]:
    """Auto-write entries for every completed day. Idempotent."""
    existing = {e.day_number for e in trip.journal}
    created: list[JournalEntry] = []
    for day in trip.days:
        if day.day_number in existing or day.date > today:
            continue
        entry = build_entry(trip, day)
        trip.journal.append(entry)
        created.append(entry)
    trip.journal.sort(key=lambda e: e.day_number)
    return created


def trip_retrospective(trip: Trip) -> dict:
    """The end-of-trip travel journal."""
    entries = trip.journal
    all_places = [p for e in entries for p in e.places_visited]
    moods = [e.mood for e in entries]
    total_spend = trip.total_spent() or sum(e.spend for e in entries)

    top_mood = max(set(moods), key=moods.count) if moods else Mood.happy
    walking = sum(
        a.place.walking_intensity for d in trip.days for a in d.activities
    )
    travel_minutes = sum(d.total_travel_minutes for d in trip.days)

    highlights = [h for e in entries for h in e.highlights][:6]

    fallback = (
        f"{len(trip.days)} days in {trip.preferences.destination}, "
        f"{len(set(all_places))} places, and {trip.preferences.currency} "
        f"{total_spend:,.0f} spent between {trip.preferences.travelers}. "
        f"Mostly {top_mood.value}."
    )
    closing = llm.narrate_journal(
        destination=trip.preferences.destination,
        day_context={
            "whole_trip": True,
            "days": len(trip.days),
            "places": list(dict.fromkeys(all_places))[:20],
            "spend": total_spend,
            "dominant_mood": top_mood.value,
        },
        fallback=fallback,
    )

    return {
        "title": trip.title or f"{trip.preferences.destination} trip",
        "closing": closing,
        "stats": {
            "days": len(trip.days),
            "places": len(set(all_places)),
            "meals": sum(
                1 for d in trip.days for a in d.activities if a.is_meal
            ),
            "spend": round(total_spend, 2),
            "travel_minutes": travel_minutes,
            "walking_score": walking,
            "dominant_mood": top_mood.value,
        },
        "highlights": highlights,
        "entries": entries,
    }

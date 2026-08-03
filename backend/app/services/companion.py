"""The travel companion.

Two halves, deliberately separated:

  1. `detect_intent` reads what the traveller said and classifies the
     *situation* (rain, fatigue, delay, overspend, ...).
  2. A handler per situation performs concrete, typed mutations on the
     itinerary and returns an ItineraryChange for each one.

The language model never decides what changes -- it only phrases changes that
already happened. That is what keeps the companion trustworthy: it cannot
promise a swap it did not make, and every reply is backed by a real diff.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from ..models.schemas import (
    Activity,
    DayPlan,
    Interest,
    ItineraryChange,
    Place,
    Slot,
    Trip,
    TripPreferences,
)
from . import llm
from . import places as places_svc
from .places import Destination

# --------------------------------------------------------------------------
# Intent detection
# --------------------------------------------------------------------------

INTENT_PATTERNS: list[tuple[str, list[str]]] = [
    ("rain", [r"\brain", r"\bpour", r"\bwet\b", r"\bstorm", r"\bdrizzl", r"\bthunder", r"bad weather", r"\bsnow"]),
    ("tired", [r"\btired\b", r"\bexhaust", r"\bknacker", r"\bworn out\b", r"\bfeet hurt", r"\bsore\b", r"\brest\b", r"too much walking", r"\bslow down\b", r"\bjet ?lag"]),
    ("hungry", [r"\bhungry\b", r"\bstarv", r"\beat\b", r"\bfood\b", r"\blunch\b", r"\bdinner\b", r"\bbreakfast\b", r"\bsnack\b", r"\bwhere.*eat"]),
    ("dietary", [r"\bvegetarian\b", r"\bvegan\b", r"\bveggie\b", r"\bhalal\b", r"\bkosher\b", r"\bgluten"]),
    ("delayed", [r"\bdelay", r"\blate\b", r"\bmissed\b", r"\btrain\b.*\b(late|delay)", r"\bflight\b.*\b(late|delay)", r"\brunning behind", r"\bstuck\b", r"\bcancel"]),
    ("over_budget", [r"\bover ?budget", r"\bspent more", r"\btoo expensive", r"\bcheaper\b", r"\bsave money", r"\bbudget\b.*\b(tight|blown|gone)", r"\bovershot", r"\bcosting too much"]),
    ("free_time", [r"\bfree (hour|hours|time)\b", r"\b(\d+|one|two|three|a couple of) (hour|hours)\b.*\b(free|spare|kill)\b", r"\bnothing to do\b", r"\bwhat should i do\b", r"\bspare time\b", r"\bkill (some )?time\b"]),
    ("nearby", [r"\bnearby\b", r"\bnear me\b", r"\bclose by\b", r"\baround here\b", r"\bwhat'?s around"]),
    ("weather_q", [r"\bweather\b", r"\bforecast\b", r"\bhow (hot|cold|warm)\b", r"\btemperature\b"]),
    ("budget_q", [r"\bhow much\b.*\b(left|spent|budget)", r"\bremaining budget\b", r"\bmy budget\b"]),
    ("packing_q", [r"\bpack\b", r"\bbring\b", r"\bwhat should i wear\b"]),
    ("phrase_q", [r"\bhow do (i|you) say\b", r"\btranslate\b", r"\bin (japanese|french|italian|spanish|portuguese|indonesian)\b", r"\bphrase"]),
    ("plan_q", [r"\bwhat'?s (the plan|next|today|tomorrow)\b", r"\bmy (plan|itinerary|schedule)\b", r"\bwhere am i going\b"]),
]


KNOWN_INTENTS = [name for name, _ in INTENT_PATTERNS] + ["general"]


def detect_intent(message: str) -> str:
    """Classify the situation.

    Keywords first — they are free, instant and cover the phrasings people
    actually use. Only when they find nothing at all does the model get asked,
    and even then it may only choose a label from the known set. Every action
    downstream is still taken by deterministic code.
    """
    text = message.lower().strip()
    scores: dict[str, int] = {}
    for intent, patterns in INTENT_PATTERNS:
        hits = sum(1 for p in patterns if re.search(p, text))
        if hits:
            scores[intent] = hits

    if not scores:
        return llm.classify_intent(message, KNOWN_INTENTS) or "general"

    # A dietary request is a more specific hunger; delay beats rain if both.
    if "dietary" in scores:
        return "dietary"
    priority = ["over_budget", "delayed", "rain", "tired", "free_time", "hungry"]
    for intent in priority:
        if intent in scores:
            return intent
    return max(scores, key=lambda k: scores[k])


# --------------------------------------------------------------------------
# Itinerary mutation primitives
# --------------------------------------------------------------------------


def _fmt(minutes: int) -> str:
    minutes = int(minutes) % (24 * 60)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _parse(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


SLOT_ORDER = {Slot.morning: 0, Slot.afternoon: 1, Slot.evening: 2}


# A day ends. Anything that would start after this could not happen today.
END_OF_DAY = 23 * 60 + 30


def retime_day(
    day: DayPlan, *, start_minutes: int | None = None, slack: int = 20
) -> list[Activity]:
    """Recompute travel times, start and end times down the whole day.

    Returns the activities that spilled past the end of the day. Times are
    formatted modulo 24h, so without this an overrun would silently reappear as
    an early-morning slot and look perfectly reachable to every later check.
    """
    day.activities.sort(key=lambda a: (SLOT_ORDER[a.slot], _parse(a.start_time)))
    if not day.activities:
        day.recompute()
        return []

    clock = start_minutes if start_minutes is not None else _parse(day.activities[0].start_time)
    prev: Place | None = None
    overflow: list[Activity] = []

    for act in day.activities:
        if prev is None:
            act.travel_time_minutes = 0
            act.travel_mode = "walk"
            act.maps_url = places_svc.maps_url(act.place)
        else:
            minutes, mode = places_svc.travel_estimate(prev, act.place)
            act.travel_time_minutes = minutes
            act.travel_mode = mode  # type: ignore[assignment]
            act.maps_url = places_svc.directions_url(
                prev, act.place, "walking" if mode == "walk" else "transit"
            )
            clock += minutes

        # Keep meals and evenings anchored to sensible hours.
        if act.is_meal and act.slot == Slot.afternoon:
            clock = max(clock, 12 * 60)
        if act.slot == Slot.evening and not act.is_meal:
            clock = max(clock, 17 * 60 + 30)
        if act.is_meal and act.slot == Slot.evening:
            clock = max(clock, 19 * 60)

        # Respect the venue's hours: never arrive early, never overrun closing.
        from .itinerary import opening_window

        opens, closes = opening_window(act.place)
        clock = max(clock, opens)
        if clock + act.duration_minutes > closes:
            act.duration_minutes = max(30, closes - clock)

        if clock > END_OF_DAY:
            overflow.append(act)

        act.start_time = _fmt(clock)
        act.end_time = _fmt(clock + act.duration_minutes)
        clock += act.duration_minutes + slack
        prev = act.place

    day.recompute()
    return overflow


def make_activity(
    place: Place, slot: Slot, prefs: TripPreferences, *, is_meal: bool = False, origin: str = "companion"
) -> Activity:
    return Activity(
        slot=slot,
        title=place.name,
        place=place,
        duration_minutes=places_svc.base_duration(place),
        estimated_cost=places_svc.activity_cost(place, prefs),
        maps_url=places_svc.maps_url(place),
        local_tip=place.description,
        is_meal=is_meal,
        origin=origin,  # type: ignore[arg-type]
    )


def replace_activity(
    day: DayPlan, activity: Activity, new_place: Place, prefs: TripPreferences, *, origin: str = "companion"
) -> ItineraryChange:
    old_name = activity.place.name
    old_id = activity.place.id
    activity.place = new_place
    activity.title = new_place.name
    activity.duration_minutes = places_svc.base_duration(new_place)
    activity.estimated_cost = places_svc.activity_cost(new_place, prefs)
    activity.local_tip = new_place.description
    activity.origin = origin  # type: ignore[assignment]
    activity.note = f"Swapped in for {old_name}"
    return ItineraryChange(
        kind="replaced",
        day_number=day.day_number,
        summary=f"{old_name} → {new_place.name}",
        before=old_name,
        after=new_place.name,
        before_place_id=old_id,
        after_place_id=new_place.id,
        activity_id=activity.id,
    )


def move_activity(trip: Trip, source: DayPlan, activity: Activity, target: DayPlan, slot: Slot) -> ItineraryChange:
    source.activities = [a for a in source.activities if a.id != activity.id]

    # Moving somewhere the traveller is already going that day would just
    # produce the same stop twice. Dropping it is the honest outcome.
    if any(a.place.id == activity.place.id for a in target.activities):
        retime_day(source)
        return ItineraryChange(
            kind="removed",
            day_number=source.day_number,
            summary=(
                f"Dropped {activity.place.name} — it's already on day "
                f"{target.day_number}"
            ),
            before=activity.place.name,
            before_place_id=activity.place.id,
            activity_id=activity.id,
        )

    activity.slot = slot
    activity.origin = "companion"
    activity.note = f"Moved from day {source.day_number}"
    target.activities.append(activity)
    retime_day(source)
    retime_day(target)
    return ItineraryChange(
        kind="moved",
        day_number=source.day_number,
        to_day_number=target.day_number,
        summary=f"{activity.place.name} moved to day {target.day_number} ({target.date:%a})",
        before=f"Day {source.day_number}",
        after=f"Day {target.day_number}",
        activity_id=activity.id,
        after_place_id=activity.place.id,
    )


def insert_activity(day: DayPlan, activity: Activity) -> ItineraryChange:
    day.activities.append(activity)
    retime_day(day)
    return ItineraryChange(
        kind="added",
        day_number=day.day_number,
        summary=f"Added {activity.place.name} at {activity.start_time}",
        after=activity.place.name,
        after_place_id=activity.place.id,
        activity_id=activity.id,
    )


def remove_activity(day: DayPlan, activity: Activity, reason: str) -> ItineraryChange:
    day.activities = [a for a in day.activities if a.id != activity.id]
    retime_day(day)
    return ItineraryChange(
        kind="removed",
        day_number=day.day_number,
        summary=f"Dropped {activity.place.name} — {reason}",
        before=activity.place.name,
        before_place_id=activity.place.id,
        activity_id=activity.id,
    )


# --------------------------------------------------------------------------
# Context helpers
# --------------------------------------------------------------------------


def enforce_hours(trip: Trip) -> list[ItineraryChange]:
    """Guarantee the plan is physically possible after a mutation.

    Inserting or shifting a stop pushes everything after it later, which can
    leave a museum scheduled for an hour after it locks the doors. Rather than
    show an itinerary that cannot be followed, anything that no longer fits is
    swapped for somewhere open, pushed to the next day, or dropped.
    """
    from .itinerary import opening_window

    dest = places_svc.for_trip(trip)
    fixes: list[ItineraryChange] = []

    def unreachable(act: Activity, spilled: set[str]) -> bool:
        if act.id in spilled:
            return True
        _, closes = opening_window(act.place)
        return _parse(act.start_time) + 30 > closes

    for day in trip.days:
        # Retime first so overflow past midnight is detected rather than being
        # read back as an early-morning start.
        spilled = {a.id for a in retime_day(day)}

        # Only touch days that are actually broken. Beyond that, retiming a
        # healthy day would quietly shift times the planner had balanced.
        if not any(unreachable(a, spilled) for a in day.activities):
            continue

        for act in list(day.activities):
            if not unreachable(act, spilled):
                continue

            here = {a.place.id for a in day.activities}
            if act.is_meal:
                alt = _best(
                    [p for p in dest.meals if open_during(p, act.start_time)],
                    _used_place_ids(trip),
                    forbid=here,
                )
                if alt and alt.id != act.place.id:
                    fixes.append(
                        replace_activity(day, act, alt, trip.preferences)
                    )
                    continue

            target = next(
                (d for d in trip.days if d.day_number > day.day_number), None
            )
            # Pushing a third meal onto another day helps nobody — two sittings
            # a day is the plan's shape, so a surplus meal is dropped instead.
            target_meals = sum(1 for a in target.activities if a.is_meal) if target else 0
            if target and not (act.is_meal and target_meals >= 2):
                fixes.append(move_activity(trip, day, act, target, act.slot))
            else:
                fixes.append(
                    remove_activity(
                        day, act, "it would be shut by the time you got there"
                    )
                )
        retime_day(day)

    return fixes


def active_day(trip: Trip, day_number: int | None = None, today: date | None = None) -> DayPlan:
    """The day the traveller is talking about: explicit, else today, else day 1."""
    if day_number is not None:
        day = trip.day(day_number)
        if day:
            return day
    today = today or date.today()
    for day in trip.days:
        if day.date == today:
            return day
    for day in trip.days:
        if day.date >= today:
            return day
    return trip.days[0]


def remaining_activities(day: DayPlan, now_minutes: int | None = None) -> list[Activity]:
    """Activities still ahead. Falls back to the whole day for a future date."""
    if now_minutes is None:
        return list(day.activities)
    ahead = [a for a in day.activities if _parse(a.start_time) >= now_minutes]
    return ahead or list(day.activities)


def _used_place_ids(trip: Trip) -> set[str]:
    return {a.place.id for d in trip.days for a in d.activities}


def open_during(place: Place, start_hhmm: str, minutes: int = 45) -> bool:
    """Is this place actually open for a visit starting at `start_hhmm`?"""
    from .itinerary import opening_window

    opens, closes = opening_window(place)
    start = max(_parse(start_hhmm), opens)
    return closes - start >= minutes


def _best(
    candidates: list[Place],
    exclude: set[str],
    key=None,
    *,
    open_at: str | None = None,
    forbid: set[str] | None = None,
) -> Place | None:
    """Pick the best candidate.

    `forbid` is absolute — used for places already on the day being edited, so
    a swap can never produce the same stop twice. `exclude` is only a
    preference (places used elsewhere on the trip), relaxed when nothing else
    is left.
    """
    pool = [p for p in candidates if p.id not in (forbid or set())]
    if not pool:
        return None

    preferred = [p for p in pool if p.id not in exclude]
    pool = preferred or pool

    if open_at is not None:
        # A swap that lands on a shut venue is worse than no swap at all.
        available = [p for p in pool if open_during(p, open_at)]
        if available:
            pool = available

    return max(pool, key=key or (lambda p: p.rating))


# --------------------------------------------------------------------------
# Situation handlers -- each returns (changes, fallback_reply)
# --------------------------------------------------------------------------


def handle_rain(trip: Trip, dest: Destination, day: DayPlan) -> tuple[list[ItineraryChange], str]:
    outdoor = [a for a in day.activities if not a.place.indoor and not a.is_meal]
    if not outdoor:
        return [], (
            f"You're already covered — everything left on day {day.day_number} is indoors. "
            "Stay where you are and let it pass."
        )

    used = _used_place_ids(trip)
    changes: list[ItineraryChange] = []
    indoor_pool = dest.indoor_attractions()

    for act in outdoor[:2]:
        replacement = _best(
            [p for p in indoor_pool if p.category == act.place.category] or indoor_pool,
            used,
            open_at=act.start_time,
            forbid={a.place.id for a in day.activities},
        )
        if not replacement or not open_during(replacement, act.start_time):
            continue
        used.add(replacement.id)
        changes.append(replace_activity(day, act, replacement, trip.preferences))

    # Anything outdoors that survived gets pushed to the driest later day.
    leftover = [a for a in day.activities if not a.place.indoor and not a.is_meal]
    dry_day = _driest_later_day(trip, day)
    if leftover and dry_day:
        changes.append(move_activity(trip, day, leftover[0], dry_day, leftover[0].slot))

    retime_day(day)

    swapped = ", ".join(f"{c.before} → {c.after}" for c in changes if c.kind == "replaced")
    reply = f"Rain's in. I've moved you indoors: {swapped}." if swapped else "Rain's in."
    moved = next((c for c in changes if c.kind == "moved"), None)
    if moved:
        reply += f" {moved.summary}, where the forecast is drier."
    return changes, reply


def _driest_later_day(trip: Trip, day: DayPlan) -> DayPlan | None:
    later = [d for d in trip.days if d.day_number > day.day_number]
    if not later:
        return None
    by_date = {w.date: w for w in trip.weather}
    def dryness(d: DayPlan) -> tuple[int, int]:
        w = by_date.get(d.date)
        return (w.precipitation_chance if w else 50, len(d.activities))
    return min(later, key=dryness)


def handle_tired(trip: Trip, dest: Destination, day: DayPlan) -> tuple[list[ItineraryChange], str]:
    changes: list[ItineraryChange] = []
    strenuous = sorted(
        [a for a in day.activities if not a.is_meal and a.place.walking_intensity >= 4],
        key=lambda a: a.place.walking_intensity,
        reverse=True,
    )
    used = _used_place_ids(trip)

    if strenuous:
        target = strenuous[0]
        easy = _best(
            dest.low_effort_attractions(),
            used,
            key=lambda p: (p.rating - p.walking_intensity * 0.3),
            open_at=target.start_time,
            forbid={a.place.id for a in day.activities},
        )
        later = _driest_later_day(trip, day)
        if later:
            changes.append(move_activity(trip, day, target, later, target.slot))
        elif easy:
            changes.append(replace_activity(day, target, easy, trip.preferences))
        else:
            changes.append(remove_activity(day, target, "you're running on empty"))

    cafe = _best(
        dest.restful_meals() or dest.meals,
        used,
        open_at="15:00",
        forbid={a.place.id for a in day.activities},
    )
    if cafe and not any(a.place.id == cafe.id for a in day.activities):
        act = make_activity(cafe, Slot.afternoon, trip.preferences, is_meal=True)
        act.duration_minutes = 60
        act.note = "A deliberate sit-down"
        changes.append(insert_activity(day, act))

    retime_day(day, slack=40)

    if not changes:
        return [], "Nothing on today is demanding — take the afternoon slowly, the plan can absorb it."

    moved = next((c for c in changes if c.kind in ("moved", "replaced", "removed")), None)
    added = next((c for c in changes if c.kind == "added"), None)
    reply = "Cutting the mileage. "
    if moved:
        reply += f"{moved.summary}. "
    if added:
        reply += f"I've also put a proper sit-down at {added.after} into the afternoon "
        reply += "and widened the gaps between stops."
    return changes, reply.strip()


def handle_hungry(
    trip: Trip, dest: Destination, day: DayPlan, vegetarian: bool = False
) -> tuple[list[ItineraryChange], str]:
    pool = dest.vegetarian_meals() if vegetarian else dest.meals
    if vegetarian and not pool:
        pool = [p for p in dest.meals if p.price_level <= 2]

    anchor = next(
        (a.place for a in reversed(day.activities) if not a.is_meal), None
    ) or dest.attractions[0]

    def proximity(p: Place) -> float:
        km = places_svc.haversine_km(anchor.coordinates, p.coordinates)
        return p.rating - km * 0.8

    used = _used_place_ids(trip)
    # Suggesting a restaurant they are already booked into today is useless,
    # so those are removed outright rather than merely penalised.
    today_ids = {a.place.id for a in day.activities}
    fresh = [p for p in pool if p.id not in today_ids]
    if not fresh:
        already = next((p for p in pool if p.id in today_ids), None)
        kind = "vegetarian place" if vegetarian else "option"
        return [], (
            f"The only {kind} I'd send you to nearby is {already.name if already else 'already on your plan'}, "
            "and it's already on today's plan. Stick with it."
        )
    pool = fresh
    slot_time = "19:30" if any(a.is_meal and a.slot == Slot.afternoon for a in day.activities) else "12:30"
    pick = _best(pool, used, key=proximity, open_at=slot_time)
    if not pick:
        return [], "I can't find anywhere open near you right now."

    # Slot it as lunch or dinner depending on what the day is missing.
    has_lunch = any(a.is_meal and a.slot == Slot.afternoon for a in day.activities)
    slot = Slot.evening if has_lunch else Slot.afternoon
    act = make_activity(pick, slot, trip.preferences, is_meal=True)
    change = insert_activity(day, act)
    retime_day(day)

    km = places_svc.haversine_km(anchor.coordinates, pick.coordinates)
    walk = int(km * 13)
    kind = "vegetarian " if vegetarian else ""
    return [change], (
        f"{pick.name} — {kind}food, {pick.rating}★, about {max(walk, 3)} minutes from {anchor.name}. "
        f"{pick.description} I've slotted it in at {act.start_time}."
    )


def handle_delayed(trip: Trip, dest: Destination, day: DayPlan, lost_minutes: int = 120) -> tuple[list[ItineraryChange], str]:
    ahead = [a for a in day.activities if not a.is_meal]
    if not ahead:
        return [], "Nothing time-critical left today, so a delay costs you nothing."

    changes: list[ItineraryChange] = []

    # Drop the lowest-value stop to buy back the lost time, and push the rest.
    if len(ahead) > 1 and lost_minutes >= 60:
        weakest = min(ahead, key=lambda a: a.place.rating)
        later = _driest_later_day(trip, day)
        if later:
            changes.append(move_activity(trip, day, weakest, later, weakest.slot))
        else:
            changes.append(remove_activity(day, weakest, "the delay ate the window"))

    first = day.activities[0] if day.activities else None
    if first:
        new_start = _parse(first.start_time) + lost_minutes
        retime_day(day, start_minutes=min(new_start, 15 * 60))
        changes.append(
            ItineraryChange(
                kind="reordered",
                day_number=day.day_number,
                summary=f"Everything shifted {lost_minutes // 60}h later, now starting {day.activities[0].start_time}",
            )
        )

    closing_risk = [
        a for a in day.activities
        if not a.is_meal and a.place.opening_hours != "24 hours"
        and _closes_before(a)
    ]
    reply = f"Rebuilt the day around the delay. Everything now starts at {day.activities[0].start_time}. "
    dropped = next((c for c in changes if c.kind in ("moved", "removed")), None)
    if dropped:
        reply += f"{dropped.summary}. "
    if closing_risk:
        reply += f"Heads up: {closing_risk[0].place.name} closes at {closing_risk[0].place.opening_hours.split('-')[-1].strip()}."
    return changes, reply.strip()


def _closes_before(act: Activity) -> bool:
    """True when the visit would run past the venue's closing time."""
    from .itinerary import opening_window

    _, closes = opening_window(act.place)
    return _parse(act.end_time) > closes


def handle_over_budget(trip: Trip, dest: Destination, day: DayPlan) -> tuple[list[ItineraryChange], str]:
    changes: list[ItineraryChange] = []
    used = _used_place_ids(trip)
    cheap = dest.cheap_meals()
    saved = 0.0

    upcoming = [d for d in trip.days if d.day_number >= day.day_number]

    for d in upcoming[:3]:
        for act in d.activities:
            if not act.is_meal or act.place.price_level <= 1:
                continue
            replacement = _best(
                cheap, used, key=lambda p: p.rating - p.price_level,
                open_at=act.start_time,
                forbid={a.place.id for a in d.activities},
            )
            if not replacement or replacement.id == act.place.id:
                continue
            before_cost = act.estimated_cost
            saving = before_cost - places_svc.activity_cost(
                replacement, trip.preferences
            )
            if saving <= 0:
                continue  # a "cheaper" option that costs more is not an answer
            used.add(replacement.id)
            change = replace_activity(d, act, replacement, trip.preferences)
            change.kind = "downgraded"
            change.summary = (
                f"{change.before} → {change.after} "
                f"(saves {trip.preferences.currency} {before_cost - act.estimated_cost:.0f})"
            )
            saved += before_cost - act.estimated_cost
            changes.append(change)

        # Drop the priciest non-meal stop on the most expensive day.
        paid = [a for a in d.activities if not a.is_meal and a.estimated_cost > 0]
        if paid and d.estimated_cost > trip.preferences.budget / max(len(trip.days), 1):
            priciest = max(paid, key=lambda a: a.estimated_cost)
            free_alt = _best(
                [p for p in dest.attractions if places_svc.base_cost(p) == 0],
                used,
                forbid={a.place.id for a in d.activities},
            )
            if free_alt:
                saved += priciest.estimated_cost
                used.add(free_alt.id)
                change = replace_activity(d, priciest, free_alt, trip.preferences)
                change.kind = "downgraded"
                change.summary = f"{change.before} → {change.after} (free entry)"
                changes.append(change)
        retime_day(d)

    remaining = trip.remaining_budget()
    if not changes:
        return [], (
            f"You've got {trip.preferences.currency} {remaining:,.0f} left and nothing "
            "obviously expensive coming up — you're fine."
        )

    return changes, (
        f"Trimmed {trip.preferences.currency} {saved:,.0f} out of the next few days. "
        f"{changes[0].summary}. That puts you back on track against your "
        f"{trip.preferences.currency} {trip.preferences.budget:,.0f} budget."
    )


def handle_free_time(
    trip: Trip, dest: Destination, day: DayPlan, minutes: int = 120
) -> tuple[list[ItineraryChange], str]:
    anchor = next((a.place for a in reversed(day.activities) if not a.is_meal), None)
    used = _used_place_ids(trip)

    def fit(p: Place) -> float:
        duration = places_svc.base_duration(p)
        if duration > minutes:
            return -100.0
        km = places_svc.haversine_km(anchor.coordinates, p.coordinates) if anchor else 0
        return p.rating * 2 - km * 0.4 - abs(minutes - duration) / 60

    now = day.activities[-1].end_time if day.activities else "14:00"
    today_ids = {a.place.id for a in day.activities}
    fresh = [p for p in dest.attractions if p.id not in today_ids] or dest.attractions
    pick = _best(fresh, used, key=fit, open_at=now)
    if not pick or fit(pick) < -50:
        meals = [
            p for p in (dest.restful_meals() or dest.meals) if p.id not in today_ids
        ] or dest.meals
        pick = _best(meals, used, key=fit, open_at=now)
    if not pick:
        return [], f"Nothing nearby fits neatly into {minutes} minutes — take the break."

    act = make_activity(pick, Slot.afternoon, trip.preferences)
    act.duration_minutes = min(places_svc.base_duration(pick), minutes - 20)
    change = insert_activity(day, act)

    km = places_svc.haversine_km(anchor.coordinates, pick.coordinates) if anchor else 0
    return [change], (
        f"{minutes} minutes is exactly enough for {pick.name} — "
        f"{int(km * 13) if km else 10} minutes away, {act.duration_minutes} minutes inside. "
        f"{pick.description} It's on the plan at {act.start_time}."
    )


# --------------------------------------------------------------------------
# Informational answers (no mutation)
# --------------------------------------------------------------------------


def _answer_weather(trip: Trip, day: DayPlan) -> str:
    w = next((x for x in trip.weather if x.date == day.date), None)
    if not w:
        return "I don't have a forecast for that day yet."
    line = (
        f"Day {day.day_number} ({day.date:%a %d %b}): {w.description.lower()}, "
        f"{w.temp_min_c:.0f}–{w.temp_max_c:.0f}°C, {w.precipitation_chance}% chance of rain."
    )
    if w.condition in ("rain", "storm"):
        indoor = sum(1 for a in day.activities if a.place.indoor)
        line += f" {indoor} of {len(day.activities)} stops that day are already indoors."
    return line


def _answer_budget(trip: Trip) -> str:
    spent, remaining = trip.total_spent(), trip.remaining_budget()
    cur = trip.preferences.currency
    days_left = max(
        sum(1 for d in trip.days if d.date >= date.today()), 1
    )
    per_day = remaining / days_left
    status = "comfortable" if per_day > 60 else "tight"
    return (
        f"Spent {cur} {spent:,.0f} of {cur} {trip.preferences.budget:,.0f}. "
        f"{cur} {remaining:,.0f} left across {days_left} day{'s' if days_left != 1 else ''} — "
        f"about {cur} {per_day:,.0f} a day, which is {status}."
    )


def _answer_nearby(trip: Trip, dest: Destination, day: DayPlan) -> str:
    anchor = next((a.place for a in reversed(day.activities) if not a.is_meal), None)
    if not anchor:
        anchor = dest.attractions[0]
    ranked = sorted(
        [p for p in dest.places if p.id != anchor.id],
        key=lambda p: places_svc.haversine_km(anchor.coordinates, p.coordinates),
    )[:3]
    lines = [
        f"{p.name} ({int(places_svc.haversine_km(anchor.coordinates, p.coordinates) * 13)} min, {p.rating}★)"
        for p in ranked
    ]
    return f"Closest to {anchor.name}: " + "; ".join(lines) + "."


def _answer_plan(trip: Trip, day: DayPlan) -> str:
    if not day.activities:
        return f"Day {day.day_number} is empty. Tell me what you feel like and I'll fill it."
    lines = [
        f"{a.start_time} {a.place.name}" + (" (meal)" if a.is_meal else "")
        for a in day.activities
    ]
    return (
        f"Day {day.day_number}, {day.date:%a %d %b} — {day.title}. "
        + " · ".join(lines)
        + f". Roughly {trip.preferences.currency} {day.estimated_cost:,.0f}."
    )


def _answer_phrases(trip: Trip, dest: Destination, message: str) -> str:
    from ..data.knowledge import PHRASES

    phrases = PHRASES.get(dest.language, PHRASES["English"])
    lower = message.lower()
    match = next(
        (p for p in phrases if any(w in lower for w in p["english"].lower().split() if len(w) > 3)),
        None,
    )
    if match:
        return f"\"{match['english']}\" is \"{match['local']}\" — {match['pronunciation']}."
    picks = phrases[:3]
    return f"The three that earn their keep in {dest.language}: " + "; ".join(
        f"{p['english']} = {p['local']} ({p['pronunciation']})" for p in picks
    ) + "."


def _answer_packing(trip: Trip) -> str:
    unpacked = [i for i in trip.packing_list if not i.packed]
    essential = [i for i in unpacked if i.essential]
    weather_items = [i for i in unpacked if i.category == "weather"]
    bits = []
    if essential:
        bits.append("Still unticked and non-negotiable: " + ", ".join(i.label for i in essential[:3]))
    if weather_items:
        bits.append("and the forecast says " + ", ".join(i.label.lower() for i in weather_items[:2]))
    return (". ".join(bits) + ".") if bits else "Your packing list is fully ticked off."


def _extract_hours(message: str) -> int:
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "half an": 0}
    m = re.search(r"(\d+)\s*(hour|hr)", message.lower())
    if m:
        return int(m.group(1)) * 60
    for word, n in words.items():
        if re.search(rf"\b{word}\s+(hour|hr)", message.lower()):
            return n * 60
    m = re.search(r"(\d+)\s*(minute|min)", message.lower())
    if m:
        return int(m.group(1))
    return 120


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def respond(
    trip: Trip, message: str, day_number: int | None = None
) -> tuple[str, list[ItineraryChange], str]:
    """Returns (reply, changes, intent)."""
    dest = places_svc.for_trip(trip)
    day = active_day(trip, day_number)
    intent = detect_intent(message)

    changes: list[ItineraryChange] = []

    if intent == "rain":
        changes, fallback = handle_rain(trip, dest, day)
    elif intent == "tired":
        changes, fallback = handle_tired(trip, dest, day)
    elif intent == "dietary":
        changes, fallback = handle_hungry(trip, dest, day, vegetarian=True)
    elif intent == "hungry":
        changes, fallback = handle_hungry(trip, dest, day)
    elif intent == "delayed":
        changes, fallback = handle_delayed(trip, dest, day, _extract_hours(message))
    elif intent == "over_budget":
        changes, fallback = handle_over_budget(trip, dest, day)
    elif intent == "free_time":
        changes, fallback = handle_free_time(trip, dest, day, _extract_hours(message))
    elif intent == "weather_q":
        fallback = _answer_weather(trip, day)
    elif intent == "budget_q":
        fallback = _answer_budget(trip)
    elif intent == "nearby":
        fallback = _answer_nearby(trip, dest, day)
    elif intent == "plan_q":
        fallback = _answer_plan(trip, day)
    elif intent == "phrase_q":
        fallback = _answer_phrases(trip, dest, message)
    elif intent == "packing_q":
        fallback = _answer_packing(trip)
    else:
        fallback = (
            f"{_answer_plan(trip, day)} Tell me what's actually happening — "
            "rain, tired feet, a delayed train, an overspend — and I'll rework it."
        )

    if changes:
        changes += enforce_hours(trip)
        trip.budget_breakdown = _rebuild_budget(trip, dest)

    reply = llm.narrate_change(
        destination=trip.preferences.destination,
        user_message=message,
        intent=intent,
        changes=[c.summary for c in changes],
        context={
            "day": day.day_number,
            "date": day.date.isoformat(),
            "plan_now": [
                {"time": a.start_time, "place": a.place.name, "indoor": a.place.indoor}
                for a in day.activities
            ],
            "budget_remaining": trip.remaining_budget(),
            "currency": trip.preferences.currency,
            "forecast": next(
                (
                    {"condition": w.condition, "rain_chance": w.precipitation_chance}
                    for w in trip.weather
                    if w.date == day.date
                ),
                None,
            ),
        },
        fallback=fallback,
    )
    return reply, changes, intent


def _rebuild_budget(trip: Trip, dest: Destination):
    from .itinerary import build_budget

    return build_budget(trip.days, trip.preferences, dest)


def revert(trip: Trip, changes: list[ItineraryChange]) -> None:
    """Undo an auto-applied set of changes. Handles replace and move."""
    dest = places_svc.for_trip(trip)
    for change in reversed(changes):
        if change.kind in ("replaced", "downgraded") and change.before_place_id:
            original = dest.by_id(change.before_place_id)
            day = trip.day(change.day_number)
            if not (original and day):
                continue
            act = next((a for a in day.activities if a.id == change.activity_id), None)
            if act:
                act.place = original
                act.title = original.name
                act.duration_minutes = places_svc.base_duration(original)
                act.estimated_cost = places_svc.activity_cost(original, trip.preferences)
                act.local_tip = original.description
                act.origin = "planned"
                act.note = None
                retime_day(day)
        elif change.kind == "moved" and change.to_day_number:
            source = trip.day(change.to_day_number)
            target = trip.day(change.day_number)
            if not (source and target):
                continue
            act = next((a for a in source.activities if a.id == change.activity_id), None)
            if act:
                source.activities = [a for a in source.activities if a.id != act.id]
                act.origin = "planned"
                act.note = None
                target.activities.append(act)
                retime_day(source)
                retime_day(target)
    trip.budget_breakdown = _rebuild_budget(trip, dest)

"""Itinerary generation.

A deterministic planner that scores the place catalog against the traveller's
interests, pace, budget and the actual forecast, then lays the winners out on
a clock with real travel times between them.

It runs with no API key. When one is present, services/llm.py rewrites the
day titles and summaries in a warmer voice on top of this structure -- the
plan itself stays deterministic so the companion can reason about it.
"""

from __future__ import annotations

import math
from datetime import date, timedelta

from ..models.schemas import (
    Activity,
    BudgetBreakdown,
    DayPlan,
    Interest,
    Pace,
    Place,
    Slot,
    Trip,
    TripPreferences,
    WeatherDay,
)
from . import places as places_svc
from .places import Destination

# attractions per day, day start, minutes of slack between stops
PACE_CONFIG: dict[Pace, tuple[int, int, int]] = {
    Pace.relaxed: (3, 10 * 60, 35),
    Pace.balanced: (4, 9 * 60, 20),
    Pace.packed: (5, 8 * 60 + 30, 10),
}

DAY_THEMES = [
    "Landing softly",
    "The big hitters",
    "Wander and eat",
    "Off the main drag",
    "Green and slow",
    "Neighbourhood day",
    "One last look",
]


def _fmt(minutes: int) -> str:
    minutes = int(minutes) % (24 * 60)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _parse(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


# Typical window each slot occupies, used to check a venue is actually open.
SLOT_WINDOW: dict[Slot, tuple[int, int]] = {
    Slot.morning: (9 * 60, 12 * 60 + 30),
    Slot.afternoon: (13 * 60, 17 * 60),
    Slot.evening: (18 * 60, 22 * 60),
}


def opening_window(place: Place) -> tuple[int, int]:
    """(open, close) in minutes. Closing past midnight is clamped to 23:59."""
    hours = place.opening_hours.strip()
    if "24" in hours and "hour" in hours.lower():
        return 0, 24 * 60
    try:
        opens, closes = [part.strip() for part in hours.split("-")]
        start, end = _parse(opens), _parse(closes)
        if end <= start:  # e.g. 18:00 - 02:00
            end = 24 * 60 - 1
        return start, end
    except Exception:
        return 9 * 60, 18 * 60


def _slot_fit(place: Place, slot: Slot | None) -> float:
    """How well a venue's hours cover the slot it would be placed in."""
    if slot is None:
        return 0.0
    open_m, close_m = opening_window(place)
    win_start, win_end = SLOT_WINDOW[slot]
    overlap = min(close_m, win_end) - max(open_m, win_start)
    window = win_end - win_start
    if overlap <= 0:
        return -25.0  # shut for this entire slot: effectively disqualified
    return (overlap / window - 1.0) * 8.0  # 0 when fully open, negative as it narrows


def _score(
    place: Place,
    prefs: TripPreferences,
    weather: WeatherDay | None,
    recency: dict[str, int],
    pick_index: int,
    day_categories: list[str],
    slot: Slot | None = None,
    prev: Place | None = None,
) -> float:
    score = place.rating * 2.0

    if isinstance(place.category, Interest) and place.category in prefs.interests:
        score += 6.0
    elif not prefs.interests:
        score += 1.5

    # Popularity, dampened so a 300k-review site does not always win.
    score += min(math.log10(max(place.review_count, 10)) / 2, 2.5)

    # Rain pushes the plan indoors.
    if weather and weather.condition in ("rain", "storm", "snow"):
        score += 5.5 if place.indoor else -5.0
    elif weather and weather.temp_max_c >= 32 and place.indoor:
        score += 2.0

    # Budget pressure favours cheaper stops. The traveller's budget is in their
    # currency and catalog costs are USD, so this has to convert before
    # comparing — otherwise every stop looks affordable in JPY and ruinous in
    # KWD purely because of the exchange rate.
    daily_budget = prefs.budget / max(_trip_length(prefs), 1) / max(prefs.travelers, 1)
    cost = places_svc.to_currency(places_svc.base_cost(place), prefs.currency)
    if cost > daily_budget * 0.45:
        score -= 3.0
    elif cost == 0:
        score += 1.0

    score += _slot_fit(place, slot)

    # Keep consecutive stops close together rather than criss-crossing the city.
    if prev is not None:
        km = places_svc.haversine_km(prev.coordinates, place.coordinates)
        score -= min(km * 0.55, 6.0)

    # Variety within a day.
    score -= day_categories.count(str(place.category)) * 3.0

    # A place that has already appeared is always worse than a fresh one, so
    # the catalog is fully spent before anything repeats. Once everything has
    # been used the flat penalty applies to all of them equally and the decay
    # term breaks the tie in favour of the least recently visited.
    if place.id in recency:
        score -= 25.0
        score -= max(0.0, 12.0 - (pick_index - recency[place.id]) * 0.9)

    if prefs.pace == Pace.relaxed and place.walking_intensity >= 4:
        score -= 1.5
    if prefs.pace == Pace.packed and place.walking_intensity >= 4:
        score += 0.5

    return score


def _trip_length(prefs: TripPreferences) -> int:
    return max((prefs.end_date - prefs.start_date).days + 1, 1)


def _pick(
    candidates: list[Place],
    prefs: TripPreferences,
    weather: WeatherDay | None,
    recency: dict[str, int],
    pick_index: int,
    day_categories: list[str],
    slot: Slot | None = None,
    prev: Place | None = None,
    exclude: set[str] | None = None,
    open_at: int | None = None,
) -> Place | None:
    exclude = exclude or set()
    # Never put the same place on the plan twice in one day.
    pool = [p for p in candidates if p.id not in exclude] or list(candidates)

    # Drop anything that would already be shut by the time you got there. If
    # that empties the pool the answer is "nothing is open", not "book
    # somewhere closed" — the caller skips the stop and the day ends earlier.
    if open_at is not None:
        pool = [
            p for p in pool
            if opening_window(p)[1] - max(open_at, opening_window(p)[0]) >= 45
        ]
        if not pool:
            return None

    if slot == Slot.evening:
        preferred = [
            p for p in pool
            if p.category == Interest.nightlife
            or {"evening", "sunset", "late"} & set(p.tags)
        ]
        # Restrict to evening venues only when there are enough of them to
        # choose between. A city with one bar in the catalog would otherwise
        # get that same bar every single night.
        if len(preferred) >= 2:
            pool = preferred
        elif preferred:
            pool = preferred + [p for p in pool if p not in preferred]
    if not pool:
        return None
    return max(
        pool,
        key=lambda p: _score(
            p, prefs, weather, recency, pick_index, day_categories, slot, prev
        ),
    )


def _activity(
    place: Place,
    slot: Slot,
    start_minutes: int,
    prev: Place | None,
    prefs: TripPreferences,
    is_meal: bool = False,
) -> Activity:
    duration = places_svc.base_duration(place)
    travel_minutes, mode = (
        places_svc.travel_estimate(prev, place) if prev else (0, "walk")
    )
    cost = places_svc.activity_cost(place, prefs)

    return Activity(
        slot=slot,
        title=place.name,
        place=place,
        start_time=_fmt(start_minutes),
        end_time=_fmt(start_minutes + duration),
        duration_minutes=duration,
        estimated_cost=cost,
        travel_time_minutes=travel_minutes,
        travel_mode=mode,  # type: ignore[arg-type]
        maps_url=(
            places_svc.directions_url(prev, place, "walking" if mode == "walk" else "transit")
            if prev
            else places_svc.maps_url(place)
        ),
        local_tip=place.description,
        is_meal=is_meal,
    )


def build_day(
    day_number: int,
    day_date: date,
    dest: Destination,
    prefs: TripPreferences,
    weather: WeatherDay | None,
    recency: dict[str, int],
    counter: list[int],
) -> DayPlan:
    """Lay out one day. `recency` maps place id -> the pick index it last
    appeared at; `counter` is a single-element mutable pick counter shared
    across the whole trip so repeats get spaced out rather than blocked."""
    attraction_count, start_minutes, slack = PACE_CONFIG[prefs.pace]
    attractions = dest.attractions
    meals = dest.meals

    day = DayPlan(day_number=day_number, date=day_date)
    day_categories: list[str] = []
    today_ids: set[str] = set()
    clock = start_minutes
    prev: Place | None = None

    def place_activity(
        place: Place, slot: Slot, is_meal: bool = False, floor: int | None = None
    ) -> None:
        nonlocal clock, prev
        act = _activity(place, slot, clock, prev, prefs, is_meal=is_meal)
        arrival = clock + act.travel_time_minutes
        if floor is not None:
            arrival = max(arrival, floor)
        # Never arrive before the doors open.
        opens, closes = opening_window(place)
        arrival = max(arrival, opens)

        # The pick was scored against the clock *before* travel, so the real
        # arrival can be later than the selection assumed. If that leaves less
        # than half an hour, going at all is pointless — skip it and let the
        # day be shorter.
        if closes - arrival < 30:
            return

        clock = arrival
        # If it would close mid-visit, trim the stay rather than overrun.
        if clock + act.duration_minutes > closes:
            act.duration_minutes = closes - clock
        act.start_time = _fmt(clock)
        act.end_time = _fmt(clock + act.duration_minutes)
        clock += act.duration_minutes + slack
        day.activities.append(act)
        counter[0] += 1
        recency[place.id] = counter[0]
        today_ids.add(place.id)
        if not is_meal:
            day_categories.append(str(place.category))
        prev = place

    def choose(pool: list[Place], slot: Slot, floor: int | None = None) -> Place | None:
        arrival = max(clock, floor) if floor is not None else clock
        return _pick(
            pool, prefs, weather, recency, counter[0],
            day_categories if pool is attractions else [],
            slot, prev, today_ids, arrival,
        )

    # --- morning ---------------------------------------------------------
    morning_count = 1 if attraction_count <= 3 else 2
    for _ in range(morning_count):
        place = choose(attractions, Slot.morning)
        if not place:
            break
        place_activity(place, Slot.morning)

    # --- lunch -----------------------------------------------------------
    lunch = choose(meals, Slot.afternoon, floor=12 * 60 + 30)
    if lunch:
        place_activity(lunch, Slot.afternoon, is_meal=True, floor=12 * 60 + 30)

    # --- afternoon -------------------------------------------------------
    afternoon_count = max(1, attraction_count - morning_count - 1)
    for _ in range(afternoon_count):
        if clock > 18 * 60:  # the day has already run long; stop stacking it
            break
        place = choose(attractions, Slot.afternoon)
        if not place:
            break
        place_activity(place, Slot.afternoon)

    # --- evening ---------------------------------------------------------
    if clock <= 20 * 60:
        evening = choose(attractions, Slot.evening, floor=17 * 60 + 30)
        if evening:
            place_activity(evening, Slot.evening, floor=17 * 60 + 30)

    # --- dinner ----------------------------------------------------------
    # Past this the day has already overrun; a 1am dinner helps nobody.
    if clock <= 22 * 60:
        dinner = choose(meals, Slot.evening, floor=19 * 60 + 30)
        if dinner:
            place_activity(dinner, Slot.evening, is_meal=True, floor=19 * 60 + 30)

    day.title = DAY_THEMES[(day_number - 1) % len(DAY_THEMES)]
    day.summary = _day_summary(day, weather)
    day.local_tips = [a.local_tip for a in day.activities if a.local_tip][:3]
    return day.recompute()


def _day_summary(day: DayPlan, weather: WeatherDay | None) -> str:
    stops = [a.title for a in day.activities if not a.is_meal]
    if not stops:
        return "A free day — ask the companion to fill it."
    head = ", ".join(stops[:-1]) + (f" and {stops[-1]}" if len(stops) > 1 else stops[0])
    weather_note = ""
    if weather:
        if weather.condition in ("rain", "storm"):
            weather_note = " Built around indoor stops, given the forecast."
        elif weather.temp_max_c >= 30:
            weather_note = f" It'll hit {weather.temp_max_c:.0f}°C — the midday gap is deliberate."
    return f"{head}.{weather_note}"


def build_budget(trip_days: list[DayPlan], prefs: TripPreferences, dest: Destination) -> BudgetBreakdown:
    # Activity costs are already in the trip's currency; the transport and
    # accommodation models are USD and get converted at the end.
    food = 0.0
    activities = 0.0
    transport_usd = 0.0

    for day in trip_days:
        for act in day.activities:
            if act.is_meal:
                food += act.estimated_cost
            else:
                activities += act.estimated_cost
            # Rough per-leg transport cost by mode, in USD.
            per_person = {"walk": 0.0, "transit": 2.2, "taxi": 9.0}[act.travel_mode]
            transport_usd += per_person * prefs.travelers * dest.cost_index

    nights = max((prefs.end_date - prefs.start_date).days, 1)
    rooms = math.ceil(prefs.travelers / 2)
    nightly_usd = 105 * dest.cost_index
    accommodation_usd = nights * rooms * nightly_usd

    return BudgetBreakdown(
        accommodation=places_svc.to_currency(accommodation_usd, prefs.currency),
        food=round(food, 2),
        transport=places_svc.to_currency(transport_usd, prefs.currency),
        activities=round(activities, 2),
    )


def generate(prefs: TripPreferences) -> tuple[list[DayPlan], BudgetBreakdown, Destination, list[WeatherDay]]:
    from .weather import forecast as get_forecast

    dest = places_svc.resolve(prefs.destination)
    length = _trip_length(prefs)
    weather = get_forecast(dest, prefs.start_date, length)

    recency: dict[str, int] = {}
    counter = [0]
    days: list[DayPlan] = []
    for i in range(length):
        day_date = prefs.start_date + timedelta(days=i)
        day_weather = next((w for w in weather if w.date == day_date), None)
        days.append(
            build_day(i + 1, day_date, dest, prefs, day_weather, recency, counter)
        )

    budget = build_budget(days, prefs, dest)
    return days, budget, dest, weather


def trip_title(prefs: TripPreferences, dest: Destination) -> str:
    length = _trip_length(prefs)
    nights = max(length - 1, 1)
    return f"{nights} nights in {dest.name}"

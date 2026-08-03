"""Domain models shared by every service and mirrored in frontend/lib/types.ts."""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

# A field named `date` shadows the `date` type inside its own class namespace,
# so annotations for those fields use this alias instead.
DateT = date


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


# --------------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------------


class Interest(str, Enum):
    food = "food"
    adventure = "adventure"
    history = "history"
    shopping = "shopping"
    nature = "nature"
    nightlife = "nightlife"


class Pace(str, Enum):
    relaxed = "relaxed"
    balanced = "balanced"
    packed = "packed"


class Slot(str, Enum):
    morning = "morning"
    afternoon = "afternoon"
    evening = "evening"


class ExpenseCategory(str, Enum):
    food = "food"
    transport = "transport"
    shopping = "shopping"
    hotels = "hotels"
    activities = "activities"


class Mood(str, Enum):
    delighted = "delighted"
    happy = "happy"
    calm = "calm"
    tired = "tired"
    stressed = "stressed"


# --------------------------------------------------------------------------
# Places & itinerary
# --------------------------------------------------------------------------


class Coordinates(BaseModel):
    lat: float
    lng: float


class Place(BaseModel):
    id: str
    name: str
    category: Interest | Literal["meal", "rest", "transit"]
    description: str = ""
    coordinates: Coordinates
    rating: float = 4.4
    review_count: int = 0
    price_level: int = Field(2, ge=0, le=4)
    indoor: bool = False
    walking_intensity: int = Field(2, ge=1, le=5)
    opening_hours: str = "09:00 - 18:00"
    photo: str = ""
    tags: list[str] = Field(default_factory=list)
    address: str = ""

    @property
    def maps_url(self) -> str:
        q = self.name.replace(" ", "+")
        return (
            "https://www.google.com/maps/search/?api=1&query="
            f"{q}&query_place_id={self.id}"
        )


class Activity(BaseModel):
    id: str = Field(default_factory=lambda: _id("act"))
    slot: Slot
    title: str
    place: Place
    start_time: str = "09:00"
    end_time: str = "11:00"
    duration_minutes: int = 120
    estimated_cost: float = 0.0
    travel_time_minutes: int = 15
    travel_mode: Literal["walk", "transit", "taxi"] = "walk"
    maps_url: str = ""
    local_tip: str = ""
    is_meal: bool = False
    locked: bool = False
    # Provenance so the UI can highlight what the companion touched.
    origin: Literal["planned", "companion", "proactive"] = "planned"
    note: str | None = None


class DayPlan(BaseModel):
    id: str = Field(default_factory=lambda: _id("day"))
    day_number: int
    date: DateT
    title: str = ""
    summary: str = ""
    activities: list[Activity] = Field(default_factory=list)
    estimated_cost: float = 0.0
    total_travel_minutes: int = 0
    local_tips: list[str] = Field(default_factory=list)

    def recompute(self) -> "DayPlan":
        order = {Slot.morning: 0, Slot.afternoon: 1, Slot.evening: 2}
        self.activities.sort(key=lambda a: (order[a.slot], a.start_time))
        self.estimated_cost = round(sum(a.estimated_cost for a in self.activities), 2)
        self.total_travel_minutes = sum(a.travel_time_minutes for a in self.activities)
        return self


class BudgetBreakdown(BaseModel):
    accommodation: float = 0.0
    food: float = 0.0
    transport: float = 0.0
    activities: float = 0.0

    @property
    def total(self) -> float:
        return round(
            self.accommodation + self.food + self.transport + self.activities, 2
        )


class WeatherDay(BaseModel):
    date: DateT
    condition: Literal["clear", "clouds", "rain", "storm", "snow", "fog"]
    description: str
    temp_min_c: float
    temp_max_c: float
    precipitation_chance: int = Field(0, ge=0, le=100)
    wind_kph: float = 0.0
    humidity: int = 50
    sunrise: str = "06:15"
    sunset: str = "18:45"
    # Hour (0-23) at which the headline condition starts, used by the
    # proactive engine to write "from 2 PM"-style alerts.
    onset_hour: int | None = None


class WeatherAlert(BaseModel):
    id: str = Field(default_factory=lambda: _id("wal"))
    date: DateT
    severity: Literal["info", "warning", "severe"]
    title: str
    message: str
    recommend_indoor: bool = False


class PackingItem(BaseModel):
    id: str = Field(default_factory=lambda: _id("pack"))
    label: str
    category: Literal[
        "essentials", "clothing", "weather", "electronics", "health", "activity"
    ]
    reason: str = ""
    packed: bool = False
    essential: bool = False


class Expense(BaseModel):
    id: str = Field(default_factory=lambda: _id("exp"))
    label: str
    amount: float
    category: ExpenseCategory
    date: DateT
    created_at: str = Field(default_factory=_now)
    note: str | None = None


class JournalEntry(BaseModel):
    id: str = Field(default_factory=lambda: _id("jrn"))
    day_number: int
    date: DateT
    title: str
    summary: str
    places_visited: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    spend: float = 0.0
    mood: Mood = Mood.happy
    photo: str = ""
    created_at: str = Field(default_factory=_now)


class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: _id("msg"))
    role: Literal["user", "companion"]
    content: str
    created_at: str = Field(default_factory=_now)
    # Human-readable list of itinerary changes attached to this message.
    changes: list["ItineraryChange"] = Field(default_factory=list)
    intent: str | None = None


class ItineraryChange(BaseModel):
    id: str = Field(default_factory=lambda: _id("chg"))
    kind: Literal[
        "replaced", "moved", "removed", "added", "reordered", "downgraded", "noted"
    ]
    day_number: int
    summary: str
    before: str | None = None
    after: str | None = None
    # Machine-readable form, so an auto-applied change can be undone.
    before_place_id: str | None = None
    after_place_id: str | None = None
    activity_id: str | None = None
    to_day_number: int | None = None


class ProactiveAlert(BaseModel):
    id: str = Field(default_factory=lambda: _id("pro"))
    trigger: Literal["weather", "budget", "pace", "closing", "arrival"]
    # Stable identity for "have I already raised this?". Set by the scanner
    # that produced the alert, so both sides of the check agree.
    dedupe_key: str = ""
    severity: Literal["info", "warning", "severe"] = "info"
    title: str
    message: str
    day_number: int | None = None
    changes: list[ItineraryChange] = Field(default_factory=list)
    applied: bool = False
    dismissed: bool = False
    created_at: str = Field(default_factory=_now)


# --------------------------------------------------------------------------
# Trip aggregate
# --------------------------------------------------------------------------


class TripPreferences(BaseModel):
    destination: str
    start_date: date
    end_date: date
    budget: float
    currency: str = "USD"
    travelers: int = Field(2, ge=1, le=20)
    interests: list[Interest] = Field(default_factory=list)
    pace: Pace = Pace.balanced


class TripCreate(TripPreferences):
    pass


class Trip(BaseModel):
    id: str = Field(default_factory=lambda: _id("trip"))
    owner: str = "demo-user"
    title: str = ""
    preferences: TripPreferences
    center: Coordinates
    timezone: str = "UTC"
    country: str = ""
    language: str = "English"
    days: list[DayPlan] = Field(default_factory=list)
    budget_breakdown: BudgetBreakdown = Field(default_factory=BudgetBreakdown)
    weather: list[WeatherDay] = Field(default_factory=list)
    weather_alerts: list[WeatherAlert] = Field(default_factory=list)
    packing_list: list[PackingItem] = Field(default_factory=list)
    expenses: list[Expense] = Field(default_factory=list)
    journal: list[JournalEntry] = Field(default_factory=list)
    messages: list[ChatMessage] = Field(default_factory=list)
    alerts: list[ProactiveAlert] = Field(default_factory=list)
    share_token: str = Field(default_factory=lambda: uuid4().hex[:10])
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)

    # -- derived helpers ---------------------------------------------------
    @property
    def duration_days(self) -> int:
        return len(self.days)

    def day(self, number: int) -> DayPlan | None:
        return next((d for d in self.days if d.day_number == number), None)

    def total_spent(self) -> float:
        return round(sum(e.amount for e in self.expenses), 2)

    def remaining_budget(self) -> float:
        return round(self.preferences.budget - self.total_spent(), 2)

    def touch(self) -> None:
        self.updated_at = _now()


class TripSummary(BaseModel):
    id: str
    title: str
    destination: str
    start_date: date
    end_date: date
    travelers: int
    budget: float
    spent: float
    cover: str = ""
    updated_at: str


# --------------------------------------------------------------------------
# Request / response payloads
# --------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str
    day_number: int | None = None


class ChatResponse(BaseModel):
    message: ChatMessage
    trip: Trip


class ExpenseCreate(BaseModel):
    label: str
    amount: float = Field(gt=0)
    category: ExpenseCategory
    date: DateT | None = None
    note: str | None = None


class ExpenseStats(BaseModel):
    budget: float
    spent: float
    remaining: float
    by_category: dict[str, float]
    by_day: list[dict[str, Any]]
    daily_average: float
    projected_total: float
    over_budget: bool


class PackingToggle(BaseModel):
    packed: bool


class JournalRequest(BaseModel):
    day_number: int
    mood: Mood | None = None
    note: str | None = None


class ApplyAlertResponse(BaseModel):
    alert: ProactiveAlert
    trip: Trip


class Phrase(BaseModel):
    english: str
    local: str
    pronunciation: str


class EmergencyContact(BaseModel):
    label: str
    number: str
    note: str = ""


class LocalInfo(BaseModel):
    country: str
    language: str
    currency: str
    currency_rate_from_usd: float
    timezone: str
    utc_offset_hours: float
    phrases: list[Phrase]
    emergency: list[EmergencyContact]
    plug_type: str = ""
    tipping: str = ""


ChatMessage.model_rebuild()

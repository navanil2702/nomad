"""Seed data.

Creates one in-progress demo trip on first boot so the app is immediately
useful: day 2 of 5 in Tokyo, two days of real expenses already logged, and
journal entries written for the days that have finished.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from .models.schemas import (
    Expense,
    ExpenseCategory,
    Interest,
    Pace,
    TripCreate,
)
from .services import journal as journal_svc, trips as trips_svc
from .store import get_store

log = logging.getLogger(__name__)

DEMO_EXPENSES: list[tuple[int, str, float, ExpenseCategory]] = [
    (0, "Ryokan, 2 nights", 268.00, ExpenseCategory.hotels),
    (0, "Suica cards + top up", 42.00, ExpenseCategory.transport),
    (0, "Tsukiji breakfast", 24.50, ExpenseCategory.food),
    (0, "Sensō-ji omamori", 12.00, ExpenseCategory.shopping),
    (0, "Ichiran ramen", 22.00, ExpenseCategory.food),
    (1, "Shibuya Sky tickets", 34.00, ExpenseCategory.activities),
    (1, "Convenience store lunch", 11.20, ExpenseCategory.food),
    (1, "Metro day pass", 16.00, ExpenseCategory.transport),
    (1, "Yakitori dinner, Omoide Yokocho", 48.00, ExpenseCategory.food),
    (1, "Golden Gai drinks", 39.00, ExpenseCategory.food),
]


def seed_if_empty() -> bool:
    """Create the demo trip if the store is empty. Returns whether it did."""
    from .core.config import get_settings

    if not get_settings().seed_demo_trip:
        return False

    store = get_store()
    try:
        if store.list():
            return False
    except Exception as exc:
        log.warning("Could not read store, skipping seed: %s", exc)
        return False

    today = date.today()
    start = today - timedelta(days=1)

    trip = trips_svc.create_trip(
        TripCreate(
            destination="Tokyo, Japan",
            start_date=start,
            end_date=start + timedelta(days=4),
            budget=2600,
            currency="USD",
            travelers=2,
            interests=[
                Interest.food,
                Interest.history,
                Interest.nature,
                Interest.nightlife,
            ],
            pace=Pace.balanced,
        )
    )
    trip.owner = "demo-user"

    for offset, label, amount, category in DEMO_EXPENSES:
        trip.expenses.append(
            Expense(
                label=label,
                amount=amount,
                category=category,
                date=start + timedelta(days=offset),
            )
        )

    journal_svc.ensure_entries_up_to(trip, today - timedelta(days=1))

    store.save(trip)
    log.info("Seeded demo trip %s (%s)", trip.id, trip.title)
    return True

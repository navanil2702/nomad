"""Expense tracking and budget analytics."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException

from ..models.schemas import Expense, ExpenseCreate, ExpenseStats, Trip
from ..services import trips as trips_svc
from ..store import get_store

router = APIRouter(prefix="/api/trips/{trip_id}/expenses", tags=["expenses"])


def _load(trip_id: str) -> Trip:
    trip = get_store().get(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.get("", response_model=list[Expense])
def list_expenses(trip_id: str) -> list[Expense]:
    return _load(trip_id).expenses


@router.post("", response_model=Trip, status_code=201)
def add_expense(trip_id: str, payload: ExpenseCreate) -> Trip:
    trip = _load(trip_id)
    when = payload.date or _default_date(trip)
    trips_svc.add_expense(
        trip,
        Expense(
            label=payload.label.strip() or payload.category.value.title(),
            amount=round(payload.amount, 2),
            category=payload.category,
            date=when,
            note=payload.note,
        ),
    )

    # An overspend is exactly the moment the companion should speak up.
    from ..services import proactive

    proactive.scan(trip)
    return get_store().save(trip)


@router.delete("/{expense_id}", response_model=Trip)
def delete_expense(trip_id: str, expense_id: str) -> Trip:
    trip = _load(trip_id)
    before = len(trip.expenses)
    trip.expenses = [e for e in trip.expenses if e.id != expense_id]
    if len(trip.expenses) == before:
        raise HTTPException(status_code=404, detail="Expense not found")
    return get_store().save(trip)


@router.get("/stats", response_model=ExpenseStats)
def stats(trip_id: str) -> ExpenseStats:
    return trips_svc.expense_stats(_load(trip_id))


def _default_date(trip: Trip) -> date:
    today = date.today()
    if trip.preferences.start_date <= today <= trip.preferences.end_date:
        return today
    return trip.preferences.start_date

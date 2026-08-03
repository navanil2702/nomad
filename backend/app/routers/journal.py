"""Memory journal: auto-written daily entries and the trip retrospective."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException

from ..models.schemas import JournalEntry, JournalRequest, Trip
from ..services import journal as journal_svc
from ..store import get_store

router = APIRouter(prefix="/api/trips/{trip_id}/journal", tags=["journal"])


def _load(trip_id: str) -> Trip:
    trip = get_store().get(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.get("", response_model=list[JournalEntry])
def list_entries(trip_id: str) -> list[JournalEntry]:
    return _load(trip_id).journal


@router.post("/autowrite", response_model=Trip)
def autowrite(trip_id: str, through: date | None = None) -> Trip:
    """Write entries for every day that has finished. Idempotent."""
    trip = _load(trip_id)
    journal_svc.ensure_entries_up_to(trip, through or date.today())
    return get_store().save(trip)


@router.post("/day", response_model=Trip)
def write_day(trip_id: str, payload: JournalRequest) -> Trip:
    trip = _load(trip_id)
    day = trip.day(payload.day_number)
    if not day:
        raise HTTPException(status_code=404, detail="Day not found")

    entry = journal_svc.build_entry(trip, day, payload.mood, payload.note)
    trip.journal = [e for e in trip.journal if e.day_number != payload.day_number]
    trip.journal.append(entry)
    trip.journal.sort(key=lambda e: e.day_number)
    return get_store().save(trip)


@router.delete("/{entry_id}", response_model=Trip)
def delete_entry(trip_id: str, entry_id: str) -> Trip:
    trip = _load(trip_id)
    trip.journal = [e for e in trip.journal if e.id != entry_id]
    return get_store().save(trip)


@router.get("/retrospective")
def retrospective(trip_id: str) -> dict:
    """The finished travel journal, generated from every day's entry."""
    trip = _load(trip_id)
    journal_svc.ensure_entries_up_to(trip, date.today())
    get_store().save(trip)
    return journal_svc.trip_retrospective(trip)

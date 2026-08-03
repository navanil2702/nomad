"""Trip persistence.

Backed by one JSON file per trip so the app has zero infrastructure
requirements. `SupabaseStore` implements the same interface and takes over
automatically when SUPABASE_URL / SUPABASE_SERVICE_KEY are present.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Protocol

from .core.config import get_settings
from .models.schemas import Trip, TripSummary


class TripStore(Protocol):
    def list(self) -> list[TripSummary]: ...
    def get(self, trip_id: str) -> Trip | None: ...
    def get_by_share_token(self, token: str) -> Trip | None: ...
    def save(self, trip: Trip) -> Trip: ...
    def delete(self, trip_id: str) -> bool: ...


class JsonFileStore:
    """Thread-safe JSON store. Reads are served from an in-memory cache."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._cache: dict[str, Trip] = {}
        self._load_all()

    def _path(self, trip_id: str) -> Path:
        return self._root / f"{trip_id}.json"

    def _load_all(self) -> None:
        for path in self._root.glob("trip_*.json"):
            try:
                self._cache[path.stem] = Trip.model_validate_json(
                    path.read_text(encoding="utf-8")
                )
            except Exception:  # corrupt file: skip rather than crash boot
                continue

    def list(self) -> list[TripSummary]:
        with self._lock:
            trips = sorted(
                self._cache.values(), key=lambda t: t.updated_at, reverse=True
            )
            return [
                TripSummary(
                    id=t.id,
                    title=t.title,
                    destination=t.preferences.destination,
                    start_date=t.preferences.start_date,
                    end_date=t.preferences.end_date,
                    travelers=t.preferences.travelers,
                    budget=t.preferences.budget,
                    spent=t.total_spent(),
                    cover=t.id,
                    updated_at=t.updated_at,
                )
                for t in trips
            ]

    def get(self, trip_id: str) -> Trip | None:
        with self._lock:
            return self._cache.get(trip_id)

    def get_by_share_token(self, token: str) -> Trip | None:
        with self._lock:
            return next(
                (t for t in self._cache.values() if t.share_token == token), None
            )

    def save(self, trip: Trip) -> Trip:
        with self._lock:
            trip.touch()
            self._cache[trip.id] = trip
            self._path(trip.id).write_text(
                json.dumps(json.loads(trip.model_dump_json()), indent=2),
                encoding="utf-8",
            )
            return trip

    def delete(self, trip_id: str) -> bool:
        with self._lock:
            existed = self._cache.pop(trip_id, None) is not None
            path = self._path(trip_id)
            if path.exists():
                path.unlink()
            return existed


class SupabaseStore:
    """Postgres-backed store via the Supabase REST API.

    Expects a `trips` table with columns: id (text, pk), owner (text),
    share_token (text), updated_at (text), payload (jsonb).
    """

    def __init__(self, url: str, service_key: str) -> None:
        import httpx

        self._client = httpx.Client(
            base_url=f"{url.rstrip('/')}/rest/v1",
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates",
            },
            timeout=15.0,
        )

    def _rows(self, params: dict) -> list[dict]:
        r = self._client.get("/trips", params=params)
        r.raise_for_status()
        return r.json()

    def list(self) -> list[TripSummary]:
        rows = self._rows({"select": "payload", "order": "updated_at.desc"})
        out: list[TripSummary] = []
        for row in rows:
            t = Trip.model_validate(row["payload"])
            out.append(
                TripSummary(
                    id=t.id,
                    title=t.title,
                    destination=t.preferences.destination,
                    start_date=t.preferences.start_date,
                    end_date=t.preferences.end_date,
                    travelers=t.preferences.travelers,
                    budget=t.preferences.budget,
                    spent=t.total_spent(),
                    cover=t.id,
                    updated_at=t.updated_at,
                )
            )
        return out

    def get(self, trip_id: str) -> Trip | None:
        rows = self._rows({"select": "payload", "id": f"eq.{trip_id}", "limit": "1"})
        return Trip.model_validate(rows[0]["payload"]) if rows else None

    def get_by_share_token(self, token: str) -> Trip | None:
        rows = self._rows(
            {"select": "payload", "share_token": f"eq.{token}", "limit": "1"}
        )
        return Trip.model_validate(rows[0]["payload"]) if rows else None

    def save(self, trip: Trip) -> Trip:
        trip.touch()
        payload = json.loads(trip.model_dump_json())
        # PostgREST only upserts when told which column identifies a conflict.
        # Without on_conflict this is a plain insert and the second save of a
        # trip fails on the primary key.
        r = self._client.post(
            "/trips",
            params={"on_conflict": "id"},
            json={
                "id": trip.id,
                "owner": trip.owner,
                "share_token": trip.share_token,
                "updated_at": trip.updated_at,
                "payload": payload,
            },
        )
        r.raise_for_status()
        return trip

    def delete(self, trip_id: str) -> bool:
        r = self._client.delete(
            "/trips",
            params={"id": f"eq.{trip_id}"},
            headers={"Prefer": "return=representation"},
        )
        r.raise_for_status()
        # PostgREST returns the deleted rows, so an empty list means "not found"
        # rather than "deleted nothing successfully".
        try:
            return bool(r.json())
        except ValueError:
            return False


_store: TripStore | None = None


def get_store() -> TripStore:
    global _store
    if _store is None:
        settings = get_settings()
        if settings.supabase_url and settings.supabase_service_key:
            _store = SupabaseStore(
                settings.supabase_url, settings.supabase_service_key
            )
        else:
            _store = JsonFileStore(settings.data_dir / "trips")
    return _store

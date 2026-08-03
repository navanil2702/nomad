"""Trip CRUD, itinerary, map, weather, packing, local info and sharing."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException

from ..core.config import get_settings
from ..models.schemas import (
    LocalInfo,
    PackingToggle,
    Trip,
    TripCreate,
    TripSummary,
)
from ..services import packing as packing_svc, places as places_svc, trips as trips_svc
from ..store import get_store

router = APIRouter(prefix="/api/trips", tags=["trips"])


def _load(trip_id: str) -> Trip:
    trip = get_store().get(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.get("", response_model=list[TripSummary])
def list_trips() -> list[TripSummary]:
    return get_store().list()


@router.post("", response_model=Trip, status_code=201)
def create_trip(payload: TripCreate) -> Trip:
    trip = trips_svc.create_trip(payload)
    return get_store().save(trip)


@router.get("/{trip_id}", response_model=Trip)
def get_trip(trip_id: str) -> Trip:
    return _load(trip_id)


@router.delete("/{trip_id}")
def delete_trip(trip_id: str) -> dict:
    if not get_store().delete(trip_id):
        raise HTTPException(status_code=404, detail="Trip not found")
    return {"deleted": trip_id}


@router.post("/{trip_id}/regenerate", response_model=Trip)
def regenerate(trip_id: str) -> Trip:
    """Rebuild the itinerary from the same preferences, keeping expenses."""
    old = _load(trip_id)
    fresh = trips_svc.create_trip(TripCreate(**old.preferences.model_dump()))
    fresh.id = old.id
    fresh.share_token = old.share_token
    fresh.expenses = old.expenses
    fresh.created_at = old.created_at
    return get_store().save(fresh)


# --- itinerary sub-resources ---------------------------------------------


@router.get("/{trip_id}/map")
def get_map(trip_id: str) -> dict:
    trip = _load(trip_id)
    return {
        "center": trip.center.model_dump(),
        "google_maps_key_present": get_settings().live_maps,
        "markers": trips_svc.map_places(trip),
    }


@router.get("/{trip_id}/places/{place_id}/nearby")
def get_nearby(trip_id: str, place_id: str, limit: int = 5) -> list[dict]:
    return trips_svc.nearby(_load(trip_id), place_id, limit)


@router.get("/{trip_id}/weather")
def get_weather(trip_id: str) -> dict[str, list]:
    trip = _load(trip_id)
    return {"forecast": trip.weather, "alerts": trip.weather_alerts}


@router.post("/{trip_id}/weather/refresh", response_model=Trip)
def refresh_weather(trip_id: str) -> Trip:
    from ..services import proactive, weather as weather_svc

    trip = _load(trip_id)
    dest = places_svc.resolve(trip.preferences.destination)
    trip.weather = weather_svc.forecast(
        dest, trip.preferences.start_date, len(trip.days)
    )
    trip.weather_alerts = weather_svc.build_alerts(trip.weather)
    proactive.scan(trip)
    return get_store().save(trip)


@router.get("/{trip_id}/packing")
def get_packing(trip_id: str) -> list:
    return _load(trip_id).packing_list


@router.patch("/{trip_id}/packing/{item_id}", response_model=Trip)
def toggle_packing(trip_id: str, item_id: str, payload: PackingToggle) -> Trip:
    trip = _load(trip_id)
    item = next((i for i in trip.packing_list if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Packing item not found")
    item.packed = payload.packed
    return get_store().save(trip)


@router.post("/{trip_id}/packing/regenerate", response_model=Trip)
def regenerate_packing(trip_id: str) -> Trip:
    trip = _load(trip_id)
    dest = places_svc.resolve(trip.preferences.destination)
    packed = {i.label for i in trip.packing_list if i.packed}
    trip.packing_list = packing_svc.generate(
        trip.preferences, dest, trip.days, trip.weather
    )
    for item in trip.packing_list:
        item.packed = item.label in packed
    return get_store().save(trip)


@router.get("/{trip_id}/local", response_model=LocalInfo)
def get_local_info(trip_id: str) -> LocalInfo:
    return trips_svc.local_info(_load(trip_id))


@router.get("/{trip_id}/share")
def get_share_link(trip_id: str) -> dict:
    trip = _load(trip_id)
    return {"token": trip.share_token, "path": f"/shared/{trip.share_token}"}


# --- offline bundle -------------------------------------------------------


@router.get("/{trip_id}/offline")
def offline_bundle(trip_id: str) -> dict:
    """Everything needed to run the itinerary with no connection."""
    trip = _load(trip_id)
    info = trips_svc.local_info(trip)
    return {
        "generated_at": date.today().isoformat(),
        "trip": {
            "title": trip.title,
            "destination": trip.preferences.destination,
            "dates": f"{trip.preferences.start_date} → {trip.preferences.end_date}",
            "travelers": trip.preferences.travelers,
        },
        "days": [
            {
                "day": d.day_number,
                "date": d.date.isoformat(),
                "title": d.title,
                "stops": [
                    {
                        "time": a.start_time,
                        "name": a.place.name,
                        "address": a.place.address,
                        "hours": a.place.opening_hours,
                        "coordinates": a.place.coordinates.model_dump(),
                        "maps_url": places_svc.maps_url(a.place),
                        "tip": a.local_tip,
                        "cost": a.estimated_cost,
                    }
                    for a in d.activities
                ],
            }
            for d in trip.days
        ],
        "emergency": [e.model_dump() for e in info.emergency],
        "phrases": [p.model_dump() for p in info.phrases],
        "packing": [i.label for i in trip.packing_list if not i.packed],
    }

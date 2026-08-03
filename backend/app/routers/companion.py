"""Chat with the companion, and the proactive alert lifecycle."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models.schemas import (
    ApplyAlertResponse,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ProactiveAlert,
    Trip,
)
from ..services import companion as companion_svc, proactive
from ..store import get_store

router = APIRouter(prefix="/api/trips/{trip_id}", tags=["companion"])

QUICK_PROMPTS = [
    "It's raining",
    "I'm tired",
    "I'm hungry",
    "My train is delayed",
    "I have two free hours",
    "I want vegetarian food nearby",
    "I spent more than expected",
]


def _load(trip_id: str) -> Trip:
    trip = get_store().get(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip


@router.get("/chat", response_model=list[ChatMessage])
def history(trip_id: str) -> list[ChatMessage]:
    return _load(trip_id).messages


@router.get("/chat/prompts")
def prompts(trip_id: str) -> list[str]:
    return QUICK_PROMPTS


@router.post("/chat", response_model=ChatResponse)
def chat(trip_id: str, payload: ChatRequest) -> ChatResponse:
    if not payload.message.strip():
        raise HTTPException(status_code=422, detail="Message cannot be empty")

    trip = _load(trip_id)
    trip.messages.append(ChatMessage(role="user", content=payload.message.strip()))

    reply, changes, intent = companion_svc.respond(
        trip, payload.message.strip(), payload.day_number
    )
    message = ChatMessage(
        role="companion", content=reply, changes=changes, intent=intent
    )
    trip.messages.append(message)

    get_store().save(trip)
    return ChatResponse(message=message, trip=trip)


@router.delete("/chat", response_model=Trip)
def clear_chat(trip_id: str) -> Trip:
    trip = _load(trip_id)
    trip.messages = []
    return get_store().save(trip)


# --- proactive alerts -----------------------------------------------------


@router.get("/alerts", response_model=list[ProactiveAlert])
def list_alerts(trip_id: str) -> list[ProactiveAlert]:
    return [a for a in _load(trip_id).alerts if not a.dismissed]


@router.post("/alerts/scan")
def scan_alerts(trip_id: str) -> dict:
    """Run the proactive engine. Returns only what is new since last scan."""
    trip = _load(trip_id)
    new_alerts = proactive.scan(trip)
    get_store().save(trip)
    return {"new": new_alerts, "trip": trip}


@router.post("/alerts/{alert_id}/apply", response_model=ApplyAlertResponse)
def apply_alert(trip_id: str, alert_id: str) -> ApplyAlertResponse:
    trip = _load(trip_id)
    alert = next((a for a in trip.alerts if a.id == alert_id), None)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    proactive.apply(trip, alert)
    get_store().save(trip)
    return ApplyAlertResponse(alert=alert, trip=trip)


@router.post("/alerts/{alert_id}/undo", response_model=ApplyAlertResponse)
def undo_alert(trip_id: str, alert_id: str) -> ApplyAlertResponse:
    trip = _load(trip_id)
    alert = next((a for a in trip.alerts if a.id == alert_id), None)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    proactive.undo(trip, alert)
    get_store().save(trip)
    return ApplyAlertResponse(alert=alert, trip=trip)


@router.post("/alerts/{alert_id}/dismiss", response_model=ApplyAlertResponse)
def dismiss_alert(trip_id: str, alert_id: str) -> ApplyAlertResponse:
    trip = _load(trip_id)
    alert = next((a for a in trip.alerts if a.id == alert_id), None)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.dismissed = True
    get_store().save(trip)
    return ApplyAlertResponse(alert=alert, trip=trip)

"""Place photos and provider status."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from ..core.config import get_settings
from ..services import google_places, providers

router = APIRouter(prefix="/api", tags=["places"])

# Photo URIs Google hands back are already signed and time-limited, so the
# lookup is worth caching but not for long.
_PHOTO_CACHE = providers.TTLCache(ttl_seconds=45 * 60, maxsize=512)


@router.get("/places/photo")
def place_photo(
    name: str = Query(..., description="Places photo resource name"),
    w: int = Query(900, ge=80, le=1600),
):
    """Redirect to a Google Places photo.

    The browser never sees the API key: this resolves the photo resource to a
    signed, key-less URL server-side and 302s to it. That is the whole reason
    this endpoint exists rather than the frontend building a media URL itself.
    """
    if not get_settings().google_maps_api_key:
        raise HTTPException(status_code=404, detail="No Places provider configured")

    # `name` comes from a Places response and is echoed into an upstream URL,
    # so constrain it to the shape Google actually uses.
    if not name.startswith("places/") or any(c in name for c in "?&#"):
        raise HTTPException(status_code=400, detail="Invalid photo reference")

    cache_key = f"{name}:{w}"
    uri = _PHOTO_CACHE.get(cache_key)
    if uri is None:
        uri = google_places.photo_uri(name, max_width=w)
        if not uri:
            raise HTTPException(status_code=502, detail="Could not resolve photo")
        _PHOTO_CACHE.set(cache_key, uri)

    return RedirectResponse(uri, status_code=307)


@router.post("/providers/check")
def provider_check() -> dict:
    """Actually call each configured provider and report what came back.

    /api/providers only reports what *this* process has observed, and on
    serverless the instance answering a status query is rarely the one that
    built your trip — so a real failure shows up there as "no calls yet". This
    exercises the providers in-process, which is the only way to get a
    trustworthy answer out of a deployment.
    """
    from ..services import google_places, llm

    settings = get_settings()
    results: dict[str, dict] = {}

    # --- LLM --------------------------------------------------------------
    if settings.live_ai:
        before = providers.registry.state("ai").last_error
        reply = llm.complete_json(
            '{"task": "Reply with JSON {\\"ok\\": true} and nothing else."}',
            system="You reply with JSON only.",
            max_tokens=32,
        )
        state = providers.registry.state("ai")
        results["ai"] = {
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "ok": reply is not None,
            "reply": reply,
            "error": None if reply is not None else (state.last_error or before),
        }
    else:
        results["ai"] = {"ok": False, "error": "no GROQ_API_KEY or OPENAI_API_KEY set"}

    # --- Places -----------------------------------------------------------
    if settings.google_maps_api_key:
        try:
            suggestions = google_places.autocomplete_cities("lisb", 3)
            results["places"] = {
                "ok": bool(suggestions),
                "sample": [s["label"] for s in (suggestions or [])],
                "error": None if suggestions else "no suggestions returned",
            }
        except Exception as exc:
            results["places"] = {"ok": False, "error": providers.describe(exc)}
    else:
        results["places"] = {"ok": False, "error": "no GOOGLE_MAPS_API_KEY set"}

    # --- Weather ----------------------------------------------------------
    if settings.openweather_api_key:
        from ..models.schemas import Coordinates
        from ..services import weather as weather_svc
        from datetime import date

        try:
            forecast = weather_svc._live_forecast(
                Coordinates(lat=51.5072, lng=-0.1276),
                date.today(),
                1,
                settings.openweather_api_key,
            )
            results["weather"] = {
                "ok": bool(forecast),
                "error": None if forecast else "no forecast returned",
            }
        except Exception as exc:
            results["weather"] = {"ok": False, "error": providers.describe(exc)}
    else:
        results["weather"] = {"ok": False, "error": "no OPENWEATHER_API_KEY set"}

    return {"checked_in_process": True, "results": results}


@router.get("/providers")
def provider_status() -> dict:
    """Which providers are live right now, and why any of them are not.

    A fallback that is invisible is a lie, so this is the source of truth for
    the badge in the UI.
    """
    settings = get_settings()
    configured = {
        "ai": settings.live_ai,
        "weather": bool(settings.openweather_api_key),
        "places": bool(settings.google_maps_api_key),
        "database": bool(settings.supabase_url),
    }
    observed = providers.registry.snapshot()

    def mode(name: str) -> str:
        if not configured.get(name):
            return "offline"
        seen = observed.get(name, {}).get("mode")
        # Configured but not yet exercised. Claiming "live" here would be an
        # assertion we have no evidence for — the point of this endpoint is
        # that it only reports what actually happened.
        return seen if seen in ("live", "fallback") else "ready"

    def entry(name: str, fallback: str, **extra) -> dict:
        # Observed state first, then the computed fields — spreading it last
        # would let a stale "disabled" overwrite the configured/offline answer.
        return {
            **observed.get(name, {}),
            "configured": configured.get(name, False),
            "mode": mode(name),
            "fallback": fallback,
            **extra,
        }

    return {
        "providers": {
            "ai": entry(
                "ai",
                "template phrasing; itinerary decisions are unaffected",
                model=(
                    f"{settings.llm_provider}:{settings.llm_model}"
                    if configured["ai"]
                    else None
                ),
            ),
            "weather": entry("weather", "seeded climate model"),
            "places": entry(
                "places", "curated catalog for 6 cities, generated elsewhere"
            ),
            "database": {
                "configured": configured["database"],
                "mode": "live" if configured["database"] else "offline",
                "fallback": "JSON files on local disk",
            },
        }
    }

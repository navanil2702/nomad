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


@router.get("/providers")
def provider_status() -> dict:
    """Which providers are live right now, and why any of them are not.

    A fallback that is invisible is a lie, so this is the source of truth for
    the badge in the UI.
    """
    settings = get_settings()
    configured = {
        "ai": bool(settings.openai_api_key),
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
                model=settings.openai_model if configured["ai"] else None,
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

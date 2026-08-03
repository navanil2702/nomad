"""Provider state and caching.

Every external provider is tried first and falls back to an offline engine.
That is only trustworthy if two things are true:

  1. A fallback is *visible*. Silently degrading to mock data while the UI
     claims to be live is worse than failing loudly, so every fallback is
     recorded here with its reason and surfaced at /api/providers.
  2. A fallback is *cheap*. Retrying a dead API on every request turns one
     outage into a latency problem, so failures are cached too.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

log = logging.getLogger(__name__)

ProviderName = Literal["ai", "weather", "places", "timezone"]
Mode = Literal["live", "fallback", "disabled"]


@dataclass
class ProviderState:
    name: str
    mode: Mode = "disabled"
    last_error: str | None = None
    last_success_at: float | None = None
    last_failure_at: float | None = None
    calls: int = 0
    failures: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "mode": self.mode,
            "last_error": self.last_error,
            "last_success_at": _iso(self.last_success_at),
            "last_failure_at": _iso(self.last_failure_at),
            "calls": self.calls,
            "failures": self.failures,
        }


def _iso(ts: float | None) -> str | None:
    if ts is None:
        return None
    from datetime import datetime, timezone

    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


class _Registry:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._states: dict[str, ProviderState] = {}

    def state(self, name: str) -> ProviderState:
        with self._lock:
            return self._states.setdefault(name, ProviderState(name=name))

    def disabled(self, name: str) -> None:
        with self._lock:
            self.state(name).mode = "disabled"

    def success(self, name: str) -> None:
        with self._lock:
            s = self.state(name)
            s.mode = "live"
            s.calls += 1
            s.last_success_at = time.time()
            s.last_error = None

    def failure(self, name: str, error: str) -> None:
        with self._lock:
            s = self.state(name)
            s.mode = "fallback"
            s.calls += 1
            s.failures += 1
            s.last_failure_at = time.time()
            s.last_error = error[:300]
        log.warning("provider %s fell back: %s", name, error)

    def snapshot(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {name: s.as_dict() for name, s in self._states.items()}


registry = _Registry()


def describe(exc: Exception) -> str:
    """A failure message you can actually act on.

    `str(HTTPStatusError)` is a generic "Client error '400 Bad Request'" plus a
    link to MDN, which tells you nothing about *why* the provider rejected the
    call. The response body almost always does, so it goes in.
    """
    detail = f"{type(exc).__name__}: {exc}"
    response = getattr(exc, "response", None)
    if response is None:
        return detail
    try:
        body = response.json()
        message = (
            body.get("error", {}).get("message")
            if isinstance(body.get("error"), dict)
            else body.get("error") or body.get("message")
        )
        if message:
            return f"HTTP {response.status_code}: {message}"
        return f"HTTP {response.status_code}: {json.dumps(body)[:280]}"
    except Exception:
        text = (getattr(response, "text", "") or "").strip()
        return f"HTTP {response.status_code}: {text[:280]}" if text else detail


# --------------------------------------------------------------------------
# TTL cache
# --------------------------------------------------------------------------


@dataclass
class _Entry:
    value: Any
    expires_at: float


class TTLCache:
    """Small in-process cache.

    On serverless this is per-instance and dies with the container, which is
    fine — it exists to stop one page render making the same upstream call
    five times, not to be a shared cache.
    """

    def __init__(self, ttl_seconds: float, maxsize: int = 256) -> None:
        self._ttl = ttl_seconds
        self._maxsize = maxsize
        self._lock = threading.RLock()
        self._data: dict[str, _Entry] = {}

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            if entry.expires_at < time.time():
                self._data.pop(key, None)
                return None
            return entry.value

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        with self._lock:
            if len(self._data) >= self._maxsize:
                # Cheapest useful eviction: drop whatever expires soonest.
                oldest = min(self._data, key=lambda k: self._data[k].expires_at)
                self._data.pop(oldest, None)
            self._data[key] = _Entry(value, time.time() + (ttl or self._ttl))

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


def cached_call(
    cache: TTLCache,
    key: str,
    provider: str,
    live: Callable[[], Any],
    fallback: Callable[[], Any],
    *,
    failure_ttl: float = 120.0,
    enabled: bool = True,
):
    """Try the live provider, cache the result, fall back on any failure.

    A failure is cached as well, under a shorter TTL, so an outage costs one
    slow request per `failure_ttl` rather than one per page load.
    """
    if not enabled:
        registry.disabled(provider)
        return fallback()

    cache_key = f"{provider}:{key}"
    hit = cache.get(cache_key)
    if hit is not None:
        # A cached miss means "we tried recently and it failed".
        return fallback() if hit is _MISS else hit

    try:
        value = live()
    except Exception as exc:
        registry.failure(provider, describe(exc))
        cache.set(cache_key, _MISS, ttl=failure_ttl)
        return fallback()

    if value is None:
        registry.failure(provider, "provider returned no usable data")
        cache.set(cache_key, _MISS, ttl=failure_ttl)
        return fallback()

    registry.success(provider)
    cache.set(cache_key, value)
    return value


class _Miss:
    """Sentinel for a cached failure."""

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "<cached-miss>"


_MISS = _Miss()

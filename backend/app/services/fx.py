"""Exchange rates.

Live mid-market rates when they can be fetched, the static table otherwise.
The table is fine for showing an order of magnitude but it is hand-written and
drifts — USD/INR sat at 83.2 in it long after the real rate had moved — so
anything shown to a traveller as a conversion should prefer the live feed.

Frankfurter publishes ECB reference rates, needs no API key and no account.
"""

from __future__ import annotations

import logging

import httpx

from ..data.knowledge import CURRENCY_RATES
from . import providers

log = logging.getLogger(__name__)

RATES_URL = "https://api.frankfurter.app/latest"

# Rates move slowly and ECB publishes once a working day; six hours is far
# fresher than the data actually changes.
_CACHE = providers.TTLCache(ttl_seconds=6 * 60 * 60, maxsize=4)


def _fetch() -> dict[str, float] | None:
    """Rates per 1 USD. None if the feed is unusable."""
    wanted = [c for c in CURRENCY_RATES if c != "USD"]
    # The endpoint sits behind Cloudflare and 301s; without following that the
    # response body is an HTML redirect page rather than rates.
    r = httpx.get(
        RATES_URL,
        params={"from": "USD", "to": ",".join(wanted)},
        timeout=8.0,
        follow_redirects=True,
    )
    r.raise_for_status()
    rates = r.json().get("rates") or {}

    # A partial answer is worse than the table: mixing live and stale rates
    # would make conversions inconsistent with each other.
    missing = [c for c in wanted if c not in rates]
    if missing:
        log.warning("FX feed missing %s, keeping the static table", missing)
        return None

    return {"USD": 1.0, **{k: float(v) for k, v in rates.items()}}


def rates() -> tuple[dict[str, float], str]:
    """(rates per 1 USD, source label)."""
    live = providers.cached_call(
        _CACHE,
        "usd",
        "fx",
        live=_fetch,
        fallback=lambda: None,
    )
    if live:
        return live, "live"
    return CURRENCY_RATES, "indicative offline rates"


def rate(currency: str) -> float:
    table, _ = rates()
    return table.get(currency.upper(), CURRENCY_RATES.get(currency.upper(), 1.0))

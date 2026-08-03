"""LLM narration layer.

Deliberately narrow. The companion's *decisions* -- which stop to swap, what
to reorder -- are made deterministically in companion.py so they are testable
and never hallucinated. This module only phrases those decisions.

When OPENAI_API_KEY is absent every function returns its template fallback,
which is why the product is fully usable offline.
"""

from __future__ import annotations

import json
import logging

import httpx

from ..core.config import get_settings
from . import providers

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Nomad, a travel companion embedded in a live itinerary app.

You are not a chatbot. You speak like a well-travelled friend who has already
made the change and is telling the traveller what you did.

Rules:
- Lead with the action you took, not with an offer to help.
- Be concise: two or three sentences, no bullet lists, no headers.
- Never invent places, prices or times. Only reference what is in the context.
- No emoji. No "As an AI". No restating the question back.
"""


def _client() -> httpx.Client | None:
    """A client for whichever OpenAI-compatible provider is configured."""
    s = get_settings()
    if not s.llm_api_key:
        return None
    return httpx.Client(
        base_url=s.llm_base_url,
        headers={
            "Authorization": f"Bearer {s.llm_api_key}",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )


def complete(
    user_prompt: str,
    *,
    system: str = SYSTEM_PROMPT,
    max_tokens: int = 300,
    temperature: float = 0.7,
) -> str | None:
    """Single-turn completion. Returns None when unavailable or on any error."""
    client = _client()
    if client is None:
        providers.registry.disabled("ai")
        return None
    try:
        with client:
            r = client.post(
                "/chat/completions",
                json={
                    "model": get_settings().llm_model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"].strip()
            providers.registry.success("ai")
            return text
    except Exception as exc:  # network, quota, bad key -- fall back to templates
        providers.registry.failure("ai", providers.describe(exc))
        return None


def estimate_place_costs(
    *,
    destination: str,
    country: str,
    places: list[dict],
) -> dict[str, float] | None:
    """Ask for a realistic per-person cost, in USD, for each place.

    This replaces a price-level band — Google's `priceLevel` is five buckets
    and says nothing about what a ticket actually costs. The model has read a
    great many menus and admission pages, which makes it a genuinely better
    estimator here than a lookup table.

    It is still an estimate from a model, so the caller validates every value
    before trusting it. Anything unparseable, negative, or wildly out of line
    with the band it replaces is discarded and the band stands.
    """
    settings = get_settings()
    if not settings.live_ai or not settings.llm_pricing or not places:
        return None

    # Places are numbered rather than keyed by their real ids. Google's ids look
    # like "ChIJN1t_tDeuEmsRUsoyG83frY4", and a model asked to echo thirty of
    # those will eventually get one wrong — at which point that estimate is
    # silently dropped. A small integer is much harder to mistranscribe.
    indexed = [{"i": i, **place} for i, place in enumerate(places)]

    prompt = json.dumps(
        {
            "destination": destination,
            "country": country,
            "places": indexed,
            "task": (
                "For each place give the realistic cost for ONE person in USD. "
                "For attractions that is standard adult admission — use 0 for "
                "places that are free to enter, which includes most parks, "
                "temples, markets, squares and viewpoints. For restaurants, "
                "cafes and bars it is a typical spend per head for one visit, "
                "including a drink. Use local prices for this city, not "
                "international averages. Return JSON shaped exactly as "
                '{"costs": {"0": <number>, "1": <number>, ...}} keyed by the '
                '"i" value of each place, with an entry for every place, and '
                "no commentary."
            ),
        },
        ensure_ascii=False,
    )

    raw = complete_json(
        prompt,
        system=(
            "You estimate travel prices. You know local price levels and you "
            "do not inflate them. You reply with JSON only."
        ),
        max_tokens=1600,
    )
    if not raw:
        return None

    costs = raw.get("costs")
    if not isinstance(costs, dict):
        return None

    # Map the indices back onto the real place ids. Accept an id key too, in
    # case the model decides to answer that way regardless.
    by_index = {str(i): place.get("id") for i, place in enumerate(places)}
    known_ids = {str(place.get("id")) for place in places}

    cleaned: dict[str, float] = {}
    for key, value in costs.items():
        place_id = by_index.get(str(key).strip())
        if place_id is None and str(key) in known_ids:
            place_id = str(key)
        if place_id is None:
            continue
        try:
            amount = float(value)
        except (TypeError, ValueError):
            continue
        if amount < 0 or amount > 500:
            continue
        cleaned[place_id] = round(amount, 2)

    if not cleaned:
        log.warning(
            "price estimates unusable: %d returned, none matched a place",
            len(costs),
        )
    return cleaned or None


def _extract_json(text: str) -> dict | None:
    """Pull a JSON object out of a reply that may be wrapped in prose or fences."""
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = (parts[1] if len(parts) > 1 else text).removeprefix("json").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def complete_json(
    user_prompt: str, *, system: str, max_tokens: int = 800
) -> dict | None:
    """Completion constrained to a JSON object. None on any failure.

    Native JSON mode is tried first, then the same call without it. Support for
    `response_format` varies by provider *and* by model — one that rejects it
    answers 400 — and losing price estimates over a single parameter is a worse
    outcome than parsing the object out of ordinary prose.
    """
    client = _client()
    if client is None:
        providers.registry.disabled("ai")
        return None

    def payload(json_mode: bool) -> dict:
        body: dict = {
            "model": get_settings().llm_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        return body

    last_error: Exception | None = None
    try:
        with client:
            for json_mode in (True, False):
                try:
                    r = client.post("/chat/completions", json=payload(json_mode))
                    r.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    last_error = exc
                    # Only a rejected *request* is worth retrying differently.
                    # Auth, rate limits and server faults will not improve.
                    if exc.response.status_code != 400 or not json_mode:
                        break
                    log.info("JSON mode rejected, retrying without it")
                    continue
                except Exception as exc:
                    last_error = exc
                    break

                parsed = _extract_json(r.json()["choices"][0]["message"]["content"])
                if parsed is not None:
                    providers.registry.success("ai")
                    return parsed
                last_error = ValueError("reply was not valid JSON")
                break
    except Exception as exc:
        last_error = exc

    providers.registry.failure(
        "ai",
        providers.describe(last_error) if last_error else "no usable JSON reply",
    )
    return None


def classify_intent(message: str, allowed: list[str]) -> str | None:
    """Last-resort intent classification for phrasing the keywords missed.

    This picks a *label*, never an action. The handler for that label still
    does the deterministic work, so a mislabel produces the wrong help — never
    an invented itinerary change.
    """
    if not get_settings().live_ai:
        return None

    prompt = json.dumps(
        {
            "traveller_said": message,
            "labels": allowed,
            "task": (
                "Return exactly one label from `labels` describing the "
                "traveller's situation. Return `general` if none fit. "
                "Reply with the label only — no punctuation, no explanation."
            ),
        },
        ensure_ascii=False,
    )
    raw = complete(
        prompt,
        system="You are a strict text classifier. You reply with one word.",
        max_tokens=8,
        temperature=0,
    )
    if not raw:
        return None

    label = raw.strip().strip(".\"'`").lower()
    return label if label in allowed else None


def narrate_change(
    *,
    destination: str,
    user_message: str,
    intent: str,
    changes: list[str],
    context: dict,
    fallback: str,
) -> str:
    """Phrase an already-decided set of itinerary changes."""
    if not get_settings().live_ai:
        return fallback

    prompt = json.dumps(
        {
            "destination": destination,
            "traveller_said": user_message,
            "detected_situation": intent,
            "changes_you_already_made": changes,
            "trip_context": context,
            "task": (
                "Tell the traveller what you changed and why, in two or three "
                "sentences. If changes_you_already_made is empty, answer the "
                "question directly using trip_context only."
            ),
        },
        ensure_ascii=False,
    )
    return complete(prompt) or fallback


def narrate_journal(*, destination: str, day_context: dict, fallback: str) -> str:
    if not get_settings().live_ai:
        return fallback

    prompt = json.dumps(
        {
            "destination": destination,
            "day": day_context,
            "task": (
                "Write a 2-3 sentence diary entry for this day in warm past "
                "tense, first person plural. Reference only the places listed."
            ),
        },
        ensure_ascii=False,
    )
    return complete(
        prompt,
        system="You write short, vivid travel diary entries. No emoji, no lists.",
    ) or fallback

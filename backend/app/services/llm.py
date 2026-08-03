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
    s = get_settings()
    if not s.openai_api_key:
        return None
    return httpx.Client(
        base_url=s.openai_base_url,
        headers={
            "Authorization": f"Bearer {s.openai_api_key}",
            "Content-Type": "application/json",
        },
        timeout=25.0,
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
                    "model": get_settings().openai_model,
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
        providers.registry.failure("ai", f"{type(exc).__name__}: {exc}")
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

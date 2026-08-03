"""Vercel serverless entrypoint.

Vercel's Python runtime serves any ASGI app exported as `app` from a file
under `api/`. `vercel.json` rewrites every path to this function, and the
original request path is preserved, so FastAPI's own `/api/...` routes match
exactly as they do under uvicorn locally.

Nothing app-specific lives here on purpose — `python -m uvicorn app.main:app`
remains the single source of truth for how the API is assembled.
"""

from app.main import app

__all__ = ["app"]

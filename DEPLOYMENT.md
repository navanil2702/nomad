# Deploying Nomad

Target: **two Vercel projects from this one repo, with Supabase for storage.**

- `nomad-api` → the FastAPI backend, root directory `backend`
- `nomad` → the Next.js frontend, root directory `frontend`

Why two projects rather than one: Vercel scopes a deployment to its Root
Directory, and a Python function under `frontend/` cannot import the FastAPI
app that lives in `backend/`. Splitting them is the supported shape, costs
nothing extra, and the code already has the seams for it — the frontend
proxies `/api/*` server-side, so the browser still only ever talks to its own
origin and there is no CORS to configure.

Everything below is free tier.

---

## 1. Supabase — the database

The JSON-file store the app uses locally cannot work on Vercel: serverless
filesystems are wiped between invocations. Supabase replaces it. The adapter
is already written (`backend/app/store.py`), so this is configuration only.

1. Create a project at <https://supabase.com/dashboard>. Any region; pick one
   near your users.
2. Open **SQL Editor → New query**, paste the contents of
   [`supabase/schema.sql`](supabase/schema.sql), and run it.
3. Go to **Project Settings → API** and copy two values:
   - **Project URL** → `SUPABASE_URL`
   - **service_role** secret → `SUPABASE_SERVICE_KEY`

> The `service_role` key bypasses Row Level Security. It belongs only in the
> backend's server-side environment variables — never in the frontend, never
> in a `NEXT_PUBLIC_*` variable, never committed.

---

## 2. `nomad-api` — the backend

On <https://vercel.com/new>, import `navanil2702/nomad`, then:

| Setting | Value |
| --- | --- |
| Project Name | `nomad-api` |
| Framework Preset | **Other** |
| Root Directory | `backend` |

Add these environment variables:

| Name | Value |
| --- | --- |
| `SUPABASE_URL` | your Project URL |
| `SUPABASE_SERVICE_KEY` | your `service_role` key |

Optional, all of which have working offline fallbacks:

| Name | Effect if set |
| --- | --- |
| `OPENAI_API_KEY` | Companion replies are phrased by the model instead of templates. Decisions are unchanged either way. |
| `OPENAI_MODEL` | Defaults to `gpt-4o-mini`. |
| `OPENWEATHER_API_KEY` | Real forecasts instead of the climate model. |
| `GOOGLE_MAPS_API_KEY` | Real Places photos. |
| `SEED_DEMO_TRIP` | `false` to deploy with an empty database. |

Deploy. Then check:

```bash
curl https://nomad-api.vercel.app/api/health
```

You want `"database": "supabase"`. If it says `json-file`, the Supabase
variables did not reach the function — check them and redeploy.

Seed the demo trip:

```bash
curl -X POST https://nomad-api.vercel.app/api/seed
```

This is idempotent and only writes when the table is empty. It exists because
some serverless runtimes never fire ASGI lifespan events, so the boot-time
seed may not run.

---

## 3. `nomad` — the frontend

Import the same repo again as a second project:

| Setting | Value |
| --- | --- |
| Project Name | `nomad` |
| Framework Preset | **Next.js** (detected) |
| Root Directory | `frontend` |

One environment variable:

| Name | Value |
| --- | --- |
| `API_URL` | `https://nomad-api.vercel.app` — your backend URL, no trailing slash |

Deploy, and open the site.

### Why `API_URL` and not `NEXT_PUBLIC_API_URL`

`API_URL` is server-only. Next rewrites `/api/*` to it, so the browser keeps
calling its own origin and never makes a cross-origin request. That means no
CORS configuration, and the `service_role` side of the system is never
reachable from a browser tab.

Set `NEXT_PUBLIC_API_URL` instead only if you deliberately want the browser to
call the API directly. If you do, you must also set `CORS_ORIGINS` on the
backend to your frontend's URL, or every request will fail.

---

## 4. Verify

```bash
curl https://nomad-api.vercel.app/api/health          # database: supabase
curl https://nomad.vercel.app/api/health              # same JSON, through the proxy
curl -s https://nomad.vercel.app/api/trips | head -c 200
```

Then in the browser: open the trip, confirm the proactive weather alert
appears, send the companion "I'm tired", and reload — the change must still be
there. If it survives a reload, persistence is working.

---

## Notes and limits

**Cold starts.** The free tier scales to zero. The first request after an idle
period takes a few seconds while the Python function boots.

**Concurrent seeding.** Two simultaneous cold starts can both find an empty
database and both decide to seed. The demo trip therefore has a fixed id
(`trip_demo_tokyo`), so they upsert the same row rather than creating
duplicates. Set `SEED_DEMO_TRIP=false` to deploy with an empty database
instead.

**`maxDuration`.** Set to 30s in `backend/vercel.json`. Hobby plans cap at 60s.
Only relevant if you enable `OPENAI_API_KEY` and the model is slow.

**Preview deployments.** Every branch gets its own frontend URL, but they all
point at the same `API_URL` and therefore the same Supabase data. Use a second
Supabase project for previews if that matters.

**Custom domain.** Add it to the `nomad` project only. The API does not need
one — nothing but Vercel's own network calls it.

---

## Alternatives

**One service instead of two.** Fly.io or Railway can run a single container
with a persistent volume, which keeps the JSON store and the zero-database
promise intact. More setup, no Supabase account.

**Backend on Render.** Works and needs no database, but Render's free disk
resets on redeploy and free services sleep after 15 minutes idle, so trips are
not durable.

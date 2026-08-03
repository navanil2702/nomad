# Nomad

**Planning is easy. Travel changes. Your itinerary should adapt.**

### → [nomad-lyart.vercel.app](https://nomad-lyart.vercel.app)

A real-time travel companion. It builds a day-by-day plan around your budget,
pace and the actual forecast — then keeps watching, and rewrites the plan
before the problem reaches you.

It uses **live Google Places, Google Maps, OpenWeather and OpenAI** when keys are
configured, and falls back to offline engines when they are missing or failing —
so it still runs end to end with **zero API keys and zero infrastructure**.

> The live demo is on Vercel's free tier, so the first request after an idle
> spell wakes the API and takes a few seconds. Check the badge in the header to
> see which providers are actually live on it.

---

## Quick start

Two terminals, about a minute.

```bash
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/uvicorn app.main:app --reload
```

```bash
cd frontend && npm install && npm run dev
```

Open <http://localhost:3000>. A five-day Tokyo trip is already seeded — day 2
of 5, with two days of expenses logged, journal entries written and the
proactive engine having already handled the first weather problem.

No account is needed. Sign-in is there, but nothing gates on it.

---

## What makes it a companion, not a chatbot

Open the trip and the first thing on screen is something you never asked for:

> **Rain showers on Thursday** · Already handled
> Looks like rain showers on Thursday from 4 PM, 76% chance. I've swapped
> Hamarikyu Gardens for Nezu Museum & Garden.

That already happened. The itinerary is different from when you closed it.
There's an **Undo** if you disagree.

This is the core design decision, and it's worth being precise about it:

**The language model never decides what changes.** `services/companion.py`
classifies the situation and performs concrete, typed mutations. The model —
when a key is present — only *phrases* the changes that already happened. So
the companion physically cannot promise a swap it didn't make, and every reply
ships with a diff of what actually moved.

With no `OPENAI_API_KEY`, the templates take over and the product behaves
identically. The intelligence is in the planner, not the prose.

### What it reacts to

| You say | What it does |
| --- | --- |
| "It's raining" | Swaps outdoor stops for indoor ones that are open at that hour; pushes what's left to the driest later day |
| "I'm tired" | Moves the highest-effort stop to another day, inserts a real sit-down café, widens every gap |
| "I'm hungry" | Picks the best-rated place near your last stop that's actually open now, and slots it in |
| "I want vegetarian food nearby" | Same, restricted to genuinely meat-free kitchens |
| "My train is delayed 2 hours" | Shifts the whole day, drops the weakest stop to buy the time back, warns about closing times |
| "I have two free hours" | Finds something that fits *in* two hours, near where you are |
| "I spent more than expected" | Downgrades upcoming meals and swaps paid attractions for free ones, with the saving on each line |

It also answers without touching anything: the weather, your remaining budget,
what's nearby, local phrases, what's still unpacked.

### What it does unprompted

`services/proactive.py` scans on every load and after every expense:

- **Weather** — rain or storms on a day with outdoor stops. Applied
  immediately, because finding out at 2 PM has already cost you the afternoon.
- **Budget** — burn rate ahead of trip progress. Offered, not applied.
- **Pace** — two brutal days back to back.
- **Closing times** — a stop scheduled past its venue's last entry.

---

## The planner

Deterministic, testable, and it reasons about things generic planners skip.

Each place in the catalog carries whether it's **indoor** (rain swaps), its
**walking intensity** (fatigue swaps), its **price level** (budget swaps),
**opening hours** and coordinates. Scoring weighs interest match, rating,
popularity (log-damped so a 300k-review site doesn't always win), cost against
your daily budget, geographic proximity to the previous stop, and category
variety within the day.

Three invariants the planner holds, and the companion preserves through every
mutation:

1. **Nothing is scheduled outside its opening hours** — not too early, not
   past closing. Verified after every companion action.
2. **No place appears twice in one day.** Across days, repeats only start once
   the catalog is genuinely exhausted, and then least-recently-visited first.
3. **The plan stays physically possible.** Inserting a stop pushes everything
   after it later; `enforce_hours` then swaps, moves or drops whatever no
   longer fits, rather than showing an itinerary you can't follow.

---

## Architecture

```
nomad/
├── backend/                  FastAPI
│   └── app/
│       ├── core/config.py       optional-provider settings
│       ├── models/schemas.py    the domain model (mirrored in lib/types.ts)
│       ├── data/                curated place catalog, phrases, FX, emergency
│       ├── services/
│       │   ├── places.py           catalog resolution, travel time, Maps links
│       │   ├── itinerary.py        the planner
│       │   ├── companion.py        intent detection + itinerary mutations
│       │   ├── proactive.py        the unprompted engine
│       │   ├── weather.py          OpenWeather + offline climate model
│       │   ├── packing.py          forecast-derived packing list
│       │   ├── journal.py          daily entries + trip retrospective
│       │   ├── llm.py              narration only, never decisions
│       │   └── trips.py            orchestration
│       ├── routers/             trips, companion, expenses, journal, tools
│       ├── store.py             JSON-file store + Supabase adapter
│       └── seed.py              the demo trip
└── frontend/                 Next.js 14 · TypeScript · Tailwind · Framer Motion
    ├── app/                     landing, /plan, /trips, /trip/[id], /shared/[token]
    ├── components/
    │   ├── ui/                     shadcn-style primitives on Radix
    │   ├── landing/                hero illustration, scripted companion demo
    │   ├── plan/                   three-step trip wizard
    │   ├── trip/                   the seven dashboard panels
    │   └── companion/              floating dock, alert stack, change diffs
    └── lib/                     api client, types, formatting, visuals
```

The browser talks to `/api/*` on its own origin; Next rewrites that to FastAPI,
so CORS never becomes a setup step.

---

## Features

**Itinerary** — morning / afternoon / evening, per-stop cost, travel time and
mode between stops, Google Maps directions links, local tips, and a budget
breakdown across accommodation, food, transport and activities.

**Map** — every stop plotted with the day's route drawn between them. Tap a pin
for opening hours, rating, review count, price level, walking effort, travel
time and what's nearby. With no Maps key it's an equirectangular projection of
the itinerary's own coordinates over a styled canvas; the pins still deep-link
to Google Maps.

**Weather** — five-day forecast, automatic warnings, and how many of that day's
stops are already indoors.

**Packing** — derived from your forecast, your activities and the country's
plug type and tipping norms. Every item says why it's there.

**Expenses** — five categories, pie chart and per-day bars (actual against
planned), remaining budget, daily average and projected total. Logging an
expense re-runs the proactive scan.

**Journal** — each finished day written up automatically: places, spend,
highlights and an inferred mood. At the end, a bound retrospective.

**Toolbox** — local phrases with pronunciation, emergency numbers, currency
converter, live time-zone comparison, a downloadable offline bundle, and a
read-only share link.

---

## Live providers, and what happens without them

Every provider is tried first. The offline engine is the fallback, never the
default.

| Capability | Live | Fallback |
| --- | --- | --- |
| Places | Google Places API (New) — real venues, hours, ratings, price levels, photos | Curated catalog for six cities; generated catalog anywhere else |
| Maps | Google Maps JS API — real tiles, markers, day routes | Coordinate projection over a styled canvas; pins still deep-link out |
| Weather | OpenWeather 5-day forecast | Seeded climate model, stable per trip |
| AI | **Groq** (`GROQ_MODEL`, default `llama-3.3-70b-versatile`) or **OpenAI** (`OPENAI_MODEL`, default `gpt-4o-mini`) — for phrasing, for classifying messages the keywords miss, and for per-place price estimates | Template phrasing; keyword classification; price-level bands. **Itinerary decisions are identical either way** |
| Database | Supabase Postgres | JSON files under `backend/.data/` |
| Auth | Google Identity Services | Local demo profile |

### Fallbacks are visible, not silent

Mock weather looks exactly like real weather, which makes a silent fallback the
most dangerous failure mode here. So `GET /api/providers` reports, per provider,
whether it is `live`, `ready` (configured but not yet called), `fallback` (tried
and failed, with the reason) or `offline` (no key). The header badge in the app
shows the same thing.

Failures are cached for two minutes, so one outage costs a single slow request
rather than one per page load.

### Keys

Set on the backend: `GOOGLE_MAPS_API_KEY`, `OPENWEATHER_API_KEY`, and one of
`GROQ_API_KEY` / `OPENAI_API_KEY` — both speak the OpenAI chat-completions
protocol, so only the base URL and model name differ, and Groq wins if both are
set. Set on the frontend: `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` for the
map itself — a **separate, browser-restricted key**, because that one is public.

Places photos are proxied through `/api/places/photo`, which resolves them to
signed, key-less URLs server-side, so the Places key never reaches a browser.

> The spec asked for GPT-5.5. That isn't a model I can verify exists, so the
> model id is an env var (`OPENAI_MODEL`) defaulting to `gpt-4o-mini`. Point it
> at whatever you actually have access to.

---

## How activity pricing works

```
activity cost = per-person price × destination cost index × travellers × FX rate
```

The per-person price comes from the best source available, and a trip records
which one it used in `catalog.pricing`:

| `pricing` | Source |
| --- | --- |
| `researched` | Hand-checked real prices in the curated catalog |
| `estimated` | The model, asked for actual admission and typical per-head spend |
| `price-band` | Google's five `priceLevel` buckets mapped to USD |
| `template` | Generic placeholder costs for an invented catalog |

Model estimates are validated before use: anything unparseable, negative, over
$500, or more than 8× off the band it replaces is discarded and the band
stands. A zero is always accepted — plenty of temples, markets and squares are
genuinely free while sitting in a non-zero price band. If more than half a
batch is rejected the whole thing is thrown away.

The **cost index** only scales *generic* figures. Researched and estimated
prices are already local, so applying it to them would double-count the
destination.

Set `LLM_PRICING=false` to keep the bands and save a call per trip.

## API

`http://localhost:8000/docs` for the full OpenAPI browser.

```
GET    /api/health
GET    /api/trips                          POST /api/trips
GET    /api/trips/{id}                     DELETE /api/trips/{id}
POST   /api/trips/{id}/regenerate

POST   /api/trips/{id}/chat                the companion
GET    /api/trips/{id}/alerts
POST   /api/trips/{id}/alerts/scan
POST   /api/trips/{id}/alerts/{aid}/apply | /undo | /dismiss

GET    /api/trips/{id}/map                 GET /api/trips/{id}/weather
GET    /api/trips/{id}/packing             GET /api/trips/{id}/local
GET    /api/trips/{id}/offline             GET /api/trips/{id}/share
POST   /api/trips/{id}/expenses            GET /api/trips/{id}/expenses/stats
POST   /api/trips/{id}/journal/autowrite   GET /api/trips/{id}/journal/retrospective

GET    /api/destinations                   GET /api/currency/convert
GET    /api/timezone                       GET /api/shared/{token}
```

---

## Configuration

Copy `.env.example` to `.env` (backend) or `frontend/.env.local` (frontend) and
uncomment what you want. Everything is optional.

## Deploying

See **[DEPLOYMENT.md](DEPLOYMENT.md)** — two Vercel projects from this repo
(`backend/` and `frontend/`) with Supabase for storage, all on free tiers.

The JSON-file store cannot survive on a serverless filesystem, so a deployment
needs Supabase; `supabase/schema.sql` is the one-time setup. In production the
frontend proxies `/api/*` server-side via `API_URL`, so the browser stays
same-origin and there is no CORS to configure.

## Notes

- Deep-link any dashboard panel with `?tab=map`, `?tab=expenses`, etc.
- Trips are capped at 20 days; the planner degrades past a fortnight.
- Currency rates are indicative offline values, not a live FX feed.

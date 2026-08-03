-- Nomad — Supabase schema.
-- Run once in the Supabase SQL Editor (Dashboard → SQL Editor → New query).
--
-- The whole trip is stored as a single jsonb document. That is deliberate:
-- a trip is only ever read and written as a unit, the shape is owned by the
-- Pydantic models in backend/app/models/schemas.py, and keeping it in one
-- column means the schema never has to chase changes to the domain model.
-- The promoted columns exist purely so the API can list, look up and sort
-- without deserialising every row.

create table if not exists public.trips (
  id           text primary key,
  owner        text        not null default 'demo-user',
  share_token  text        not null,
  updated_at   text        not null,
  payload      jsonb       not null,
  created_at   timestamptz not null default now()
);

-- Listing is always "most recently touched first".
create index if not exists trips_updated_at_idx
  on public.trips (updated_at desc);

-- Share links resolve by token.
create unique index if not exists trips_share_token_idx
  on public.trips (share_token);

-- Ready for per-user trips once real auth is wired up.
create index if not exists trips_owner_idx
  on public.trips (owner);

-- Row Level Security.
--
-- The API talks to Supabase with the service_role key, which bypasses RLS.
-- Enabling it with no policies therefore changes nothing for the backend, but
-- means the anon/public key cannot read or write this table if it ever leaks
-- or gets used from a browser. Leave it on.
alter table public.trips enable row level security;

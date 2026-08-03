"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  Bus,
  Car,
  Clock,
  ExternalLink,
  Footprints,
  Home,
  Lightbulb,
  Sparkles,
  Star,
  Sun,
  Sunrise,
  Sunset,
  Timer,
  Utensils,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { BudgetBreakdownCard } from "@/components/trip/budget-breakdown";
import { categoryIcon, placeGradient, WEATHER_ICON } from "@/lib/place-visual";
import type { Activity, DayPlan, Slot, Trip } from "@/lib/types";
import { cn, duration, formatDate, formatTime, isToday, money } from "@/lib/utils";

const SLOT_META: Record<Slot, { label: string; icon: typeof Sun }> = {
  morning: { label: "Morning", icon: Sunrise },
  afternoon: { label: "Afternoon", icon: Sun },
  evening: { label: "Evening", icon: Sunset },
};

const TRAVEL_ICON = { walk: Footprints, transit: Bus, taxi: Car };

export function ItineraryPanel({
  trip,
  touched,
}: {
  trip: Trip;
  touched: string[];
}) {
  const todayIndex = Math.max(
    trip.days.findIndex((d) => isToday(d.date)),
    0,
  );
  const [active, setActive] = React.useState(todayIndex);

  // When the companion changes a day, jump the reader to it.
  React.useEffect(() => {
    if (!touched.length) return;
    const idx = trip.days.findIndex((d) =>
      d.activities.some((a) => touched.includes(a.id)),
    );
    if (idx >= 0) setActive(idx);
  }, [touched, trip.days]);

  const day = trip.days[active];
  const weather = trip.weather.find((w) => w.date === day?.date);

  if (!day) {
    return <p className="text-muted-foreground">This trip has no days yet.</p>;
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
      <div className="min-w-0">
        {/* day switcher */}
        <div className="scrollbar-thin -mx-1 flex gap-2 overflow-x-auto px-1 pb-2">
          {trip.days.map((d, i) => {
            const w = trip.weather.find((x) => x.date === d.date);
            const Icon = w ? WEATHER_ICON[w.condition] : Sun;
            const changed = d.activities.some((a) => touched.includes(a.id));
            return (
              <button
                key={d.id}
                onClick={() => setActive(i)}
                className={cn(
                  "relative shrink-0 rounded-2xl border px-4 py-3 text-left transition-all",
                  i === active
                    ? "border-primary bg-primary/5 shadow-sm"
                    : "border-border hover:border-primary/40 hover:bg-secondary/50",
                )}
              >
                {changed && (
                  <span className="absolute -right-1 -top-1 flex size-3">
                    <span className="absolute inline-flex size-full animate-pulse-ring rounded-full bg-accent" />
                    <span className="relative inline-flex size-3 rounded-full bg-accent" />
                  </span>
                )}
                <span className="block text-xs text-muted-foreground">
                  Day {d.day_number}
                  {isToday(d.date) && (
                    <span className="ml-1.5 font-medium text-primary">Today</span>
                  )}
                </span>
                <span className="mt-0.5 flex items-center gap-1.5 text-sm font-medium">
                  {formatDate(d.date, { weekday: "short", day: "numeric", month: undefined })}
                  <Icon className="size-3.5 text-muted-foreground" />
                </span>
              </button>
            );
          })}
        </div>

        {/* day header */}
        <div className="mt-5 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-display text-2xl italic">{day.title}</h2>
            <p className="mt-1 max-w-xl text-sm leading-relaxed text-muted-foreground">
              {day.summary}
            </p>
          </div>
          <div className="flex gap-2">
            <Badge variant="secondary">
              <Timer /> {duration(day.total_travel_minutes)} moving
            </Badge>
            <Badge variant="default">
              {money(day.estimated_cost, trip.preferences.currency)}
            </Badge>
          </div>
        </div>

        {/* timeline */}
        <div className="mt-6 space-y-6">
          {(["morning", "afternoon", "evening"] as Slot[]).map((slot) => {
            const items = day.activities.filter((a) => a.slot === slot);
            if (!items.length) return null;
            const SlotIcon = SLOT_META[slot].icon;
            return (
              <div key={slot}>
                <div className="mb-3 flex items-center gap-2">
                  <SlotIcon className="size-4 text-muted-foreground" />
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    {SLOT_META[slot].label}
                  </h3>
                  <span className="h-px flex-1 bg-border" />
                </div>
                <div className="space-y-3">
                  {items.map((activity, i) => (
                    <ActivityCard
                      key={activity.id}
                      activity={activity}
                      currency={trip.preferences.currency}
                      highlighted={touched.includes(activity.id)}
                      index={i}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {day.local_tips.length > 0 && (
          <Card className="mt-6 border-primary/20 bg-primary/[0.04] p-5">
            <div className="flex items-center gap-2">
              <Lightbulb className="size-4 text-primary" />
              <h3 className="text-sm font-semibold">Local tips for this day</h3>
            </div>
            <ul className="mt-3 space-y-2">
              {day.local_tips.map((tip, i) => (
                <li key={i} className="flex gap-2.5 text-sm leading-relaxed">
                  <span className="mt-2 size-1 shrink-0 rounded-full bg-primary" />
                  {tip}
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>

      <aside className="space-y-4">
        {weather && (
          <Card className="overflow-hidden p-5">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Forecast for day {day.day_number}
            </p>
            <div className="mt-3 flex items-center gap-3">
              {React.createElement(WEATHER_ICON[weather.condition], {
                className: "size-9 text-primary",
              })}
              <div>
                <p className="text-2xl font-semibold tabular-nums">
                  {Math.round(weather.temp_max_c)}°
                  <span className="ml-1 text-base font-normal text-muted-foreground">
                    / {Math.round(weather.temp_min_c)}°
                  </span>
                </p>
                <p className="text-sm text-muted-foreground">{weather.description}</p>
              </div>
            </div>
            <p className="mt-3 text-sm text-muted-foreground">
              {weather.precipitation_chance}% chance of rain ·{" "}
              {Math.round(weather.wind_kph)} km/h wind
            </p>
          </Card>
        )}

        <BudgetBreakdownCard trip={trip} />
      </aside>
    </div>
  );
}

function ActivityCard({
  activity,
  currency,
  highlighted,
  index,
}: {
  activity: Activity;
  currency: string;
  highlighted: boolean;
  index: number;
}) {
  const Icon = categoryIcon(String(activity.place.category));
  const TravelIcon = TRAVEL_ICON[activity.travel_mode];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.25 }}
    >
      {activity.travel_time_minutes > 0 && (
        <div className="mb-2 flex items-center gap-2 pl-4 text-xs text-muted-foreground">
          <TravelIcon className="size-3.5" />
          {duration(activity.travel_time_minutes)} by {activity.travel_mode}
        </div>
      )}

      <Card
        className={cn(
          "overflow-hidden transition-all",
          highlighted && "border-accent shadow-lg shadow-accent/10 ring-2 ring-accent/25",
        )}
      >
        <div className="flex">
          <div
            className="relative w-2 shrink-0 sm:w-24"
            style={placeGradient(activity.place)}
          >
            <Icon className="absolute left-1/2 top-1/2 hidden size-7 -translate-x-1/2 -translate-y-1/2 text-white/85 sm:block" />
          </div>

          <div className="min-w-0 flex-1 p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium tabular-nums text-primary">
                    {formatTime(activity.start_time)}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    – {formatTime(activity.end_time)}
                  </span>
                  {activity.is_meal && (
                    <Badge variant="accent">
                      <Utensils /> Meal
                    </Badge>
                  )}
                  {activity.place.indoor && (
                    <Badge variant="secondary">
                      <Home /> Indoor
                    </Badge>
                  )}
                  {activity.origin !== "planned" && (
                    <Badge variant="warning">
                      <Sparkles /> Companion
                    </Badge>
                  )}
                </div>
                <h4 className="mt-1 truncate text-base font-semibold tracking-tight">
                  {activity.place.name}
                </h4>
              </div>

              <span className="shrink-0 text-sm font-medium tabular-nums">
                {activity.estimated_cost > 0
                  ? money(activity.estimated_cost, currency)
                  : "Free"}
              </span>
            </div>

            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Star className="size-3 fill-current text-amber-500" />
                {activity.place.rating.toFixed(1)}
                {activity.place.review_count > 0 && (
                  <span className="opacity-70">
                    ({(activity.place.review_count / 1000).toFixed(0)}k)
                  </span>
                )}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="size-3" />
                {activity.place.opening_hours}
              </span>
              <span>{duration(activity.duration_minutes)}</span>
            </div>

            {activity.local_tip && (
              <p className="mt-2.5 flex gap-2 rounded-lg bg-secondary/60 px-3 py-2 text-xs leading-relaxed">
                <Lightbulb className="mt-px size-3.5 shrink-0 text-primary" />
                {activity.local_tip}
              </p>
            )}

            {activity.note && (
              <p className="mt-2 text-xs font-medium text-accent">{activity.note}</p>
            )}

            <a
              href={activity.maps_url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-primary transition-colors hover:text-primary/80"
            >
              Open in Google Maps <ExternalLink className="size-3" />
            </a>
          </div>
        </div>
      </Card>
    </motion.div>
  );
}

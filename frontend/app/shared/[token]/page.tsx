import Link from "next/link";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ArrowRight, CalendarDays, Clock, MapPin, Users } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Logo } from "@/components/site-header";
import { ThemeToggle } from "@/components/theme-toggle";
import { api, ApiError } from "@/lib/api";
import type { DayPlan, WeatherDay } from "@/lib/types";
import { formatDate, formatTime, money } from "@/lib/utils";

export const metadata: Metadata = { title: "Shared itinerary" };

interface SharedTrip {
  title: string;
  destination: string;
  start_date: string;
  end_date: string;
  travelers: number;
  interests: string[];
  pace: string;
  days: DayPlan[];
  weather: WeatherDay[];
  budget_breakdown: Record<string, number>;
}

export default async function SharedTripPage({
  params,
}: {
  params: { token: string };
}) {
  let trip: SharedTrip;
  try {
    trip = await api.sharedTrip(params.token);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    throw err;
  }

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur-xl">
        <div className="container flex h-16 items-center justify-between">
          <Logo />
          <div className="flex items-center gap-2">
            <Badge variant="outline">Shared · read-only</Badge>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <section className="aurora relative border-b border-border/60">
        <div className="grid-lines pointer-events-none absolute inset-0 opacity-25" />
        <div className="container relative py-10">
          <Badge variant="outline" className="mb-3 gap-1.5 bg-background/60">
            <MapPin className="size-3" />
            {trip.destination}
          </Badge>
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            {trip.title}
          </h1>
          <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-sm text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <CalendarDays className="size-4" />
              {formatDate(trip.start_date)} — {formatDate(trip.end_date)}
            </span>
            <span className="flex items-center gap-1.5">
              <Users className="size-4" />
              {trip.travelers} {trip.travelers === 1 ? "traveller" : "travellers"}
            </span>
            <span className="capitalize">{trip.pace} pace</span>
          </div>
          <div className="mt-4 flex flex-wrap gap-1.5">
            {trip.interests.map((i) => (
              <Badge key={i} variant="secondary" className="capitalize">
                {i}
              </Badge>
            ))}
          </div>
        </div>
      </section>

      <main className="container py-10">
        <div className="space-y-8">
          {trip.days.map((day) => {
            const weather = trip.weather.find((w) => w.date === day.date);
            return (
              <div key={day.id}>
                <div className="flex flex-wrap items-baseline justify-between gap-3">
                  <div>
                    <p className="text-xs text-muted-foreground">
                      Day {day.day_number} · {formatDate(day.date)}
                    </p>
                    <h2 className="font-display text-2xl italic">{day.title}</h2>
                  </div>
                  {weather && (
                    <Badge variant="secondary">
                      {Math.round(weather.temp_max_c)}° · {weather.description}
                    </Badge>
                  )}
                </div>
                <p className="mt-1.5 max-w-2xl text-sm text-muted-foreground">
                  {day.summary}
                </p>

                <div className="mt-4 space-y-2.5">
                  {day.activities.map((a) => (
                    <Card key={a.id} className="flex items-center gap-4 p-4">
                      <span className="w-16 shrink-0 text-sm font-medium tabular-nums text-primary">
                        {formatTime(a.start_time)}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-medium">{a.place.name}</p>
                        <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
                          <Clock className="size-3" />
                          {a.place.opening_hours}
                        </p>
                      </div>
                      <span className="shrink-0 text-sm tabular-nums text-muted-foreground">
                        {a.estimated_cost > 0 ? money(a.estimated_cost, "USD") : "Free"}
                      </span>
                    </Card>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        <Card className="mt-12 p-6 text-center">
          <h2 className="text-lg font-semibold tracking-tight">
            Want one that adapts while you travel?
          </h2>
          <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
            This is a static copy. The live version rewrites itself when the weather
            turns or the train is late.
          </p>
          <Button variant="gradient" className="mt-5" asChild>
            <Link href="/plan">
              Plan your own <ArrowRight />
            </Link>
          </Button>
        </Card>
      </main>
    </div>
  );
}

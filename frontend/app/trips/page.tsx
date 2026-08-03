import Link from "next/link";
import type { Metadata } from "next";
import { ArrowRight, CalendarDays, Plus, Users, Wallet } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { SiteHeader } from "@/components/site-header";
import { api } from "@/lib/api";
import type { TripSummary } from "@/lib/types";
import { daysBetween, formatDate, hashHue, money } from "@/lib/utils";

export const metadata: Metadata = { title: "My trips" };

async function getTrips(): Promise<{ trips: TripSummary[]; error: string | null }> {
  try {
    return { trips: await api.listTrips(), error: null };
  } catch {
    return {
      trips: [],
      error:
        "Can't reach the Nomad API. Start the backend with `uvicorn app.main:app --reload` in ./backend.",
    };
  }
}

export default async function TripsPage() {
  const { trips, error } = await getTrips();

  return (
    <div className="min-h-dvh">
      <SiteHeader />
      <main className="container py-10 sm:py-14">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              My trips
            </h1>
            <p className="mt-2 text-muted-foreground">
              The companion keeps watching every trip here, whether it's open or not.
            </p>
          </div>
          <Button variant="gradient" asChild>
            <Link href="/plan">
              <Plus /> New trip
            </Link>
          </Button>
        </div>

        {error && (
          <Card className="mt-8 border-destructive/30 bg-destructive/[0.04] p-5">
            <p className="text-sm">{error}</p>
          </Card>
        )}

        {!error && trips.length === 0 && (
          <Card className="mt-8 p-10 text-center">
            <p className="font-medium">No trips yet</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Plan one and it'll appear here.
            </p>
            <Button variant="gradient" className="mt-5" asChild>
              <Link href="/plan">
                Plan My Trip <ArrowRight />
              </Link>
            </Button>
          </Card>
        )}

        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {trips.map((trip) => {
            const hue = hashHue(trip.id);
            const nights = Math.max(
              daysBetween(trip.start_date, trip.end_date) - 1,
              1,
            );
            const pct = Math.min((trip.spent / Math.max(trip.budget, 1)) * 100, 100);
            return (
              <Link key={trip.id} href={`/trip/${trip.id}`}>
                <Card className="h-full overflow-hidden" interactive>
                  <div
                    className="relative h-28"
                    style={{
                      backgroundImage: `linear-gradient(135deg, hsl(${hue} 66% 54%), hsl(${(hue + 48) % 360} 60% 42%))`,
                    }}
                  >
                    <div className="absolute inset-x-0 bottom-0 p-4">
                      <Badge className="border-transparent bg-black/30 text-white backdrop-blur">
                        {nights} night{nights === 1 ? "" : "s"}
                      </Badge>
                    </div>
                  </div>

                  <div className="p-5">
                    <h2 className="truncate font-semibold tracking-tight">
                      {trip.title || trip.destination}
                    </h2>
                    <p className="truncate text-sm text-muted-foreground">
                      {trip.destination}
                    </p>

                    <div className="mt-3 space-y-1.5 text-xs text-muted-foreground">
                      <p className="flex items-center gap-1.5">
                        <CalendarDays className="size-3.5" />
                        {formatDate(trip.start_date)} — {formatDate(trip.end_date)}
                      </p>
                      <p className="flex items-center gap-1.5">
                        <Users className="size-3.5" />
                        {trip.travelers}{" "}
                        {trip.travelers === 1 ? "traveller" : "travellers"}
                      </p>
                      <p className="flex items-center gap-1.5">
                        <Wallet className="size-3.5" />
                        {money(trip.spent, "USD")} of {money(trip.budget, "USD")} spent
                      </p>
                    </div>

                    <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-secondary">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                </Card>
              </Link>
            );
          })}
        </div>
      </main>
    </div>
  );
}

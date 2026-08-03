"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  CalendarDays,
  Check,
  Link2,
  Loader2,
  MapPin,
  RefreshCw,
  Users,
  Wallet,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/controls";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import type { Trip } from "@/lib/types";
import { formatDate, money } from "@/lib/utils";

export function TripHeader({
  trip,
  onTripChange,
}: {
  trip: Trip;
  onTripChange: (t: Trip) => void;
}) {
  const router = useRouter();
  const { toast } = useToast();
  const [copied, setCopied] = React.useState(false);
  const [regenerating, setRegenerating] = React.useState(false);

  const spent = trip.expenses.reduce((sum, e) => sum + e.amount, 0);
  const pct = Math.min((spent / Math.max(trip.preferences.budget, 1)) * 100, 100);
  const { currency } = trip.preferences;

  async function share() {
    try {
      const { path } = await api.getShareLink(trip.id);
      const url = `${window.location.origin}${path}`;
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2200);
      toast({
        title: "Share link copied",
        description: "Anyone with the link can view this itinerary, read-only.",
        tone: "success",
      });
    } catch {
      toast({ title: "Couldn't copy the link", tone: "error" });
    }
  }

  async function regenerate() {
    setRegenerating(true);
    try {
      const fresh = await api.regenerateTrip(trip.id);
      onTripChange(fresh);
      toast({
        title: "Itinerary rebuilt",
        description: "Same preferences, fresh plan. Your expenses were kept.",
        tone: "success",
      });
      router.refresh();
    } catch {
      toast({ title: "Couldn't rebuild the itinerary", tone: "error" });
    } finally {
      setRegenerating(false);
    }
  }

  return (
    <section className="aurora relative overflow-hidden border-b border-border/60">
      <div className="grid-lines pointer-events-none absolute inset-0 opacity-25" />
      <div className="container relative py-8">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="min-w-0">
            <Badge variant="outline" className="mb-3 gap-1.5 bg-background/60">
              <MapPin className="size-3" />
              {trip.preferences.destination}
            </Badge>
            <h1 className="text-balance text-3xl font-semibold tracking-tight sm:text-4xl">
              {trip.title}
            </h1>
            <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-sm text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <CalendarDays className="size-4" />
                {formatDate(trip.preferences.start_date)} —{" "}
                {formatDate(trip.preferences.end_date)}
              </span>
              <span className="flex items-center gap-1.5">
                <Users className="size-4" />
                {trip.preferences.travelers}{" "}
                {trip.preferences.travelers === 1 ? "traveller" : "travellers"}
              </span>
              <span className="flex items-center gap-1.5">
                <Wallet className="size-4" />
                {money(spent, currency)} of {money(trip.preferences.budget, currency)}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={share}>
              {copied ? <Check /> : <Link2 />}
              <span className="hidden sm:inline">{copied ? "Copied" : "Share"}</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={regenerate}
              disabled={regenerating}
            >
              {regenerating ? <Loader2 className="animate-spin" /> : <RefreshCw />}
              <span className="hidden sm:inline">Rebuild</span>
            </Button>
          </div>
        </div>

        <div className="mt-6 max-w-md">
          <div className="mb-1.5 flex items-center justify-between text-xs text-muted-foreground">
            <span>Budget used</span>
            <span className="tabular-nums">{Math.round(pct)}%</span>
          </div>
          <Progress
            value={pct}
            indicatorClassName={
              pct > 90
                ? "bg-gradient-to-r from-orange-500 to-destructive"
                : undefined
            }
          />
        </div>
      </div>
    </section>
  );
}

"use client";

import * as React from "react";
import {
  AlertTriangle,
  Droplets,
  Home,
  Info,
  Loader2,
  RefreshCw,
  Sunrise,
  Sunset,
  Wind,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import { WEATHER_ICON, WEATHER_TINT } from "@/lib/place-visual";
import type { Trip } from "@/lib/types";
import { cn, formatDate, isToday } from "@/lib/utils";

export function WeatherPanel({
  trip,
  onTripChange,
}: {
  trip: Trip;
  onTripChange: (t: Trip) => void;
}) {
  const { toast } = useToast();
  const [refreshing, setRefreshing] = React.useState(false);

  async function refresh() {
    setRefreshing(true);
    try {
      const fresh = await api.refreshWeather(trip.id);
      onTripChange(fresh);
      toast({
        title: "Forecast refreshed",
        description: "The companion re-checked your plan against it.",
        tone: "success",
      });
    } catch {
      toast({ title: "Couldn't refresh the forecast", tone: "error" });
    } finally {
      setRefreshing(false);
    }
  }

  const indoorByDate = React.useMemo(() => {
    const map: Record<string, { indoor: number; total: number }> = {};
    for (const day of trip.days) {
      const stops = day.activities.filter((a) => !a.is_meal);
      map[day.date] = {
        indoor: stops.filter((a) => a.place.indoor).length,
        total: stops.length,
      };
    }
    return map;
  }, [trip.days]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Forecast</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            The companion plans against this — indoor stops appear automatically on wet
            days.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={refresh} disabled={refreshing}>
          {refreshing ? <Loader2 className="animate-spin" /> : <RefreshCw />}
          Refresh
        </Button>
      </div>

      {/* warnings */}
      {trip.weather_alerts.length > 0 && (
        <div className="space-y-2.5">
          {trip.weather_alerts.map((alert) => (
            <Card
              key={alert.id}
              className={cn(
                "flex items-start gap-3 p-4",
                alert.severity === "severe" && "border-destructive/30 bg-destructive/[0.04]",
                alert.severity === "warning" &&
                  "border-[hsl(var(--warning))]/30 bg-[hsl(var(--warning))]/[0.05]",
              )}
            >
              {alert.severity === "info" ? (
                <Info className="mt-0.5 size-4 shrink-0 text-primary" />
              ) : (
                <AlertTriangle
                  className={cn(
                    "mt-0.5 size-4 shrink-0",
                    alert.severity === "severe"
                      ? "text-destructive"
                      : "text-[hsl(var(--warning))]",
                  )}
                />
              )}
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold">{alert.title}</p>
                  <Badge variant="outline">{formatDate(alert.date)}</Badge>
                  {alert.recommend_indoor && (
                    <Badge variant="secondary">
                      <Home /> Indoor recommended
                    </Badge>
                  )}
                </div>
                <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                  {alert.message}
                </p>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* daily cards */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {trip.weather.map((w) => {
          const Icon = WEATHER_ICON[w.condition];
          const coverage = indoorByDate[w.date];
          const day = trip.days.find((d) => d.date === w.date);
          return (
            <Card
              key={w.date}
              className={cn(
                "relative overflow-hidden p-5",
                isToday(w.date) && "border-primary/40",
              )}
            >
              <div
                className={cn(
                  "pointer-events-none absolute inset-0 bg-gradient-to-br",
                  WEATHER_TINT[w.condition],
                )}
              />
              <div className="relative">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs text-muted-foreground">
                      Day {day?.day_number ?? "—"}
                      {isToday(w.date) && (
                        <span className="ml-1.5 font-medium text-primary">Today</span>
                      )}
                    </p>
                    <p className="text-sm font-medium">{formatDate(w.date)}</p>
                  </div>
                  <Icon className="size-8 text-primary" />
                </div>

                <p className="mt-3 text-3xl font-semibold tabular-nums">
                  {Math.round(w.temp_max_c)}°
                  <span className="ml-1.5 text-lg font-normal text-muted-foreground">
                    {Math.round(w.temp_min_c)}°
                  </span>
                </p>
                <p className="text-sm text-muted-foreground">{w.description}</p>

                <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1.5">
                    <Droplets className="size-3.5" />
                    {w.precipitation_chance}% rain
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Wind className="size-3.5" />
                    {Math.round(w.wind_kph)} km/h
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Sunrise className="size-3.5" />
                    {w.sunrise}
                  </span>
                  <span className="flex items-center gap-1.5">
                    <Sunset className="size-3.5" />
                    {w.sunset}
                  </span>
                </div>

                {coverage && coverage.total > 0 && (
                  <p className="mt-4 border-t border-border pt-3 text-xs text-muted-foreground">
                    <span className="font-medium text-foreground">
                      {coverage.indoor} of {coverage.total}
                    </span>{" "}
                    stops that day are indoors
                  </p>
                )}
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

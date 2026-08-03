"use client";

import { Bed, Bus, Ticket, UtensilsCrossed } from "lucide-react";

import { Card } from "@/components/ui/card";
import type { Trip } from "@/lib/types";
import { cn, money } from "@/lib/utils";

const ROWS = [
  { key: "accommodation", label: "Accommodation", icon: Bed, color: "bg-violet-500" },
  { key: "food", label: "Food", icon: UtensilsCrossed, color: "bg-orange-500" },
  { key: "transport", label: "Transport", icon: Bus, color: "bg-sky-500" },
  { key: "activities", label: "Activities", icon: Ticket, color: "bg-emerald-500" },
] as const;

export function BudgetBreakdownCard({
  trip,
  className,
}: {
  trip: Trip;
  className?: string;
}) {
  const b = trip.budget_breakdown;
  const total = b.accommodation + b.food + b.transport + b.activities;
  const { currency, budget } = trip.preferences;
  const over = total > budget;

  return (
    <Card className={cn("p-5", className)}>
      <div className="flex items-baseline justify-between">
        <h3 className="text-sm font-semibold">Planned budget</h3>
        <span className="text-xs text-muted-foreground">
          of {money(budget, currency)}
        </span>
      </div>

      <p className="mt-2 text-2xl font-semibold tabular-nums">
        {money(total, currency)}
      </p>
      <p className={cn("text-xs", over ? "text-destructive" : "text-muted-foreground")}>
        {over
          ? `${money(total - budget, currency)} above your budget`
          : `${money(budget - total, currency)} of headroom`}
      </p>

      {/* stacked bar */}
      <div className="mt-4 flex h-2.5 overflow-hidden rounded-full bg-secondary">
        {ROWS.map((row) => {
          const value = b[row.key];
          const pct = total > 0 ? (value / total) * 100 : 0;
          if (pct <= 0) return null;
          return (
            <div
              key={row.key}
              className={row.color}
              style={{ width: `${pct}%` }}
              title={`${row.label}: ${money(value, currency)}`}
            />
          );
        })}
      </div>

      <ul className="mt-4 space-y-2.5">
        {ROWS.map((row) => {
          const value = b[row.key];
          const pct = total > 0 ? Math.round((value / total) * 100) : 0;
          return (
            <li key={row.key} className="flex items-center gap-2.5 text-sm">
              <span className={cn("size-2 shrink-0 rounded-full", row.color)} />
              <row.icon className="size-3.5 shrink-0 text-muted-foreground" />
              <span className="flex-1 truncate">{row.label}</span>
              <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
                {pct}%
              </span>
              <span className="w-16 shrink-0 text-right font-medium tabular-nums">
                {money(value, currency)}
              </span>
            </li>
          );
        })}
      </ul>

      <p className="mt-4 text-xs leading-relaxed text-muted-foreground">
        Accommodation is estimated from local nightly rates; everything else comes
        from the stops actually on your plan.
      </p>
    </Card>
  );
}

"use client";

import * as React from "react";
import {
  BatteryCharging,
  CloudRain,
  HeartPulse,
  Loader2,
  Mountain,
  RefreshCw,
  Shirt,
  ShieldCheck,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Checkbox, Progress } from "@/components/ui/controls";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import type { PackingItem, Trip } from "@/lib/types";
import { cn } from "@/lib/utils";

const GROUPS = [
  { key: "essentials", label: "Essentials", icon: ShieldCheck },
  { key: "clothing", label: "Clothing", icon: Shirt },
  { key: "weather", label: "For the forecast", icon: CloudRain },
  { key: "activity", label: "For your activities", icon: Mountain },
  { key: "electronics", label: "Electronics", icon: BatteryCharging },
  { key: "health", label: "Health", icon: HeartPulse },
] as const;

export function PackingPanel({
  trip,
  onTripChange,
}: {
  trip: Trip;
  onTripChange: (t: Trip) => void;
}) {
  const { toast } = useToast();
  const [pending, setPending] = React.useState<string[]>([]);
  const [regenerating, setRegenerating] = React.useState(false);

  const packed = trip.packing_list.filter((i) => i.packed).length;
  const total = trip.packing_list.length;
  const pct = total ? (packed / total) * 100 : 0;

  async function toggle(item: PackingItem) {
    setPending((p) => [...p, item.id]);
    try {
      const fresh = await api.togglePacking(trip.id, item.id, !item.packed);
      onTripChange(fresh);
    } catch {
      toast({ title: "Couldn't update that item", tone: "error" });
    } finally {
      setPending((p) => p.filter((id) => id !== item.id));
    }
  }

  async function regenerate() {
    setRegenerating(true);
    try {
      const fresh = await api.regeneratePacking(trip.id);
      onTripChange(fresh);
      toast({
        title: "Packing list rebuilt",
        description: "Re-derived from the current forecast and plan. Ticks were kept.",
        tone: "success",
      });
    } catch {
      toast({ title: "Couldn't rebuild the list", tone: "error" });
    } finally {
      setRegenerating(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Packing list</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Built from your forecast, your activities and {trip.country}'s local
            quirks — not a generic checklist.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={regenerate} disabled={regenerating}>
          {regenerating ? <Loader2 className="animate-spin" /> : <RefreshCw />}
          Rebuild
        </Button>
      </div>

      <Card className="p-5">
        <div className="mb-2 flex items-baseline justify-between">
          <span className="text-sm font-medium">
            {packed} of {total} packed
          </span>
          <span className="text-sm text-muted-foreground tabular-nums">
            {Math.round(pct)}%
          </span>
        </div>
        <Progress value={pct} />
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        {GROUPS.map((group) => {
          const items = trip.packing_list.filter((i) => i.category === group.key);
          if (!items.length) return null;
          return (
            <Card key={group.key} className="p-5">
              <div className="flex items-center gap-2">
                <group.icon className="size-4 text-primary" />
                <h3 className="text-sm font-semibold">{group.label}</h3>
                <Badge variant="secondary" className="ml-auto">
                  {items.filter((i) => i.packed).length}/{items.length}
                </Badge>
              </div>

              <ul className="mt-3 space-y-1">
                {items.map((item) => (
                  <li key={item.id}>
                    <label
                      className={cn(
                        "flex cursor-pointer items-start gap-3 rounded-lg p-2 transition-colors hover:bg-secondary/60",
                        pending.includes(item.id) && "opacity-50",
                      )}
                    >
                      <Checkbox
                        checked={item.packed}
                        onCheckedChange={() => toggle(item)}
                        disabled={pending.includes(item.id)}
                        className="mt-0.5"
                      />
                      <span className="min-w-0 flex-1">
                        <span
                          className={cn(
                            "flex flex-wrap items-center gap-1.5 text-sm",
                            item.packed && "text-muted-foreground line-through",
                          )}
                        >
                          {item.label}
                          {item.essential && (
                            <Badge variant="destructive">Essential</Badge>
                          )}
                        </span>
                        {item.reason && (
                          <span className="mt-0.5 block text-xs text-muted-foreground">
                            {item.reason}
                          </span>
                        )}
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

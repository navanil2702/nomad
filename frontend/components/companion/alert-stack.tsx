"use client";

import * as React from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertTriangle,
  CalendarClock,
  Check,
  CloudRain,
  Footprints,
  Loader2,
  Radar,
  Undo2,
  Wallet,
  X,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { useToast } from "@/components/ui/toast";
import { ChangeDiff } from "@/components/companion/change-diff";
import { api } from "@/lib/api";
import type { ItineraryChange, ProactiveAlert, Trip } from "@/lib/types";
import { cn } from "@/lib/utils";

const TRIGGER_ICON = {
  weather: CloudRain,
  budget: Wallet,
  pace: Footprints,
  closing: CalendarClock,
  arrival: Radar,
} as const;

/**
 * Proactive notifications.
 *
 * Weather swaps arrive already applied — the companion acted rather than asked,
 * which is the whole point — so those get an Undo. Suggestions that need a
 * judgement call get Apply.
 */
export function AlertStack({
  trip,
  onTripChange,
  onHighlight,
}: {
  trip: Trip;
  onTripChange: (t: Trip) => void;
  onHighlight: (changes: ItineraryChange[]) => void;
}) {
  const { toast } = useToast();
  const [busy, setBusy] = React.useState<string | null>(null);
  const [expanded, setExpanded] = React.useState<string | null>(null);
  const announced = React.useRef(new Set<string>());

  const alerts = trip.alerts.filter((a) => !a.dismissed);

  // Surface newly auto-applied changes as a toast the first time they appear.
  React.useEffect(() => {
    for (const alert of alerts) {
      if (!alert.applied || announced.current.has(alert.id)) continue;
      announced.current.add(alert.id);
      toast({
        title: alert.title,
        description: alert.message,
        tone: alert.severity === "severe" ? "error" : "warning",
      });
    }
  }, [alerts, toast]);

  async function act(alert: ProactiveAlert, action: "apply" | "undo" | "dismiss") {
    setBusy(alert.id);
    try {
      const fn =
        action === "apply"
          ? api.applyAlert
          : action === "undo"
            ? api.undoAlert
            : api.dismissAlert;
      const { trip: fresh, alert: updated } = await fn(trip.id, alert.id);
      onTripChange(fresh);
      if (action === "apply") {
        onHighlight(updated.changes);
        toast({
          title: "Applied",
          description: `${updated.changes.length} change${updated.changes.length === 1 ? "" : "s"} made to your itinerary.`,
          tone: "success",
        });
      }
      if (action === "undo") {
        toast({ title: "Reverted", description: "Your original plan is back.", tone: "info" });
      }
    } catch {
      toast({ title: "That didn't go through", tone: "error" });
    } finally {
      setBusy(null);
    }
  }

  if (!alerts.length) {
    return (
      <div className="mt-6 flex items-center gap-2.5 rounded-2xl border border-dashed border-border px-4 py-3 text-sm text-muted-foreground">
        <span className="relative flex size-2">
          <span className="absolute inline-flex size-full animate-pulse-ring rounded-full bg-[hsl(var(--success))]" />
          <span className="relative inline-flex size-2 rounded-full bg-[hsl(var(--success))]" />
        </span>
        Companion is watching this trip. Nothing needs your attention right now.
      </div>
    );
  }

  return (
    <div className="mt-6 space-y-3">
      <AnimatePresence initial={false}>
        {alerts.map((alert) => {
          const Icon = TRIGGER_ICON[alert.trigger];
          const isOpen = expanded === alert.id;
          return (
            <motion.div
              key={alert.id}
              layout
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, height: 0, marginBottom: 0 }}
              transition={{ duration: 0.25 }}
            >
              <Card
                className={cn(
                  "overflow-hidden",
                  alert.severity === "severe" &&
                    "border-destructive/35 bg-destructive/[0.035]",
                  alert.severity === "warning" &&
                    "border-[hsl(var(--warning))]/35 bg-[hsl(var(--warning))]/[0.045]",
                  alert.applied && "border-primary/35 bg-primary/[0.035]",
                )}
              >
                <div className="flex items-start gap-3.5 p-4">
                  <span
                    className={cn(
                      "grid size-10 shrink-0 place-items-center rounded-xl",
                      alert.severity === "severe"
                        ? "bg-destructive/12 text-destructive"
                        : alert.applied
                          ? "bg-primary/12 text-primary"
                          : "bg-[hsl(var(--warning))]/15 text-[hsl(var(--warning))]",
                    )}
                  >
                    <Icon className="size-5" />
                  </span>

                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-semibold">{alert.title}</p>
                      {alert.applied ? (
                        <Badge variant="success">
                          <Check /> Already handled
                        </Badge>
                      ) : (
                        <Badge variant="warning">
                          <AlertTriangle /> Needs a decision
                        </Badge>
                      )}
                      {alert.day_number && (
                        <Badge variant="outline">Day {alert.day_number}</Badge>
                      )}
                    </div>

                    <p className="mt-1.5 text-[15px] leading-relaxed">{alert.message}</p>

                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      {alert.applied ? (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => void act(alert, "undo")}
                            disabled={busy === alert.id}
                          >
                            {busy === alert.id ? (
                              <Loader2 className="animate-spin" />
                            ) : (
                              <Undo2 />
                            )}
                            Undo
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => void act(alert, "dismiss")}
                            disabled={busy === alert.id}
                          >
                            Keep it
                          </Button>
                        </>
                      ) : (
                        <>
                          <Button
                            variant="gradient"
                            size="sm"
                            onClick={() => void act(alert, "apply")}
                            disabled={busy === alert.id}
                          >
                            {busy === alert.id ? (
                              <Loader2 className="animate-spin" />
                            ) : (
                              <Check />
                            )}
                            Do it
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => void act(alert, "dismiss")}
                            disabled={busy === alert.id}
                          >
                            Not now
                          </Button>
                        </>
                      )}

                      {alert.changes.length > 0 && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setExpanded(isOpen ? null : alert.id)}
                        >
                          {isOpen ? "Hide" : `Show ${alert.changes.length} change${alert.changes.length === 1 ? "" : "s"}`}
                        </Button>
                      )}
                    </div>
                  </div>

                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className="shrink-0 text-muted-foreground"
                    onClick={() => void act(alert, "dismiss")}
                    aria-label="Dismiss"
                  >
                    <X />
                  </Button>
                </div>

                <AnimatePresence>
                  {isOpen && alert.changes.length > 0 && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="border-t border-border p-4">
                        <ChangeDiff changes={alert.changes} />
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </Card>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}

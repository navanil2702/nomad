"use client";

import { motion } from "framer-motion";
import {
  ArrowRight,
  CalendarClock,
  Minus,
  Plus,
  Repeat,
  TrendingDown,
} from "lucide-react";

import type { ItineraryChange } from "@/lib/types";
import { cn } from "@/lib/utils";

const KIND_META: Record<
  ItineraryChange["kind"],
  { icon: typeof Plus; tint: string; label: string }
> = {
  replaced: { icon: Repeat, tint: "text-sky-500", label: "Swapped" },
  moved: { icon: CalendarClock, tint: "text-violet-500", label: "Moved" },
  removed: { icon: Minus, tint: "text-rose-500", label: "Removed" },
  added: { icon: Plus, tint: "text-emerald-500", label: "Added" },
  reordered: { icon: ArrowRight, tint: "text-amber-500", label: "Reordered" },
  downgraded: { icon: TrendingDown, tint: "text-emerald-500", label: "Cheaper" },
  noted: { icon: ArrowRight, tint: "text-muted-foreground", label: "Note" },
};

/** The receipt for what the companion actually did. */
export function ChangeDiff({
  changes,
  className,
}: {
  changes: ItineraryChange[];
  className?: string;
}) {
  if (!changes.length) return null;

  return (
    <div className={cn("space-y-1.5", className)}>
      {changes.map((change, i) => {
        const meta = KIND_META[change.kind];
        const Icon = meta.icon;
        return (
          <motion.div
            key={change.id}
            initial={{ opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.07 }}
            className="flex items-start gap-2 rounded-lg border border-border bg-background/60 px-2.5 py-2 text-xs"
          >
            <Icon className={cn("mt-px size-3.5 shrink-0", meta.tint)} />
            <div className="min-w-0 flex-1">
              <span className="font-medium">{meta.label}</span>
              <span className="text-muted-foreground"> · Day {change.day_number}</span>
              <p className="mt-0.5 leading-snug text-muted-foreground">
                {change.summary}
              </p>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

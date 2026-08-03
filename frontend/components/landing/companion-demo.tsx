"use client";

import * as React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, CloudRain, Sparkles, Wallet } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/**
 * A scripted loop of the companion doing its job. It is a demonstration, not a
 * live session -- the real thing lives on the trip page.
 */
const SCENES = [
  {
    icon: CloudRain,
    tone: "text-sky-500",
    trigger: "Rain forecast detected — nobody asked",
    message:
      "Heavy rain tomorrow from 2 PM. I've swapped your beach afternoon for the Picasso Museum and moved the beach to Friday morning, which is clear.",
    diff: [
      { before: "Barceloneta Beach", after: "Picasso Museum", day: "Thu 2 PM" },
      { before: "Thursday", after: "Friday morning", day: "Beach moved" },
    ],
  },
  {
    icon: Sparkles,
    tone: "text-accent",
    trigger: "You said: “I'm tired”",
    message:
      "Cutting the mileage. Park Güell moves to Saturday and I've put a proper sit-down at Nomad Coffee into your afternoon, with wider gaps between stops.",
    diff: [
      { before: "Park Güell", after: "Saturday", day: "Moved" },
      { before: "—", after: "Nomad Coffee Lab", day: "Added 3:40 PM" },
    ],
  },
  {
    icon: Wallet,
    tone: "text-emerald-500",
    trigger: "You said: “I spent more than expected”",
    message:
      "Trimmed €78 out of the next three days. Dinner moves from Quimet & Quimet to La Cova Fumada, and Tibidabo becomes the free Bunkers viewpoint.",
    diff: [
      { before: "Quimet & Quimet", after: "La Cova Fumada", day: "Saves €22" },
      { before: "Tibidabo", after: "Bunkers del Carmel", day: "Saves €56" },
    ],
  },
];

export function CompanionDemo({ className }: { className?: string }) {
  const [index, setIndex] = React.useState(0);

  React.useEffect(() => {
    const id = setInterval(() => setIndex((i) => (i + 1) % SCENES.length), 6000);
    return () => clearInterval(id);
  }, []);

  const scene = SCENES[index];
  const Icon = scene.icon;

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-3xl border border-border bg-card p-5 shadow-xl sm:p-6",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <Badge variant="outline" className="gap-1.5">
          <span className="relative flex size-1.5">
            <span className="absolute inline-flex size-full animate-pulse-ring rounded-full bg-[hsl(var(--success))]" />
            <span className="relative inline-flex size-1.5 rounded-full bg-[hsl(var(--success))]" />
          </span>
          Companion active
        </Badge>
        <div className="flex gap-1">
          {SCENES.map((_, i) => (
            <button
              key={i}
              onClick={() => setIndex(i)}
              aria-label={`Show example ${i + 1}`}
              className={cn(
                "h-1.5 rounded-full transition-all",
                i === index ? "w-5 bg-primary" : "w-1.5 bg-border hover:bg-primary/40",
              )}
            />
          ))}
        </div>
      </div>

      {/* Deliberately not `mode="wait"` — if an exit animation stalls, the
          carousel would be left showing nothing at all. */}
      <AnimatePresence initial={false}>
        <motion.div
          key={index}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
          className="mt-4"
        >
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {scene.trigger}
          </p>

          <div className="mt-3 flex gap-3">
            <span
              className={cn(
                "grid size-9 shrink-0 place-items-center rounded-xl bg-secondary",
                scene.tone,
              )}
            >
              <Icon className="size-4.5" />
            </span>
            <p className="text-[15px] leading-relaxed">{scene.message}</p>
          </div>

          <div className="mt-4 space-y-1.5">
            {scene.diff.map((row, i) => (
              <motion.div
                key={`${index}-${i}`}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.15 + i * 0.12 }}
                className="flex items-center gap-2 rounded-xl bg-secondary/70 px-3 py-2 text-xs"
              >
                <span className="text-muted-foreground line-through">{row.before}</span>
                <ArrowRight className="size-3 shrink-0 text-muted-foreground" />
                <span className="font-medium">{row.after}</span>
                <span className="ml-auto shrink-0 text-muted-foreground">{row.day}</span>
              </motion.div>
            ))}
          </div>
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

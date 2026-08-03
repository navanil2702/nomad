"use client";

import * as React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Activity, ChevronDown } from "lucide-react";

import { Card } from "@/components/ui/card";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface ProviderInfo {
  configured: boolean;
  mode: string;
  fallback?: string;
  model?: string | null;
  last_error?: string | null;
}

const LABELS: Record<string, string> = {
  ai: "AI",
  weather: "Weather",
  places: "Places",
  database: "Database",
};

/**
 * Which providers are actually live right now.
 *
 * Falling back silently is the failure mode that matters here: mock weather
 * looks exactly like real weather. This makes the distinction visible instead
 * of leaving it in a log nobody reads.
 */
export function ProviderBadge() {
  const [providers, setProviders] = React.useState<Record<string, ProviderInfo> | null>(
    null,
  );
  const [open, setOpen] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    const load = () =>
      api
        .providers()
        .then((r) => !cancelled && setProviders(r.providers))
        .catch(() => !cancelled && setProviders(null));
    load();
    const id = setInterval(load, 60_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  if (!providers) return null;

  const entries = Object.entries(providers);
  const live = entries.filter(([, p]) => p.mode === "live").length;
  const degraded = entries.filter(([, p]) => p.mode === "fallback");

  const tone =
    degraded.length > 0
      ? "text-[hsl(var(--warning))]"
      : live === entries.length
        ? "text-[hsl(var(--success))]"
        : "text-muted-foreground";

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-xs transition-colors hover:bg-secondary"
        aria-expanded={open}
      >
        <Activity className={cn("size-3", tone)} />
        <span className="hidden sm:inline">
          {degraded.length > 0
            ? `${degraded.length} degraded`
            : `${live}/${entries.length} live`}
        </span>
        <ChevronDown
          className={cn("size-3 transition-transform", open && "rotate-180")}
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            className="absolute right-0 top-full z-50 mt-2 w-72"
          >
            <Card className="p-3 shadow-xl">
              <p className="px-1 pb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Data sources
              </p>
              <ul className="space-y-1.5">
                {entries.map(([name, p]) => (
                  <li key={name} className="rounded-lg px-1 py-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          "size-1.5 shrink-0 rounded-full",
                          p.mode === "live" && "bg-[hsl(var(--success))]",
                          p.mode === "fallback" && "bg-[hsl(var(--warning))]",
                          p.mode === "offline" && "bg-muted-foreground/40",
                        )}
                      />
                      <span className="flex-1 text-sm">{LABELS[name] ?? name}</span>
                      <span
                        className={cn(
                          "text-xs",
                          p.mode === "live"
                            ? "text-[hsl(var(--success))]"
                            : "text-muted-foreground",
                        )}
                      >
                        {p.mode === "live"
                          ? p.model ?? "live"
                          : p.mode === "fallback"
                            ? "fell back"
                            : p.mode === "ready"
                              ? "configured"
                              : "offline engine"}
                      </span>
                    </div>
                    {p.mode !== "live" && p.fallback && (
                      <p className="mt-0.5 pl-3.5 text-[11px] leading-snug text-muted-foreground">
                        {p.fallback}
                      </p>
                    )}
                    {p.mode === "fallback" && p.last_error && (
                      <p className="mt-0.5 pl-3.5 text-[11px] leading-snug text-[hsl(var(--warning))]">
                        {p.last_error}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowLeft,
  ArrowRight,
  CalendarDays,
  Check,
  Loader2,
  MapPin,
  Minus,
  Plus,
  Sparkles,
  Users,
  Wallet,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Slider,
} from "@/components/ui/controls";
import { useToast } from "@/components/ui/toast";
import { api, ApiError } from "@/lib/api";
import type { DestinationOption, Interest, Pace } from "@/lib/types";

import { INTEREST_META, PACE_META } from "@/lib/place-visual";
import { addDaysIso, cn, daysBetween, formatDate, money, todayIso } from "@/lib/utils";

/** A city suggestion, from Google Places or the curated list. */
interface DestinationSuggestion {
  label: string;
  primary: string;
  secondary: string;
  curated?: boolean;
}

const CURRENCIES = ["USD", "EUR", "GBP", "JPY", "INR", "AUD", "CAD", "SGD"];

const STEPS = [
  { id: "where", label: "Where & when" },
  { id: "who", label: "Budget & travellers" },
  { id: "style", label: "Interests & pace" },
] as const;

export function TripForm({ destinations }: { destinations: DestinationOption[] }) {
  const router = useRouter();
  const params = useSearchParams();
  const { toast } = useToast();

  const [step, setStep] = React.useState(0);
  const [submitting, setSubmitting] = React.useState(false);

  const [destination, setDestination] = React.useState(params.get("destination") ?? "");
  const [startDate, setStartDate] = React.useState(addDaysIso(todayIso(), 14));
  const [endDate, setEndDate] = React.useState(addDaysIso(todayIso(), 18));
  const [budget, setBudget] = React.useState(2500);
  const [currency, setCurrency] = React.useState("USD");
  const [travelers, setTravelers] = React.useState(2);
  const [interests, setInterests] = React.useState<Interest[]>(["food", "history"]);
  const [pace, setPace] = React.useState<Pace>("balanced");

  const nights = Math.max(daysBetween(startDate, endDate) - 1, 1);
  const perDay = budget / Math.max(daysBetween(startDate, endDate), 1);

  // --- destination type-ahead ---------------------------------------------
  const [matches, setMatches] = React.useState<DestinationSuggestion[]>([]);
  const [open, setOpen] = React.useState(false);
  const [highlight, setHighlight] = React.useState(-1);
  const [searching, setSearching] = React.useState(false);
  // Set when a suggestion is chosen, so selecting one doesn't immediately
  // trigger a fresh search for the text it just filled in.
  const justPicked = React.useRef(false);
  const boxRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const q = destination.trim();
    if (justPicked.current) {
      justPicked.current = false;
      return;
    }
    if (q.length < 2) {
      setMatches([]);
      setOpen(false);
      return;
    }

    // Autocomplete is billed per request, so wait for a pause in typing.
    let cancelled = false;
    setSearching(true);
    const timer = setTimeout(() => {
      api
        .searchDestinations(q)
        .then((results) => {
          if (cancelled) return;
          setMatches(results);
          setHighlight(-1);
          setOpen(results.length > 0);
        })
        .catch(() => !cancelled && setMatches([]))
        .finally(() => !cancelled && setSearching(false));
    }, 220);

    return () => {
      cancelled = true;
      clearTimeout(timer);
      setSearching(false);
    };
  }, [destination]);

  // Close on an outside click.
  React.useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  function pick(suggestion: DestinationSuggestion) {
    justPicked.current = true;
    setDestination(suggestion.label);
    const curated = destinations.find((d) => d.label === suggestion.label);
    if (curated) setCurrency(curated.currency);
    setOpen(false);
    setHighlight(-1);
  }

  function onDestinationKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open || matches.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlight((h) => (h + 1) % matches.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlight((h) => (h - 1 + matches.length) % matches.length);
    } else if (e.key === "Enter" && highlight >= 0) {
      e.preventDefault();
      pick(matches[highlight]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  const canAdvance = React.useMemo(() => {
    if (step === 0) return destination.trim().length >= 2 && endDate >= startDate;
    if (step === 1) return budget > 0 && travelers >= 1;
    return true;
  }, [step, destination, startDate, endDate, budget, travelers]);

  function toggleInterest(value: Interest) {
    setInterests((prev) =>
      prev.includes(value) ? prev.filter((i) => i !== value) : [...prev, value],
    );
  }

  async function submit() {
    setSubmitting(true);
    try {
      const trip = await api.createTrip({
        destination: destination.trim(),
        start_date: startDate,
        end_date: endDate,
        budget,
        currency,
        travelers,
        interests,
        pace,
      });
      router.push(`/trip/${trip.id}`);
    } catch (err) {
      toast({
        title: "Couldn't build that trip",
        description:
          err instanceof ApiError
            ? err.message
            : "Something went wrong. Please try again.",
        tone: "error",
      });
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-2xl">
      {/* progress */}
      <div className="mb-8 flex items-center gap-2">
        {STEPS.map((s, i) => (
          <React.Fragment key={s.id}>
            <button
              type="button"
              onClick={() => i < step && setStep(i)}
              disabled={i > step}
              className={cn(
                "flex items-center gap-2 rounded-full px-1 text-sm transition-colors",
                i <= step ? "text-foreground" : "text-muted-foreground",
                i < step && "cursor-pointer hover:text-primary",
              )}
            >
              <span
                className={cn(
                  "grid size-7 shrink-0 place-items-center rounded-full border text-xs font-medium transition-colors",
                  i < step && "border-primary bg-primary text-primary-foreground",
                  i === step && "border-primary text-primary",
                  i > step && "border-border",
                )}
              >
                {i < step ? <Check className="size-3.5" strokeWidth={3} /> : i + 1}
              </span>
              <span className="hidden sm:inline">{s.label}</span>
            </button>
            {i < STEPS.length - 1 && (
              <span
                className={cn(
                  "h-px flex-1 transition-colors",
                  i < step ? "bg-primary" : "bg-border",
                )}
              />
            )}
          </React.Fragment>
        ))}
      </div>

      <Card className="overflow-hidden p-6 sm:p-8">
        <AnimatePresence mode="wait">
          {/* ------------------------------------------------ step 1 */}
          {step === 0 && (
            <motion.div
              key="where"
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -16 }}
              transition={{ duration: 0.22 }}
              className="space-y-6"
            >
              <div>
                <h2 className="text-2xl font-semibold tracking-tight">Where to?</h2>
                <p className="mt-1 text-muted-foreground">
                  Any city works. These ones have hand-researched place catalogs.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="destination">Destination</Label>
                <div ref={boxRef} className="relative">
                  <MapPin className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="destination"
                    value={destination}
                    onChange={(e) => setDestination(e.target.value)}
                    onKeyDown={onDestinationKeyDown}
                    onFocus={() => matches.length > 0 && setOpen(true)}
                    placeholder="Start typing a city…"
                    className="pl-10 pr-10"
                    autoComplete="off"
                    role="combobox"
                    aria-expanded={open}
                    aria-autocomplete="list"
                  />
                  {searching && (
                    <Loader2 className="absolute right-3.5 top-1/2 size-4 -translate-y-1/2 animate-spin text-muted-foreground" />
                  )}

                  <AnimatePresence>
                    {open && matches.length > 0 && (
                      <motion.ul
                        initial={{ opacity: 0, y: -4 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -4 }}
                        transition={{ duration: 0.12 }}
                        role="listbox"
                        className="absolute z-50 mt-1.5 w-full overflow-hidden rounded-xl border border-border bg-popover shadow-xl"
                      >
                        {matches.map((s, i) => (
                          <li key={s.label} role="option" aria-selected={i === highlight}>
                            <button
                              type="button"
                              onMouseEnter={() => setHighlight(i)}
                              onClick={() => pick(s)}
                              className={cn(
                                "flex w-full items-center gap-3 px-3.5 py-2.5 text-left transition-colors",
                                i === highlight ? "bg-secondary" : "hover:bg-secondary/60",
                              )}
                            >
                              <MapPin className="size-4 shrink-0 text-muted-foreground" />
                              <span className="min-w-0 flex-1">
                                <span className="block truncate text-sm font-medium">
                                  {s.primary}
                                </span>
                                {s.secondary && (
                                  <span className="block truncate text-xs text-muted-foreground">
                                    {s.secondary}
                                  </span>
                                )}
                              </span>
                              {s.curated && (
                                <Badge variant="default" className="shrink-0">
                                  <Sparkles /> Curated
                                </Badge>
                              )}
                            </button>
                          </li>
                        ))}
                      </motion.ul>
                    )}
                  </AnimatePresence>
                </div>

                <div className="flex flex-wrap gap-2 pt-1">
                  {destinations.slice(0, 6).map((s) => (
                    <button
                      key={s.key}
                      type="button"
                      onClick={() => {
                        justPicked.current = true;
                        setDestination(s.label);
                        setCurrency(s.currency);
                        setOpen(false);
                      }}
                      className="rounded-full border border-border px-3 py-1.5 text-xs transition-colors hover:border-primary/50 hover:bg-primary/5"
                    >
                      {s.name}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="start">Start date</Label>
                  <Input
                    id="start"
                    type="date"
                    value={startDate}
                    min={todayIso()}
                    onChange={(e) => {
                      setStartDate(e.target.value);
                      if (endDate < e.target.value) setEndDate(e.target.value);
                    }}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="end">End date</Label>
                  <Input
                    id="end"
                    type="date"
                    value={endDate}
                    min={startDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                </div>
              </div>

              <div className="flex items-center gap-2 rounded-xl bg-secondary/70 px-4 py-3 text-sm">
                <CalendarDays className="size-4 shrink-0 text-primary" />
                <span>
                  {nights} night{nights === 1 ? "" : "s"} —{" "}
                  {formatDate(startDate)} to {formatDate(endDate)}
                </span>
              </div>
            </motion.div>
          )}

          {/* ------------------------------------------------ step 2 */}
          {step === 1 && (
            <motion.div
              key="who"
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -16 }}
              transition={{ duration: 0.22 }}
              className="space-y-7"
            >
              <div>
                <h2 className="text-2xl font-semibold tracking-tight">
                  What's the budget?
                </h2>
                <p className="mt-1 text-muted-foreground">
                  Total for everyone, across the whole trip. It shapes which places get
                  picked.
                </p>
              </div>

              <div className="space-y-4">
                <div className="flex items-end justify-between gap-4">
                  <Label>Total budget</Label>
                  <div className="flex items-center gap-2">
                    <Select value={currency} onValueChange={setCurrency}>
                      <SelectTrigger className="h-9 w-[92px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {CURRENCIES.map((c) => (
                          <SelectItem key={c} value={c}>
                            {c}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Input
                      type="number"
                      min={100}
                      step={50}
                      value={budget}
                      onChange={(e) => setBudget(Math.max(100, Number(e.target.value)))}
                      className="h-9 w-32 text-right"
                    />
                  </div>
                </div>

                <Slider
                  value={[Math.min(budget, 15000)]}
                  min={200}
                  max={15000}
                  step={100}
                  onValueChange={([v]) => setBudget(v)}
                />

                <div className="flex items-center gap-2 rounded-xl bg-secondary/70 px-4 py-3 text-sm">
                  <Wallet className="size-4 shrink-0 text-primary" />
                  <span>
                    About {money(perDay, currency)} a day for {travelers}{" "}
                    {travelers === 1 ? "person" : "people"}
                  </span>
                </div>
              </div>

              <div className="space-y-3">
                <Label>Travellers</Label>
                <div className="flex items-center gap-4">
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => setTravelers((n) => Math.max(1, n - 1))}
                    aria-label="Fewer travellers"
                  >
                    <Minus />
                  </Button>
                  <div className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-border py-2.5">
                    <Users className="size-4 text-muted-foreground" />
                    <span className="text-lg font-semibold tabular-nums">{travelers}</span>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="icon"
                    onClick={() => setTravelers((n) => Math.min(20, n + 1))}
                    aria-label="More travellers"
                  >
                    <Plus />
                  </Button>
                </div>
              </div>
            </motion.div>
          )}

          {/* ------------------------------------------------ step 3 */}
          {step === 2 && (
            <motion.div
              key="style"
              initial={{ opacity: 0, x: 16 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -16 }}
              transition={{ duration: 0.22 }}
              className="space-y-7"
            >
              <div>
                <h2 className="text-2xl font-semibold tracking-tight">
                  What do you actually enjoy?
                </h2>
                <p className="mt-1 text-muted-foreground">
                  Pick as many as you like. Leave it empty and you'll get the
                  best-rated mix.
                </p>
              </div>

              <div className="grid gap-2.5 sm:grid-cols-2">
                {INTEREST_META.map((item) => {
                  const active = interests.includes(item.value);
                  return (
                    <button
                      key={item.value}
                      type="button"
                      onClick={() => toggleInterest(item.value)}
                      className={cn(
                        "flex items-start gap-3 rounded-xl border p-3.5 text-left transition-all",
                        active
                          ? "border-primary bg-primary/5 shadow-sm"
                          : "border-border hover:border-primary/40 hover:bg-secondary/50",
                      )}
                    >
                      <span
                        className={cn(
                          "grid size-9 shrink-0 place-items-center rounded-lg transition-colors",
                          active
                            ? "bg-primary text-primary-foreground"
                            : "bg-secondary text-muted-foreground",
                        )}
                      >
                        <item.icon className="size-4" />
                      </span>
                      <span className="min-w-0">
                        <span className="block text-sm font-medium">{item.label}</span>
                        <span className="block text-xs text-muted-foreground">
                          {item.blurb}
                        </span>
                      </span>
                    </button>
                  );
                })}
              </div>

              <div className="space-y-3">
                <Label>Travel pace</Label>
                <div className="grid gap-2.5 sm:grid-cols-3">
                  {PACE_META.map((p) => {
                    const active = pace === p.value;
                    return (
                      <button
                        key={p.value}
                        type="button"
                        onClick={() => setPace(p.value)}
                        className={cn(
                          "rounded-xl border p-4 text-left transition-all",
                          active
                            ? "border-primary bg-primary/5 shadow-sm"
                            : "border-border hover:border-primary/40 hover:bg-secondary/50",
                        )}
                      >
                        <p.icon
                          className={cn(
                            "size-5",
                            active ? "text-primary" : "text-muted-foreground",
                          )}
                        />
                        <span className="mt-2.5 block text-sm font-medium">{p.label}</span>
                        <span className="mt-0.5 block text-xs text-muted-foreground">
                          {p.detail}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="rounded-xl border border-dashed border-border p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Summary
                </p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  <Badge variant="secondary">{destination || "Somewhere"}</Badge>
                  <Badge variant="secondary">{nights} nights</Badge>
                  <Badge variant="secondary">
                    {money(budget, currency, true)} budget
                  </Badge>
                  <Badge variant="secondary">
                    {travelers} {travelers === 1 ? "traveller" : "travellers"}
                  </Badge>
                  <Badge variant="secondary">{pace}</Badge>
                  {interests.map((i) => (
                    <Badge key={i}>{i}</Badge>
                  ))}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* navigation */}
        <div className="mt-8 flex items-center justify-between gap-3 border-t border-border pt-6">
          <Button
            variant="ghost"
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            disabled={step === 0 || submitting}
          >
            <ArrowLeft /> Back
          </Button>

          {step < STEPS.length - 1 ? (
            <Button
              variant="gradient"
              onClick={() => setStep((s) => s + 1)}
              disabled={!canAdvance}
            >
              Continue <ArrowRight />
            </Button>
          ) : (
            <Button variant="gradient" onClick={submit} disabled={submitting}>
              {submitting ? (
                <>
                  <Loader2 className="animate-spin" /> Building your trip
                </>
              ) : (
                <>
                  <Sparkles /> Generate itinerary
                </>
              )}
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}

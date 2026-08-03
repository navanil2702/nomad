"use client";

import * as React from "react";
import { motion } from "framer-motion";
import {
  BookHeart,
  Footprints,
  Loader2,
  MapPin,
  PenLine,
  Sparkles,
  Utensils,
  Wallet,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/controls";
import { Textarea } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import { MOOD_META } from "@/lib/place-visual";
import type { Mood, Retrospective, Trip } from "@/lib/types";
import { cn, duration, formatDate, isPast, money } from "@/lib/utils";

export function JournalPanel({
  trip,
  onTripChange,
}: {
  trip: Trip;
  onTripChange: (t: Trip) => void;
}) {
  const { toast } = useToast();
  const [retro, setRetro] = React.useState<Retrospective | null>(null);
  const [loadingRetro, setLoadingRetro] = React.useState(false);
  const [writing, setWriting] = React.useState<number | null>(null);
  const [draftDay, setDraftDay] = React.useState<number | null>(null);
  const [note, setNote] = React.useState("");
  const [mood, setMood] = React.useState<Mood>("happy");

  const finishedDays = trip.days.filter((d) => isPast(d.date) || d.date === trip.preferences.end_date);
  const missing = trip.days.filter(
    (d) => isPast(d.date) && !trip.journal.some((e) => e.day_number === d.day_number),
  );

  async function autowrite() {
    setWriting(-1);
    try {
      const fresh = await api.autowriteJournal(trip.id);
      onTripChange(fresh);
      toast({
        title: "Journal caught up",
        description: "Entries written for every day that has finished.",
        tone: "success",
      });
    } catch {
      toast({ title: "Couldn't write the journal", tone: "error" });
    } finally {
      setWriting(null);
    }
  }

  async function saveDay(dayNumber: number) {
    setWriting(dayNumber);
    try {
      const fresh = await api.writeJournalDay(trip.id, dayNumber, mood, note.trim() || undefined);
      onTripChange(fresh);
      setDraftDay(null);
      setNote("");
      toast({ title: `Day ${dayNumber} saved`, tone: "success" });
    } catch {
      toast({ title: "Couldn't save that entry", tone: "error" });
    } finally {
      setWriting(null);
    }
  }

  async function loadRetro() {
    setLoadingRetro(true);
    try {
      setRetro(await api.retrospective(trip.id));
    } catch {
      toast({ title: "Couldn't build the travel journal", tone: "error" });
    } finally {
      setLoadingRetro(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Memory journal</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Each finished day is written up automatically — where you went, what it
            cost, how it felt.
          </p>
        </div>
        <div className="flex gap-2">
          {missing.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={autowrite}
              disabled={writing === -1}
            >
              {writing === -1 ? <Loader2 className="animate-spin" /> : <Sparkles />}
              Write {missing.length} missing
            </Button>
          )}
          <Button variant="gradient" size="sm" onClick={loadRetro} disabled={loadingRetro}>
            {loadingRetro ? <Loader2 className="animate-spin" /> : <BookHeart />}
            Travel journal
          </Button>
        </div>
      </div>

      {/* the bound retrospective */}
      {retro && (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <Card className="aurora relative overflow-hidden border-primary/25 p-6 sm:p-8">
            <div className="grid-lines pointer-events-none absolute inset-0 opacity-20" />
            <div className="relative">
              <Badge variant="outline" className="bg-background/60">
                <BookHeart /> The whole trip
              </Badge>
              <h3 className="mt-4 font-display text-3xl italic sm:text-4xl">
                {retro.title}
              </h3>
              <p className="mt-4 max-w-2xl text-pretty text-lg leading-relaxed">
                {retro.closing}
              </p>

              <div className="mt-7 grid grid-cols-2 gap-4 sm:grid-cols-4">
                <RetroStat icon={MapPin} value={retro.stats.places} label="places" />
                <RetroStat icon={Utensils} value={retro.stats.meals} label="meals" />
                <RetroStat
                  icon={Wallet}
                  value={money(retro.stats.spend, trip.preferences.currency)}
                  label="spent"
                />
                <RetroStat
                  icon={Footprints}
                  value={duration(retro.stats.travel_minutes)}
                  label="in transit"
                />
              </div>

              {retro.highlights.length > 0 && (
                <div className="mt-7">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    Highlights
                  </p>
                  <div className="mt-2.5 flex flex-wrap gap-2">
                    {retro.highlights.map((h, i) => (
                      <Badge key={i} variant="secondary" className="py-1">
                        {h}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Card>
        </motion.div>
      )}

      {/* per-day entries */}
      {trip.journal.length === 0 ? (
        <Card className="p-8 text-center">
          <BookHeart className="mx-auto size-8 text-muted-foreground" />
          <p className="mt-3 font-medium">Nothing written yet</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Entries appear automatically at the end of each day. You can also write one
            early for any day below.
          </p>
        </Card>
      ) : (
        <div className="space-y-4">
          {trip.journal.map((entry, i) => {
            const moodMeta = MOOD_META[entry.mood];
            return (
              <motion.div
                key={entry.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
              >
                <Card className="overflow-hidden">
                  <div className="flex flex-wrap items-start justify-between gap-3 p-5 pb-3">
                    <div>
                      <p className="text-xs text-muted-foreground">
                        Day {entry.day_number} · {formatDate(entry.date)}
                      </p>
                      <h3 className="mt-0.5 font-display text-xl italic">
                        {entry.title}
                      </h3>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary">
                        <span className={moodMeta.tint}>{moodMeta.emoji}</span>
                        {moodMeta.label}
                      </Badge>
                      <Badge variant="outline">
                        {money(entry.spend, trip.preferences.currency)}
                      </Badge>
                    </div>
                  </div>

                  <p className="px-5 text-[15px] leading-relaxed">{entry.summary}</p>

                  {entry.places_visited.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 px-5 pt-3">
                      {entry.places_visited.map((p, j) => (
                        <Badge key={j} variant="secondary">
                          {p}
                        </Badge>
                      ))}
                    </div>
                  )}

                  <div className="mt-4 flex items-center justify-between border-t border-border px-5 py-3">
                    <p className="text-xs text-muted-foreground">
                      {entry.highlights[0] ?? "Written by your companion"}
                    </p>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        setDraftDay(entry.day_number);
                        setMood(entry.mood);
                        setNote("");
                      }}
                    >
                      <PenLine /> Add your own note
                    </Button>
                  </div>

                  {draftDay === entry.day_number && (
                    <div className="border-t border-border bg-secondary/40 p-5">
                      <Textarea
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        placeholder="What do you actually want to remember about today?"
                      />
                      <div className="mt-3 flex flex-wrap items-center gap-2">
                        <Select value={mood} onValueChange={(v) => setMood(v as Mood)}>
                          <SelectTrigger className="h-9 w-40">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {Object.entries(MOOD_META).map(([key, m]) => (
                              <SelectItem key={key} value={key}>
                                {m.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <Button
                          size="sm"
                          onClick={() => saveDay(entry.day_number)}
                          disabled={writing === entry.day_number}
                        >
                          {writing === entry.day_number ? (
                            <Loader2 className="animate-spin" />
                          ) : null}
                          Save
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setDraftDay(null)}
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  )}
                </Card>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* write early */}
      {finishedDays.length < trip.days.length && (
        <Card className="p-5">
          <h3 className="text-sm font-semibold">Write an entry early</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Useful mid-trip, before the details blur.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {trip.days.map((d) => (
              <Button
                key={d.id}
                variant="outline"
                size="sm"
                onClick={() => saveDay(d.day_number)}
                disabled={writing === d.day_number}
              >
                {writing === d.day_number ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <PenLine />
                )}
                Day {d.day_number}
              </Button>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

function RetroStat({
  icon: Icon,
  value,
  label,
}: {
  icon: React.ComponentType<{ className?: string }>;
  value: React.ReactNode;
  label: string;
}) {
  return (
    <div>
      <Icon className="size-4 text-primary" />
      <p className="mt-1.5 text-xl font-semibold tabular-nums">{value}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

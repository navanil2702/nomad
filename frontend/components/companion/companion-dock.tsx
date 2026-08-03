"use client";

import * as React from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Compass, Eraser, Loader2, SendHorizonal, Sparkles, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogTitle, SheetContent } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { ChangeDiff } from "@/components/companion/change-diff";
import { api } from "@/lib/api";
import type { ChatMessage, ItineraryChange, Trip } from "@/lib/types";
import { cn } from "@/lib/utils";

const QUICK_PROMPTS = [
  "It's raining",
  "I'm tired",
  "I'm hungry",
  "My train is delayed",
  "I have two free hours",
  "I want vegetarian food nearby",
  "I spent more than expected",
];

/** The floating companion. Always one tap away, on every tab. */
export function CompanionDock({
  trip,
  onTripChange,
  onHighlight,
}: {
  trip: Trip;
  onTripChange: (t: Trip) => void;
  onHighlight: (changes: ItineraryChange[]) => void;
}) {
  const { toast } = useToast();
  const [open, setOpen] = React.useState(false);
  const [input, setInput] = React.useState("");
  const [sending, setSending] = React.useState(false);
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const messages = trip.messages;

  React.useEffect(() => {
    if (!open) return;
    const id = requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    });
    return () => cancelAnimationFrame(id);
  }, [messages.length, open, sending]);

  async function send(text: string) {
    const message = text.trim();
    if (!message || sending) return;
    setInput("");
    setSending(true);
    try {
      const { message: reply, trip: fresh } = await api.chat(trip.id, message);
      onTripChange(fresh);
      if (reply.changes.length) onHighlight(reply.changes);
    } catch {
      toast({
        title: "The companion didn't respond",
        description: "Check the API is running, then try again.",
        tone: "error",
      });
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }

  async function clear() {
    try {
      onTripChange(await api.clearChat(trip.id));
    } catch {
      toast({ title: "Couldn't clear the conversation", tone: "error" });
    }
  }

  return (
    <>
      {/* floating button */}
      <motion.div
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: 0.4, type: "spring", stiffness: 260, damping: 20 }}
        className="fixed bottom-5 right-5 z-50 sm:bottom-7 sm:right-7"
      >
        <button
          onClick={() => setOpen(true)}
          className="group relative flex items-center gap-2.5 rounded-full bg-gradient-to-br from-primary to-primary/80 py-3 pl-3.5 pr-5 text-primary-foreground shadow-xl shadow-primary/25 transition-all hover:shadow-2xl hover:shadow-primary/35 active:scale-95"
          aria-label="Open your travel companion"
        >
          <span className="absolute -right-0.5 -top-0.5 flex size-3">
            <span className="absolute inline-flex size-full animate-pulse-ring rounded-full bg-accent" />
            <span className="relative inline-flex size-3 rounded-full bg-accent" />
          </span>
          <Compass className="size-5 transition-transform group-hover:rotate-45" />
          <span className="text-sm font-medium">Companion</span>
        </button>
      </motion.div>

      <Dialog open={open} onOpenChange={setOpen}>
        <SheetContent className="gap-0 p-0">
          {/* header */}
          <div className="flex items-start justify-between gap-3 border-b border-border p-5">
            <div className="min-w-0">
              <DialogTitle className="flex items-center gap-2">
                <span className="grid size-7 place-items-center rounded-lg bg-gradient-to-br from-primary to-accent text-primary-foreground">
                  <Compass className="size-4" />
                </span>
                Your companion
              </DialogTitle>
              <p className="mt-1 truncate text-xs text-muted-foreground">
                Knows all {trip.days.length} days in {trip.preferences.destination}
              </p>
            </div>
            <div className="flex shrink-0 gap-1">
              {messages.length > 0 && (
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={clear}
                  aria-label="Clear conversation"
                >
                  <Eraser />
                </Button>
              )}
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => setOpen(false)}
                aria-label="Close"
              >
                <X />
              </Button>
            </div>
          </div>

          {/* transcript */}
          <div ref={scrollRef} className="scrollbar-thin flex-1 overflow-y-auto p-5">
            {messages.length === 0 ? (
              <div className="flex h-full flex-col justify-center">
                <div className="rounded-2xl border border-border bg-secondary/50 p-4">
                  <Sparkles className="size-5 text-primary" />
                  <p className="mt-2.5 text-[15px] leading-relaxed">
                    Tell me what's actually happening and I'll rework the plan — not
                    just talk about it. Every reply comes with the changes I made.
                  </p>
                </div>
                <p className="mt-5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Try one of these
                </p>
                <div className="mt-2.5 flex flex-wrap gap-2">
                  {QUICK_PROMPTS.map((p) => (
                    <button
                      key={p}
                      onClick={() => void send(p)}
                      className="rounded-full border border-border px-3 py-1.5 text-xs transition-colors hover:border-primary/50 hover:bg-primary/5"
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <AnimatePresence initial={false}>
                  {messages.map((m) => (
                    <MessageBubble key={m.id} message={m} />
                  ))}
                </AnimatePresence>
                {sending && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex items-center gap-2 text-sm text-muted-foreground"
                  >
                    <span className="flex gap-1">
                      {[0, 1, 2].map((i) => (
                        <motion.span
                          key={i}
                          className="size-1.5 rounded-full bg-primary"
                          animate={{ opacity: [0.3, 1, 0.3] }}
                          transition={{
                            duration: 1.1,
                            repeat: Infinity,
                            delay: i * 0.18,
                          }}
                        />
                      ))}
                    </span>
                    Reworking your plan…
                  </motion.div>
                )}
              </div>
            )}
          </div>

          {/* composer */}
          <div className="border-t border-border p-4">
            {messages.length > 0 && (
              <div className="scrollbar-thin mb-3 flex gap-2 overflow-x-auto pb-1">
                {QUICK_PROMPTS.map((p) => (
                  <button
                    key={p}
                    onClick={() => void send(p)}
                    disabled={sending}
                    className="shrink-0 rounded-full border border-border px-3 py-1.5 text-xs transition-colors hover:border-primary/50 hover:bg-primary/5 disabled:opacity-50"
                  >
                    {p}
                  </button>
                ))}
              </div>
            )}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void send(input);
              }}
              className="flex gap-2"
            >
              <Input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="What's happening?"
                disabled={sending}
                autoComplete="off"
              />
              <Button
                type="submit"
                variant="gradient"
                size="icon"
                disabled={sending || !input.trim()}
                aria-label="Send"
              >
                {sending ? <Loader2 className="animate-spin" /> : <SendHorizonal />}
              </Button>
            </form>
          </div>
        </SheetContent>
      </Dialog>
    </>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22 }}
      className={cn("flex", isUser ? "justify-end" : "justify-start")}
    >
      <div className={cn("max-w-[88%]", isUser && "items-end")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed",
            isUser
              ? "rounded-br-md bg-primary text-primary-foreground"
              : "rounded-bl-md border border-border bg-secondary/60",
          )}
        >
          {message.content}
        </div>

        {message.changes.length > 0 && (
          <div className="mt-2">
            <div className="mb-1.5 flex items-center gap-1.5">
              <Badge variant="success">
                <Sparkles /> Itinerary updated
              </Badge>
              {message.intent && (
                <span className="text-[11px] text-muted-foreground">
                  detected: {message.intent.replace(/_/g, " ")}
                </span>
              )}
            </div>
            <ChangeDiff changes={message.changes} />
          </div>
        )}
      </div>
    </motion.div>
  );
}

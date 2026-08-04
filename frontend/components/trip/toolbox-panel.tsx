"use client";

import * as React from "react";
import {
  ArrowLeftRight,
  Check,
  Clock,
  Copy,
  Download,
  Languages,
  Loader2,
  Navigation,
  Phone,
  Plug,
  FileText,
  Share2,
  Wallet,
  WifiOff,
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
  Skeleton,
} from "@/components/ui/controls";
import { useToast } from "@/components/ui/toast";
import { api } from "@/lib/api";
import type { LocalInfo, Trip } from "@/lib/types";

export function ToolboxPanel({ trip }: { trip: Trip }) {
  const [info, setInfo] = React.useState<LocalInfo | null>(null);

  React.useEffect(() => {
    api.getLocalInfo(trip.id).then(setInfo).catch(() => setInfo(null));
  }, [trip.id]);

  if (!info) return <Skeleton className="h-96 w-full" />;

  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <PhrasesCard info={info} />
      <EmergencyCard info={info} />
      <CurrencyCard info={info} trip={trip} />
      <TimeZoneCard trip={trip} info={info} />
      <OfflineCard trip={trip} />
      <ShareCard trip={trip} />
    </div>
  );
}

/* ------------------------------------------------------------------ phrases */

function PhrasesCard({ info }: { info: LocalInfo }) {
  const { toast } = useToast();
  return (
    <Card className="p-5">
      <div className="flex items-center gap-2">
        <Languages className="size-4 text-primary" />
        <h3 className="text-sm font-semibold">{info.language} phrases</h3>
        <Badge variant="secondary" className="ml-auto">
          {info.phrases.length}
        </Badge>
      </div>
      <ul className="mt-4 divide-y divide-border">
        {info.phrases.map((p) => (
          <li key={p.english} className="flex items-center gap-3 py-2.5">
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">{p.local}</p>
              <p className="text-xs text-muted-foreground">
                {p.english} · <span className="italic">{p.pronunciation}</span>
              </p>
            </div>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={`Copy ${p.english}`}
              onClick={() => {
                navigator.clipboard.writeText(p.local);
                toast({ title: `Copied “${p.local}”`, tone: "success" });
              }}
            >
              <Copy />
            </Button>
          </li>
        ))}
      </ul>
      <p className="mt-3 flex items-center gap-1.5 text-xs text-muted-foreground">
        <Plug className="size-3.5" />
        {info.plug_type} · {info.tipping}
      </p>
    </Card>
  );
}

/* ---------------------------------------------------------------- emergency */

function EmergencyCard({ info }: { info: LocalInfo }) {
  return (
    <Card className="border-destructive/25 p-5">
      <div className="flex items-center gap-2">
        <Phone className="size-4 text-destructive" />
        <h3 className="text-sm font-semibold">Emergency contacts</h3>
        <Badge variant="outline" className="ml-auto">
          {info.country}
        </Badge>
      </div>
      <ul className="mt-4 space-y-2">
        {info.emergency.map((e) => (
          <li
            key={`${e.label}-${e.number}`}
            className="flex items-center gap-3 rounded-xl border border-border p-3"
          >
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">{e.label}</p>
              {e.note && <p className="text-xs text-muted-foreground">{e.note}</p>}
            </div>
            <a
              href={`tel:${e.number.replace(/\s/g, "")}`}
              className="shrink-0 rounded-lg bg-destructive/10 px-3 py-1.5 text-sm font-semibold tabular-nums text-destructive transition-colors hover:bg-destructive/20"
            >
              {e.number}
            </a>
          </li>
        ))}
      </ul>

      {info.nearby_help.length > 0 && (
        <div className="mt-5 border-t border-border pt-4">
          <div className="flex items-center gap-2">
            <Navigation className="size-3.5 text-primary" />
            <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Nearest help in {info.city}
            </h4>
          </div>
          <div className="mt-2.5 grid gap-1.5 sm:grid-cols-2">
            {info.nearby_help.map((h) => (
              <a
                key={h.label}
                href={h.maps_url}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded-lg border border-border px-3 py-2 transition-colors hover:border-primary/40 hover:bg-secondary/50"
              >
                <span className="block text-sm font-medium">{h.label}</span>
                <span className="block text-xs text-muted-foreground">{h.note}</span>
              </a>
            ))}
          </div>
        </div>
      )}

      <p className="mt-3 text-xs text-muted-foreground">
        Save the numbers before you land — they work without data. The map links
        need a connection.
      </p>
    </Card>
  );
}

/* ----------------------------------------------------------------- currency */

function CurrencyCard({ info, trip }: { info: LocalInfo; trip: Trip }) {
  const [amount, setAmount] = React.useState("100");
  const [base, setBase] = React.useState(trip.preferences.currency);
  const [target, setTarget] = React.useState(info.currency);
  const [result, setResult] = React.useState<{ converted: number; rate: number; target_symbol: string } | null>(null);
  const [rates, setRates] = React.useState<string[]>([]);

  React.useEffect(() => {
    api.rates().then((r) => setRates(Object.keys(r.rates))).catch(() => setRates([]));
  }, []);

  React.useEffect(() => {
    const value = Number(amount);
    if (!value) return setResult(null);
    let cancelled = false;
    api
      .convertCurrency(value, base, target)
      .then((r) => !cancelled && setResult(r))
      .catch(() => !cancelled && setResult(null));
    return () => {
      cancelled = true;
    };
  }, [amount, base, target]);

  return (
    <Card className="p-5">
      <div className="flex items-center gap-2">
        <Wallet className="size-4 text-primary" />
        <h3 className="text-sm font-semibold">Currency converter</h3>
      </div>

      <div className="mt-4 grid grid-cols-[1fr_auto_1fr] items-end gap-2">
        <div className="space-y-1.5">
          <Label htmlFor="fx-amount">Amount</Label>
          <Input
            id="fx-amount"
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
          <Select value={base} onValueChange={setBase}>
            <SelectTrigger className="h-9">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {rates.map((c) => (
                <SelectItem key={c} value={c}>
                  {c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Button
          variant="ghost"
          size="icon"
          className="mb-9"
          aria-label="Swap currencies"
          onClick={() => {
            setBase(target);
            setTarget(base);
          }}
        >
          <ArrowLeftRight />
        </Button>

        <div className="space-y-1.5">
          <Label>Converts to</Label>
          <div className="flex h-11 items-center rounded-xl border border-input bg-secondary/50 px-3.5 text-sm font-semibold tabular-nums">
            {result
              ? `${result.target_symbol}${result.converted.toLocaleString()}`
              : "—"}
          </div>
          <Select value={target} onValueChange={setTarget}>
            <SelectTrigger className="h-9">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {rates.map((c) => (
                <SelectItem key={c} value={c}>
                  {c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <p className="mt-3 text-xs text-muted-foreground">
        {result
          ? `1 ${base} = ${result.rate.toLocaleString()} ${target}. Indicative offline rates.`
          : "Enter an amount to convert."}
      </p>
    </Card>
  );
}

/* ---------------------------------------------------------------- time zone */

function TimeZoneCard({ trip, info }: { trip: Trip; info: LocalInfo }) {
  const [homeOffset, setHomeOffset] = React.useState(
    () => -new Date().getTimezoneOffset() / 60,
  );
  const [now, setNow] = React.useState(() => Date.now());

  React.useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(id);
  }, []);

  // The trip's own catalog carries the destination's real timezone, resolved
  // when it was planned. Asking the API to look it up again by name would
  // re-resolve a bare string with no coordinates — which is how this card came
  // to claim a town in Kerala was ten hours behind India.
  const data = React.useMemo(() => {
    const utcMs = now + new Date().getTimezoneOffset() * 60_000;
    const at = (offsetHours: number) => new Date(utcMs + offsetHours * 3_600_000);
    const fmtTime = (d: Date) =>
      `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;

    const local = at(info.utc_offset_hours);
    const home = at(homeOffset);
    const delta = info.utc_offset_hours - homeOffset;
    const name = trip.preferences.destination.split(",")[0].trim();

    return {
      destination: name,
      timezone: info.timezone,
      local_time: fmtTime(local),
      local_date: local.toLocaleDateString("en-GB", {
        weekday: "short",
        day: "numeric",
        month: "short",
      }),
      home_time: fmtTime(home),
      difference_hours: delta,
      summary: delta
        ? `${name} is ${Math.abs(delta)}h ${delta > 0 ? "ahead of" : "behind"} you`
        : `${name} is in your time zone`,
    };
  }, [now, info.utc_offset_hours, info.timezone, homeOffset, trip.preferences.destination]);

  return (
    <Card className="p-5">
      <div className="flex items-center gap-2">
        <Clock className="size-4 text-primary" />
        <h3 className="text-sm font-semibold">Time zones</h3>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-border p-4">
          <p className="text-xs text-muted-foreground">Where you are</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">
            {data.home_time}
          </p>
          <p className="text-xs text-muted-foreground">UTC{homeOffset >= 0 ? "+" : ""}{homeOffset}</p>
        </div>
        <div className="rounded-xl border border-primary/40 bg-primary/5 p-4">
          <p className="text-xs text-muted-foreground">{data.destination}</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">
            {data.local_time}
          </p>
          <p className="text-xs text-muted-foreground">
            {data.local_date} · {data.timezone}
          </p>
        </div>
      </div>

      <p className="mt-3 text-sm text-muted-foreground">{data.summary}</p>

      <div className="mt-3 space-y-1.5">
        <Label htmlFor="home-offset">Your UTC offset</Label>
        <Input
          id="home-offset"
          type="number"
          step="0.5"
          min={-12}
          max={14}
          value={homeOffset}
          onChange={(e) => setHomeOffset(Number(e.target.value))}
          className="h-9"
        />
      </div>
    </Card>
  );
}

/* ------------------------------------------------------------------ offline */

function OfflineCard({ trip }: { trip: Trip }) {
  const { toast } = useToast();
  const [downloading, setDownloading] = React.useState(false);

  async function download() {
    setDownloading(true);
    try {
      const res = await fetch(api.offlinePdfUrl(trip.id));
      if (!res.ok) throw new Error("pdf");
      const blob = await res.blob();

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `nomad-${trip.preferences.destination.toLowerCase().replace(/\W+/g, "-")}.pdf`;
      a.click();
      URL.revokeObjectURL(url);

      // Cache the JSON alongside it, so the app itself still has the trip if
      // the connection dies — the PDF is for reading, this is for the app.
      api
        .getOffline(trip.id)
        .then((bundle) =>
          localStorage.setItem(`nomad.offline.${trip.id}`, JSON.stringify(bundle)),
        )
        .catch(() => {
          /* the PDF is the deliverable; caching is a bonus */
        });

      toast({
        title: "Itinerary PDF downloaded",
        description: "Print it or keep it on your phone. No signal needed.",
        tone: "success",
      });
    } catch {
      toast({ title: "Couldn't build the PDF", tone: "error" });
    } finally {
      setDownloading(false);
    }
  }

  return (
    <Card className="p-5">
      <div className="flex items-center gap-2">
        <WifiOff className="size-4 text-primary" />
        <h3 className="text-sm font-semibold">Offline itinerary</h3>
      </div>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
        A printable PDF: every stop with its address, coordinates, opening hours
        and tip, plus emergency numbers, phrases and what's still unpacked. Works
        with no signal.
      </p>
      <Button
        variant="outline"
        className="mt-4 w-full"
        onClick={download}
        disabled={downloading}
      >
        {downloading ? <Loader2 className="animate-spin" /> : <FileText />}
        Download PDF itinerary
      </Button>
    </Card>
  );
}

/* -------------------------------------------------------------------- share */

function ShareCard({ trip }: { trip: Trip }) {
  const { toast } = useToast();
  const [copied, setCopied] = React.useState(false);
  const url =
    typeof window !== "undefined"
      ? `${window.location.origin}/shared/${trip.share_token}`
      : "";

  return (
    <Card className="p-5">
      <div className="flex items-center gap-2">
        <Share2 className="size-4 text-primary" />
        <h3 className="text-sm font-semibold">Share with friends</h3>
      </div>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
        A read-only view of the itinerary, map and forecast. Your expenses, journal
        and companion history stay private.
      </p>
      <div className="mt-4 flex gap-2">
        <Input readOnly value={url} className="font-mono text-xs" />
        <Button
          variant="outline"
          size="icon"
          aria-label="Copy share link"
          onClick={() => {
            navigator.clipboard.writeText(url);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
            toast({ title: "Link copied", tone: "success" });
          }}
        >
          {copied ? <Check /> : <Copy />}
        </Button>
      </div>
    </Card>
  );
}

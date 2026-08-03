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
  Phone,
  Plug,
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
      <TimeZoneCard trip={trip} />
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
            key={e.label}
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
      <p className="mt-3 text-xs text-muted-foreground">
        Save these before you land — they work without data.
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

function TimeZoneCard({ trip }: { trip: Trip }) {
  const [homeOffset, setHomeOffset] = React.useState(() => -new Date().getTimezoneOffset() / 60);
  const [data, setData] = React.useState<Awaited<ReturnType<typeof api.timezone>> | null>(null);

  React.useEffect(() => {
    let cancelled = false;
    const load = () =>
      api
        .timezone(trip.preferences.destination, homeOffset)
        .then((d) => !cancelled && setData(d))
        .catch(() => !cancelled && setData(null));
    load();
    const id = setInterval(load, 30_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [trip.preferences.destination, homeOffset]);

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
            {data?.home_time ?? "—"}
          </p>
          <p className="text-xs text-muted-foreground">UTC{homeOffset >= 0 ? "+" : ""}{homeOffset}</p>
        </div>
        <div className="rounded-xl border border-primary/40 bg-primary/5 p-4">
          <p className="text-xs text-muted-foreground">{data?.destination ?? "There"}</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">
            {data?.local_time ?? "—"}
          </p>
          <p className="text-xs text-muted-foreground">{data?.local_date}</p>
        </div>
      </div>

      <p className="mt-3 text-sm text-muted-foreground">{data?.summary}</p>

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
      const bundle = await api.getOffline(trip.id);
      const blob = new Blob([JSON.stringify(bundle, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `nomad-${trip.preferences.destination.toLowerCase().replace(/\W+/g, "-")}.json`;
      a.click();
      URL.revokeObjectURL(url);
      // Also cache it so the trip survives a dead connection.
      localStorage.setItem(`nomad.offline.${trip.id}`, JSON.stringify(bundle));
      toast({
        title: "Offline copy saved",
        description: "Downloaded and cached in this browser.",
        tone: "success",
      });
    } catch {
      toast({ title: "Couldn't build the offline copy", tone: "error" });
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
        Every stop with its address, coordinates, opening hours, tip and Maps link —
        plus emergency numbers, phrases and what's still unpacked. Works with no
        signal.
      </p>
      <Button
        variant="outline"
        className="mt-4 w-full"
        onClick={download}
        disabled={downloading}
      >
        {downloading ? <Loader2 className="animate-spin" /> : <Download />}
        Download offline copy
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

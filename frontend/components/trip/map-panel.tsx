"use client";

import * as React from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Bus,
  Car,
  Clock,
  ExternalLink,
  Footprints,
  Home,
  Loader2,
  MapPin,
  Navigation,
  Star,
  Trees,
  X,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/controls";
import { api } from "@/lib/api";
import { categoryIcon, CATEGORY_LABEL, placeGradient } from "@/lib/place-visual";
import type { MapMarker, MapPayload, NearbyPlace, Trip } from "@/lib/types";
import { cn, duration, formatTime, money } from "@/lib/utils";

const TRAVEL_ICON = { walk: Footprints, transit: Bus, taxi: Car };
const DAY_COLORS = [
  "hsl(168 62% 40%)",
  "hsl(22 85% 55%)",
  "hsl(262 65% 60%)",
  "hsl(200 80% 48%)",
  "hsl(340 68% 56%)",
  "hsl(45 90% 48%)",
  "hsl(150 55% 42%)",
];

/**
 * Offline map.
 *
 * With no Google Maps key there is no tile server, so this projects the
 * itinerary's own coordinates into a styled canvas: equirectangular, scaled to
 * the bounding box of the markers, with the day's route drawn between stops in
 * visit order. Everything the spec asks for on click — hours, rating, photo,
 * travel time — comes from the place record itself.
 */
export function MapPanel({ trip }: { trip: Trip }) {
  const [payload, setPayload] = React.useState<MapPayload | null>(null);
  const [dayFilter, setDayFilter] = React.useState<number | "all">("all");
  const [selected, setSelected] = React.useState<MapMarker | null>(null);
  const [nearby, setNearby] = React.useState<NearbyPlace[] | null>(null);
  const [loadingNearby, setLoadingNearby] = React.useState(false);

  React.useEffect(() => {
    api.getMap(trip.id).then(setPayload).catch(() => setPayload(null));
  }, [trip.id, trip.updated_at]);

  React.useEffect(() => {
    if (!selected) {
      setNearby(null);
      return;
    }
    setLoadingNearby(true);
    api
      .getNearby(trip.id, selected.place.id)
      .then(setNearby)
      .catch(() => setNearby([]))
      .finally(() => setLoadingNearby(false));
  }, [selected, trip.id]);

  const markers = React.useMemo(() => {
    if (!payload) return [];
    return dayFilter === "all"
      ? payload.markers
      : payload.markers.filter((m) => m.days.includes(dayFilter));
  }, [payload, dayFilter]);

  const projection = React.useMemo(() => {
    if (!markers.length) return null;
    const lats = markers.map((m) => m.place.coordinates.lat);
    const lngs = markers.map((m) => m.place.coordinates.lng);
    const pad = 0.12;
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLng = Math.min(...lngs);
    const maxLng = Math.max(...lngs);
    // Guard against a single marker collapsing the span to zero.
    const spanLat = Math.max(maxLat - minLat, 0.01);
    const spanLng = Math.max(maxLng - minLng, 0.01);
    return {
      x: (lng: number) =>
        ((lng - minLng + spanLng * pad) / (spanLng * (1 + pad * 2))) * 100,
      y: (lat: number) =>
        100 - ((lat - minLat + spanLat * pad) / (spanLat * (1 + pad * 2))) * 100,
    };
  }, [markers]);

  // Route lines, one polyline per day, in visit order.
  const routes = React.useMemo(() => {
    if (!payload || !projection) return [];
    const days = dayFilter === "all" ? trip.days.map((d) => d.day_number) : [dayFilter];
    return days.map((dayNumber) => {
      const day = trip.days.find((d) => d.day_number === dayNumber);
      const points = (day?.activities ?? [])
        .map((a) => a.place.coordinates)
        .map((c) => `${projection.x(c.lng)},${projection.y(c.lat)}`);
      return {
        dayNumber,
        points: points.join(" "),
        color: DAY_COLORS[(dayNumber - 1) % DAY_COLORS.length],
      };
    });
  }, [payload, projection, dayFilter, trip.days]);

  if (!payload) {
    return <Skeleton className="h-[520px] w-full" />;
  }

  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_340px]">
      <div className="min-w-0">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <button
            onClick={() => setDayFilter("all")}
            className={cn(
              "rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
              dayFilter === "all"
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border hover:border-primary/40",
            )}
          >
            All days
          </button>
          {trip.days.map((d) => (
            <button
              key={d.id}
              onClick={() => setDayFilter(d.day_number)}
              className={cn(
                "flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
                dayFilter === d.day_number
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-border hover:border-primary/40",
              )}
            >
              <span
                className="size-2 rounded-full"
                style={{
                  background: DAY_COLORS[(d.day_number - 1) % DAY_COLORS.length],
                }}
              />
              Day {d.day_number}
            </button>
          ))}
        </div>

        <Card className="relative aspect-[4/3] overflow-hidden sm:aspect-[16/10]">
          {/* backdrop */}
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/[0.07] via-sky-500/[0.05] to-orange-500/[0.06]" />
          <div className="grid-lines absolute inset-0 opacity-40" />

          <svg
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            className="absolute inset-0 size-full"
          >
            {routes.map((r) =>
              r.points ? (
                <polyline
                  key={r.dayNumber}
                  points={r.points}
                  fill="none"
                  stroke={r.color}
                  strokeWidth="0.5"
                  strokeOpacity="0.55"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeDasharray="1.6 1.4"
                  vectorEffect="non-scaling-stroke"
                />
              ) : null,
            )}
          </svg>

          {projection &&
            markers.map((m) => {
              const Icon = categoryIcon(String(m.place.category));
              const color = DAY_COLORS[(m.days[0] - 1) % DAY_COLORS.length];
              const isSelected = selected?.place.id === m.place.id;
              return (
                <button
                  key={m.place.id}
                  onClick={() => setSelected(isSelected ? null : m)}
                  className="absolute -translate-x-1/2 -translate-y-full focus:outline-none"
                  style={{
                    left: `${projection.x(m.place.coordinates.lng)}%`,
                    top: `${projection.y(m.place.coordinates.lat)}%`,
                    zIndex: isSelected ? 20 : 10,
                  }}
                  aria-label={m.place.name}
                >
                  <motion.span
                    initial={{ scale: 0, y: -8 }}
                    animate={{ scale: 1, y: 0 }}
                    transition={{ type: "spring", stiffness: 300, damping: 20 }}
                    className={cn(
                      "flex size-8 items-center justify-center rounded-full border-2 border-white text-white shadow-lg transition-transform hover:scale-110",
                      isSelected && "scale-125 ring-4 ring-white/40",
                    )}
                    style={{ background: color }}
                  >
                    <Icon className="size-3.5" />
                  </motion.span>
                  <span
                    className="mx-auto block size-0 border-x-[5px] border-t-[7px] border-x-transparent"
                    style={{ borderTopColor: color }}
                  />
                </button>
              );
            })}

          <div className="absolute bottom-3 left-3 rounded-lg bg-background/85 px-2.5 py-1.5 text-[11px] text-muted-foreground backdrop-blur">
            {payload.google_maps_key_present
              ? "Google Maps key detected"
              : "Offline projection — pins link out to Google Maps"}
          </div>
        </Card>

        <p className="mt-3 text-sm text-muted-foreground">
          {markers.length} stop{markers.length === 1 ? "" : "s"} plotted. Tap a pin for
          hours, rating and travel time.
        </p>
      </div>

      {/* detail rail */}
      <aside>
        {/* No `mode="wait"` here: gating the detail card's mount on the empty
            state finishing its exit animation leaves the panel blank if that
            animation is ever throttled. A plain crossfade is safer. */}
        <AnimatePresence initial={false}>
          {selected ? (
            <motion.div
              key={selected.place.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2 }}
            >
              <PlaceDetail
                marker={selected}
                currency={trip.preferences.currency}
                nearby={nearby}
                loadingNearby={loadingNearby}
                onClose={() => setSelected(null)}
                onPick={(placeId) => {
                  const next = payload.markers.find((m) => m.place.id === placeId);
                  if (next) setSelected(next);
                }}
              />
            </motion.div>
          ) : (
            <motion.div key="empty" initial={false} animate={{ opacity: 1 }}>
              <Card className="p-5">
                <MapPin className="size-5 text-primary" />
                <h3 className="mt-3 font-semibold tracking-tight">Pick a stop</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                  Every pin carries its opening hours, rating, price level, walking
                  effort and what's nearby.
                </p>
                <div className="mt-4 space-y-2">
                  {markers.slice(0, 6).map((m) => (
                    <button
                      key={m.place.id}
                      onClick={() => setSelected(m)}
                      className="flex w-full items-center gap-3 rounded-xl border border-border p-2.5 text-left transition-colors hover:border-primary/40 hover:bg-secondary/50"
                    >
                      <span
                        className="size-8 shrink-0 rounded-lg"
                        style={placeGradient(m.place)}
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium">
                          {m.place.name}
                        </span>
                        <span className="block text-xs text-muted-foreground">
                          Day {m.days.join(", ")} · {formatTime(m.start_time)}
                        </span>
                      </span>
                    </button>
                  ))}
                </div>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </aside>
    </div>
  );
}

function PlaceDetail({
  marker,
  currency,
  nearby,
  loadingNearby,
  onClose,
  onPick,
}: {
  marker: MapMarker;
  currency: string;
  nearby: NearbyPlace[] | null;
  loadingNearby: boolean;
  onClose: () => void;
  onPick: (placeId: string) => void;
}) {
  const { place } = marker;
  const Icon = categoryIcon(String(place.category));
  const TravelIcon = TRAVEL_ICON[marker.travel_mode];

  return (
    <Card className="overflow-hidden">
      {/* "photo" */}
      <div className="relative h-32" style={placeGradient(place)}>
        <Icon className="absolute left-1/2 top-1/2 size-10 -translate-x-1/2 -translate-y-1/2 text-white/80" />
        <button
          onClick={onClose}
          className="absolute right-2.5 top-2.5 rounded-full bg-black/25 p-1.5 text-white backdrop-blur transition-colors hover:bg-black/40"
          aria-label="Close"
        >
          <X className="size-3.5" />
        </button>
        <div className="absolute bottom-2.5 left-3 flex gap-1.5">
          <Badge className="border-transparent bg-black/35 text-white backdrop-blur">
            Day {marker.days.join(", ")}
          </Badge>
          <Badge className="border-transparent bg-black/35 text-white backdrop-blur">
            {formatTime(marker.start_time)}
          </Badge>
        </div>
      </div>

      <div className="p-5">
        <h3 className="text-lg font-semibold tracking-tight">{place.name}</h3>
        <p className="mt-0.5 text-sm text-muted-foreground">{place.address}</p>

        <div className="mt-3 flex flex-wrap gap-1.5">
          <Badge variant="secondary">
            {CATEGORY_LABEL[String(place.category)] ?? place.category}
          </Badge>
          {place.indoor && (
            <Badge variant="secondary">
              <Home /> Indoor
            </Badge>
          )}
          <Badge variant="outline">{"$".repeat(Math.max(place.price_level, 1))}</Badge>
        </div>

        <dl className="mt-4 space-y-2.5 text-sm">
          <Row icon={Star} label="Rating">
            <span className="font-medium">{place.rating.toFixed(1)}</span>
            <span className="text-muted-foreground">
              {" "}
              · {place.review_count.toLocaleString()} reviews
            </span>
          </Row>
          <Row icon={Clock} label="Opening hours">
            {place.opening_hours}
          </Row>
          <Row icon={TravelIcon} label="Travel from previous">
            {marker.travel_time_minutes > 0
              ? `${duration(marker.travel_time_minutes)} by ${marker.travel_mode}`
              : "First stop of the day"}
          </Row>
          <Row icon={Footprints} label="Walking effort">
            {"●".repeat(place.walking_intensity)}
            <span className="text-muted-foreground">
              {"○".repeat(5 - place.walking_intensity)}
            </span>
          </Row>
          <Row icon={Trees} label="Estimated cost">
            {marker.estimated_cost > 0 ? money(marker.estimated_cost, currency) : "Free"}
          </Row>
        </dl>

        {place.description && (
          <p className="mt-4 rounded-lg bg-secondary/60 px-3 py-2.5 text-xs leading-relaxed">
            {place.description}
          </p>
        )}

        <Button variant="outline" size="sm" className="mt-4 w-full" asChild>
          <a href={marker.maps_url} target="_blank" rel="noopener noreferrer">
            <Navigation /> Directions <ExternalLink />
          </a>
        </Button>

        <div className="mt-5 border-t border-border pt-4">
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Nearby
          </h4>
          {loadingNearby ? (
            <div className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-3.5 animate-spin" /> Looking around…
            </div>
          ) : (
            <div className="mt-2.5 space-y-1.5">
              {(nearby ?? []).slice(0, 4).map((n) => (
                <button
                  key={n.place.id}
                  onClick={() => onPick(n.place.id)}
                  className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm transition-colors hover:bg-secondary"
                >
                  <span className="min-w-0 flex-1 truncate">{n.place.name}</span>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {n.walk_minutes} min
                  </span>
                </button>
              ))}
              {nearby?.length === 0 && (
                <p className="text-sm text-muted-foreground">Nothing else close by.</p>
              )}
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

function Row({
  icon: Icon,
  label,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-2.5">
      <Icon className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
      <div className="min-w-0 flex-1">
        <dt className="text-xs text-muted-foreground">{label}</dt>
        <dd className="truncate">{children}</dd>
      </div>
    </div>
  );
}

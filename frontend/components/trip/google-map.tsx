"use client";

import * as React from "react";

import type { MapMarker, Trip } from "@/lib/types";

const MAPS_KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;

export const hasGoogleMaps = Boolean(MAPS_KEY);

let loaderPromise: Promise<void> | null = null;

/** Load the Maps JS API once, shared across every mount. */
function loadMapsApi(): Promise<void> {
  if (typeof window === "undefined") return Promise.reject(new Error("server"));
  if ((window as any).google?.maps) return Promise.resolve();
  if (loaderPromise) return loaderPromise;

  loaderPromise = new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${MAPS_KEY}&v=weekly&loading=async`;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => {
      loaderPromise = null;
      reject(new Error("Google Maps failed to load"));
    };
    document.head.appendChild(script);
  });
  return loaderPromise;
}

const DAY_COLORS = [
  "#2f9e7e",
  "#e8712a",
  "#8b5cf6",
  "#2196d6",
  "#e0457b",
  "#e0a020",
  "#3aa76d",
];

function pinIcon(color: string, selected: boolean) {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="34" height="44" viewBox="0 0 34 44">
      <path d="M17 43C17 43 32 26.5 32 16A15 15 0 1 0 2 16C2 26.5 17 43 17 43Z"
            fill="${color}" stroke="white" stroke-width="${selected ? 3.5 : 2.5}"/>
      <circle cx="17" cy="16" r="5.5" fill="white"/>
    </svg>`;
  return {
    url: `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`,
    scaledSize: new google.maps.Size(selected ? 40 : 32, selected ? 52 : 41),
    anchor: new google.maps.Point(selected ? 20 : 16, selected ? 52 : 41),
  };
}

/**
 * Real Google Maps, used whenever NEXT_PUBLIC_GOOGLE_MAPS_API_KEY is set.
 * `onUnavailable` lets the parent fall back to the offline projection if the
 * script is blocked, the key is rejected, or billing is not enabled — the map
 * silently showing nothing would be the worst outcome.
 */
export function GoogleMapCanvas({
  trip,
  markers,
  selectedId,
  dayFilter,
  onSelect,
  onUnavailable,
}: {
  trip: Trip;
  markers: MapMarker[];
  selectedId: string | null;
  dayFilter: number | "all";
  onSelect: (marker: MapMarker) => void;
  onUnavailable: (reason: string) => void;
}) {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const mapRef = React.useRef<any>(null);
  const markerRefs = React.useRef<any[]>([]);
  const lineRefs = React.useRef<any[]>([]);
  const [ready, setReady] = React.useState(false);

  // Keep the latest onSelect without making the map re-initialise.
  const selectRef = React.useRef(onSelect);
  React.useEffect(() => {
    selectRef.current = onSelect;
  }, [onSelect]);

  React.useEffect(() => {
    let cancelled = false;
    loadMapsApi()
      .then(() => {
        if (cancelled || !containerRef.current) return;
        mapRef.current = new google.maps.Map(containerRef.current, {
          center: { lat: trip.center.lat, lng: trip.center.lng },
          zoom: 12,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: false,
          clickableIcons: false,
        });
        setReady(true);
      })
      .catch((err) => {
        if (!cancelled) onUnavailable(err.message ?? "Google Maps unavailable");
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trip.center.lat, trip.center.lng]);

  // Redraw markers and routes whenever the visible set changes.
  React.useEffect(() => {
    if (!ready || !mapRef.current) return;
    const map = mapRef.current;

    markerRefs.current.forEach((m) => m.setMap(null));
    lineRefs.current.forEach((l) => l.setMap(null));
    markerRefs.current = [];
    lineRefs.current = [];

    const bounds = new google.maps.LatLngBounds();

    for (const marker of markers) {
      const color = DAY_COLORS[(marker.days[0] - 1) % DAY_COLORS.length];
      const position = {
        lat: marker.place.coordinates.lat,
        lng: marker.place.coordinates.lng,
      };
      const pin = new google.maps.Marker({
        map,
        position,
        title: marker.place.name,
        icon: pinIcon(color, selectedId === marker.place.id),
        zIndex: selectedId === marker.place.id ? 999 : undefined,
      });
      pin.addListener("click", () => selectRef.current(marker));
      markerRefs.current.push(pin);
      bounds.extend(position);
    }

    const days =
      dayFilter === "all" ? trip.days.map((d) => d.day_number) : [dayFilter];
    for (const dayNumber of days) {
      const day = trip.days.find((d) => d.day_number === dayNumber);
      const path = (day?.activities ?? []).map((a) => ({
        lat: a.place.coordinates.lat,
        lng: a.place.coordinates.lng,
      }));
      if (path.length < 2) continue;
      lineRefs.current.push(
        new google.maps.Polyline({
          map,
          path,
          strokeColor: DAY_COLORS[(dayNumber - 1) % DAY_COLORS.length],
          strokeOpacity: 0,
          icons: [
            {
              icon: {
                path: "M 0,-1 0,1",
                strokeOpacity: 0.7,
                strokeWeight: 3,
                scale: 3,
              },
              offset: "0",
              repeat: "14px",
            },
          ],
        }),
      );
    }

    if (!bounds.isEmpty()) {
      map.fitBounds(bounds, 56);
    }
  }, [ready, markers, selectedId, dayFilter, trip.days]);

  return <div ref={containerRef} className="absolute inset-0" />;
}

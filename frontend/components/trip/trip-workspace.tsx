"use client";

import * as React from "react";
import { useSearchParams } from "next/navigation";
import {
  BookHeart,
  CloudSun,
  Compass,
  Luggage,
  Map as MapIcon,
  Route,
  Wallet,
} from "lucide-react";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AlertStack } from "@/components/companion/alert-stack";
import { CompanionDock } from "@/components/companion/companion-dock";
import { ExpensesPanel } from "@/components/trip/expenses-panel";
import { ItineraryPanel } from "@/components/trip/itinerary-panel";
import { JournalPanel } from "@/components/trip/journal-panel";
import { MapPanel } from "@/components/trip/map-panel";
import { PackingPanel } from "@/components/trip/packing-panel";
import { ToolboxPanel } from "@/components/trip/toolbox-panel";
import { TripHeader } from "@/components/trip/trip-header";
import { WeatherPanel } from "@/components/trip/weather-panel";
import { api } from "@/lib/api";
import type { ItineraryChange, Trip } from "@/lib/types";

const TABS = [
  { value: "itinerary", label: "Itinerary", icon: Route },
  { value: "map", label: "Map", icon: MapIcon },
  { value: "weather", label: "Weather", icon: CloudSun },
  { value: "expenses", label: "Budget", icon: Wallet },
  { value: "packing", label: "Packing", icon: Luggage },
  { value: "journal", label: "Journal", icon: BookHeart },
  { value: "toolbox", label: "Toolbox", icon: Compass },
];

const TAB_VALUES = new Set([
  "itinerary",
  "map",
  "weather",
  "expenses",
  "packing",
  "journal",
  "toolbox",
]);

export function TripWorkspace({ initialTrip }: { initialTrip: Trip }) {
  const [trip, setTrip] = React.useState(initialTrip);

  // `?tab=` makes each panel deep-linkable, so a shared link can open straight
  // on the map or the budget. Read through useSearchParams so the server and
  // the client agree on the first render.
  const searchParams = useSearchParams();
  const requested = searchParams.get("tab");
  const initialTab = requested && TAB_VALUES.has(requested) ? requested : "itinerary";

  const [tab, setTabState] = React.useState(initialTab);

  const setTab = React.useCallback((next: string) => {
    setTabState(next);
    const url = new URL(window.location.href);
    if (next === "itinerary") url.searchParams.delete("tab");
    else url.searchParams.set("tab", next);
    window.history.replaceState(null, "", url);
  }, []);
  // Activity ids the companion touched most recently, so the itinerary can
  // highlight exactly what moved.
  const [touched, setTouched] = React.useState<string[]>([]);

  const highlightChanges = React.useCallback((changes: ItineraryChange[]) => {
    const ids = changes.map((c) => c.activity_id).filter(Boolean) as string[];
    if (!ids.length) return;
    setTouched(ids);
    const first = changes[0];
    if (first?.day_number) setTab("itinerary");
    setTimeout(() => setTouched([]), 6000);
  }, []);

  // The companion should be working even while the tab sits open. One scan on
  // mount catches anything that changed since the trip was last loaded.
  React.useEffect(() => {
    let cancelled = false;
    api
      .scanAlerts(initialTrip.id)
      .then(({ trip: scanned }) => {
        if (!cancelled) setTrip(scanned);
      })
      .catch(() => {
        /* the trip is still usable without a fresh scan */
      });
    return () => {
      cancelled = true;
    };
  }, [initialTrip.id]);

  return (
    <div className="pb-28">
      <TripHeader trip={trip} onTripChange={setTrip} />

      <div className="container">
        <AlertStack trip={trip} onTripChange={setTrip} onHighlight={highlightChanges} />

        <Tabs value={tab} onValueChange={setTab} className="mt-6">
          <TabsList>
            {TABS.map((t) => (
              <TabsTrigger key={t.value} value={t.value}>
                <t.icon />
                <span className="hidden md:inline">{t.label}</span>
              </TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="itinerary">
            <ItineraryPanel trip={trip} touched={touched} />
          </TabsContent>
          <TabsContent value="map">
            <MapPanel trip={trip} />
          </TabsContent>
          <TabsContent value="weather">
            <WeatherPanel trip={trip} onTripChange={setTrip} />
          </TabsContent>
          <TabsContent value="expenses">
            <ExpensesPanel trip={trip} onTripChange={setTrip} />
          </TabsContent>
          <TabsContent value="packing">
            <PackingPanel trip={trip} onTripChange={setTrip} />
          </TabsContent>
          <TabsContent value="journal">
            <JournalPanel trip={trip} onTripChange={setTrip} />
          </TabsContent>
          <TabsContent value="toolbox">
            <ToolboxPanel trip={trip} />
          </TabsContent>
        </Tabs>
      </div>

      <CompanionDock
        trip={trip}
        onTripChange={setTrip}
        onHighlight={highlightChanges}
      />
    </div>
  );
}

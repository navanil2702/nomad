import {
  Bike,
  Building2,
  Camera,
  Cloud,
  CloudDrizzle,
  CloudFog,
  CloudLightning,
  CloudSun,
  Landmark,
  Moon,
  Mountain,
  ShoppingBag,
  Snowflake,
  Sun,
  Trees,
  UtensilsCrossed,
  type LucideIcon,
} from "lucide-react";

import { hashHue } from "./utils";
import type { Interest, Place, WeatherCondition } from "./types";

/**
 * Places have no photographs offline, so each one gets a stable, category-tinted
 * gradient derived from its id. It reads as deliberate art direction rather than
 * a missing image, and it never depends on the network.
 */
export function placeGradient(place: Pick<Place, "id" | "category">) {
  const hue = hashHue(place.id);
  const base = CATEGORY_HUE[place.category as Interest] ?? hue;
  const h1 = (base + (hue % 26)) % 360;
  const h2 = (h1 + 42) % 360;
  return {
    backgroundImage: `linear-gradient(135deg, hsl(${h1} 68% 56%), hsl(${h2} 62% 42%))`,
  };
}

const CATEGORY_HUE: Record<string, number> = {
  food: 22,
  adventure: 8,
  history: 268,
  shopping: 320,
  nature: 148,
  nightlife: 232,
  meal: 30,
};

export const CATEGORY_ICON: Record<string, LucideIcon> = {
  food: UtensilsCrossed,
  meal: UtensilsCrossed,
  adventure: Bike,
  history: Landmark,
  shopping: ShoppingBag,
  nature: Trees,
  nightlife: Moon,
  rest: Building2,
  transit: Building2,
};

export function categoryIcon(category: string): LucideIcon {
  return CATEGORY_ICON[category] ?? Camera;
}

export const CATEGORY_LABEL: Record<string, string> = {
  food: "Food",
  meal: "Meal",
  adventure: "Adventure",
  history: "History & culture",
  shopping: "Shopping",
  nature: "Nature",
  nightlife: "Nightlife",
};

export const WEATHER_ICON: Record<WeatherCondition, LucideIcon> = {
  clear: Sun,
  clouds: CloudSun,
  rain: CloudDrizzle,
  storm: CloudLightning,
  snow: Snowflake,
  fog: CloudFog,
};

export const WEATHER_TINT: Record<WeatherCondition, string> = {
  clear: "from-amber-400/25 to-orange-500/10",
  clouds: "from-slate-400/25 to-slate-500/10",
  rain: "from-sky-500/25 to-blue-600/10",
  storm: "from-violet-500/30 to-indigo-700/15",
  snow: "from-cyan-200/30 to-sky-400/10",
  fog: "from-zinc-400/25 to-zinc-500/10",
};

export const INTEREST_META: {
  value: Interest;
  label: string;
  icon: LucideIcon;
  blurb: string;
}[] = [
  { value: "food", label: "Food", icon: UtensilsCrossed, blurb: "Markets, counters, long dinners" },
  { value: "adventure", label: "Adventure", icon: Mountain, blurb: "Climbs, water, things that move" },
  { value: "history", label: "History", icon: Landmark, blurb: "Ruins, museums, old quarters" },
  { value: "shopping", label: "Shopping", icon: ShoppingBag, blurb: "Boutiques, markets, makers" },
  { value: "nature", label: "Nature", icon: Trees, blurb: "Parks, coast, green escapes" },
  { value: "nightlife", label: "Nightlife", icon: Moon, blurb: "Bars, music, late kitchens" },
];

export const PACE_META = [
  {
    value: "relaxed" as const,
    label: "Relaxed",
    detail: "3 stops a day, late starts",
    icon: Cloud,
  },
  {
    value: "balanced" as const,
    label: "Balanced",
    detail: "4 stops, room to wander",
    icon: CloudSun,
  },
  {
    value: "packed" as const,
    label: "Packed",
    detail: "5 stops, early starts",
    icon: Sun,
  },
];

export const MOOD_META: Record<string, { label: string; emoji: string; tint: string }> = {
  delighted: { label: "Delighted", emoji: "✦", tint: "text-amber-500" },
  happy: { label: "Happy", emoji: "●", tint: "text-emerald-500" },
  calm: { label: "Calm", emoji: "○", tint: "text-sky-500" },
  tired: { label: "Tired", emoji: "◐", tint: "text-orange-500" },
  stressed: { label: "Stressed", emoji: "◆", tint: "text-rose-500" },
};

export const EXPENSE_COLORS: Record<string, string> = {
  food: "hsl(22 85% 58%)",
  transport: "hsl(200 82% 52%)",
  shopping: "hsl(320 70% 58%)",
  hotels: "hsl(262 70% 62%)",
  activities: "hsl(168 62% 42%)",
};

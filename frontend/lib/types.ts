/** Mirrors backend/app/models/schemas.py. Keep the two in step. */

export type Interest =
  | "food"
  | "adventure"
  | "history"
  | "shopping"
  | "nature"
  | "nightlife";

export type Pace = "relaxed" | "balanced" | "packed";
export type Slot = "morning" | "afternoon" | "evening";
export type ExpenseCategory =
  | "food"
  | "transport"
  | "shopping"
  | "hotels"
  | "activities";
export type Mood = "delighted" | "happy" | "calm" | "tired" | "stressed";
export type WeatherCondition =
  | "clear"
  | "clouds"
  | "rain"
  | "storm"
  | "snow"
  | "fog";
export type Severity = "info" | "warning" | "severe";
export type TravelMode = "walk" | "transit" | "taxi";

export interface Coordinates {
  lat: number;
  lng: number;
}

export interface Place {
  id: string;
  name: string;
  category: Interest | "meal" | "rest" | "transit";
  description: string;
  coordinates: Coordinates;
  rating: number;
  review_count: number;
  price_level: number;
  indoor: boolean;
  walking_intensity: number;
  opening_hours: string;
  photo: string;
  tags: string[];
  address: string;
}

export interface Activity {
  id: string;
  slot: Slot;
  title: string;
  place: Place;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  estimated_cost: number;
  travel_time_minutes: number;
  travel_mode: TravelMode;
  maps_url: string;
  local_tip: string;
  is_meal: boolean;
  locked: boolean;
  origin: "planned" | "companion" | "proactive";
  note: string | null;
}

export interface DayPlan {
  id: string;
  day_number: number;
  date: string;
  title: string;
  summary: string;
  activities: Activity[];
  estimated_cost: number;
  total_travel_minutes: number;
  local_tips: string[];
}

export interface BudgetBreakdown {
  accommodation: number;
  food: number;
  transport: number;
  activities: number;
}

export interface WeatherDay {
  date: string;
  condition: WeatherCondition;
  description: string;
  temp_min_c: number;
  temp_max_c: number;
  precipitation_chance: number;
  wind_kph: number;
  humidity: number;
  sunrise: string;
  sunset: string;
  onset_hour: number | null;
}

export interface WeatherAlert {
  id: string;
  date: string;
  severity: Severity;
  title: string;
  message: string;
  recommend_indoor: boolean;
}

export interface PackingItem {
  id: string;
  label: string;
  category:
    | "essentials"
    | "clothing"
    | "weather"
    | "electronics"
    | "health"
    | "activity";
  reason: string;
  packed: boolean;
  essential: boolean;
}

export interface Expense {
  id: string;
  label: string;
  amount: number;
  category: ExpenseCategory;
  date: string;
  created_at: string;
  note: string | null;
}

export interface JournalEntry {
  id: string;
  day_number: number;
  date: string;
  title: string;
  summary: string;
  places_visited: string[];
  highlights: string[];
  spend: number;
  mood: Mood;
  photo: string;
  created_at: string;
}

export interface ItineraryChange {
  id: string;
  kind:
    | "replaced"
    | "moved"
    | "removed"
    | "added"
    | "reordered"
    | "downgraded"
    | "noted";
  day_number: number;
  summary: string;
  before: string | null;
  after: string | null;
  before_place_id: string | null;
  after_place_id: string | null;
  activity_id: string | null;
  to_day_number: number | null;
}

export interface ChatMessage {
  id: string;
  role: "user" | "companion";
  content: string;
  created_at: string;
  changes: ItineraryChange[];
  intent: string | null;
}

export interface ProactiveAlert {
  id: string;
  trigger: "weather" | "budget" | "pace" | "closing" | "arrival";
  severity: Severity;
  title: string;
  message: string;
  day_number: number | null;
  changes: ItineraryChange[];
  applied: boolean;
  dismissed: boolean;
  created_at: string;
}

export interface TripPreferences {
  destination: string;
  start_date: string;
  end_date: string;
  budget: number;
  currency: string;
  travelers: number;
  interests: Interest[];
  pace: Pace;
}

/** The frozen place catalog a trip was planned from. */
export interface DestinationCatalog {
  key: string;
  name: string;
  country: string;
  language: string;
  currency: string;
  timezone: string;
  utc_offset_hours: number;
  climate: string;
  daily_cost_index: number;
  blurb: string;
  /** "google-places" | "curated" | "generated" */
  source: string;
  center: Coordinates;
  places: Place[];
  costs: Record<string, number>;
  durations: Record<string, number>;
}

export interface Trip {
  id: string;
  owner: string;
  title: string;
  preferences: TripPreferences;
  center: Coordinates;
  catalog: DestinationCatalog | null;
  timezone: string;
  country: string;
  language: string;
  days: DayPlan[];
  budget_breakdown: BudgetBreakdown;
  weather: WeatherDay[];
  weather_alerts: WeatherAlert[];
  packing_list: PackingItem[];
  expenses: Expense[];
  journal: JournalEntry[];
  messages: ChatMessage[];
  alerts: ProactiveAlert[];
  share_token: string;
  created_at: string;
  updated_at: string;
}

export interface TripSummary {
  id: string;
  title: string;
  destination: string;
  start_date: string;
  end_date: string;
  travelers: number;
  budget: number;
  spent: number;
  cover: string;
  updated_at: string;
}

export interface ExpenseStats {
  budget: number;
  spent: number;
  remaining: number;
  by_category: Record<string, number>;
  by_day: {
    date: string;
    label: string;
    day_number: number;
    amount: number;
    planned: number;
  }[];
  daily_average: number;
  projected_total: number;
  over_budget: boolean;
}

export interface MapMarker {
  place: Place;
  days: number[];
  slot: Slot;
  start_time: string;
  estimated_cost: number;
  travel_time_minutes: number;
  travel_mode: TravelMode;
  maps_url: string;
  is_meal: boolean;
}

export interface MapPayload {
  center: Coordinates;
  google_maps_key_present: boolean;
  markers: MapMarker[];
}

export interface NearbyPlace {
  place: Place;
  distance_km: number;
  walk_minutes: number;
  maps_url: string;
}

export interface Phrase {
  english: string;
  local: string;
  pronunciation: string;
}

export interface EmergencyContact {
  label: string;
  number: string;
  note: string;
}

export interface LocalInfo {
  country: string;
  language: string;
  currency: string;
  currency_rate_from_usd: number;
  timezone: string;
  utc_offset_hours: number;
  phrases: Phrase[];
  emergency: EmergencyContact[];
  plug_type: string;
  tipping: string;
}

export interface DestinationOption {
  key: string;
  name: string;
  country: string;
  label: string;
  blurb: string;
  currency: string;
  cost_index: number;
  places: number;
}

export interface Retrospective {
  title: string;
  closing: string;
  stats: {
    days: number;
    places: number;
    meals: number;
    spend: number;
    travel_minutes: number;
    walking_score: number;
    dominant_mood: Mood;
  };
  highlights: string[];
  entries: JournalEntry[];
}

export interface OfflineBundle {
  generated_at: string;
  trip: {
    title: string;
    destination: string;
    dates: string;
    travelers: number;
  };
  days: {
    day: number;
    date: string;
    title: string;
    stops: {
      time: string;
      name: string;
      address: string;
      hours: string;
      coordinates: Coordinates;
      maps_url: string;
      tip: string;
      cost: number;
    }[];
  }[];
  emergency: EmergencyContact[];
  phrases: Phrase[];
  packing: string[];
}

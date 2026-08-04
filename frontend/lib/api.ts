import type {
  ChatMessage,
  DestinationOption,
  ExpenseCategory,
  ExpenseStats,
  LocalInfo,
  MapPayload,
  Mood,
  NearbyPlace,
  OfflineBundle,
  ProactiveAlert,
  Retrospective,
  Trip,
  TripPreferences,
  TripSummary,
} from "./types";

/**
 * In the browser, requests go to the same origin and Next's rewrite forwards
 * them to FastAPI — so there is no CORS step, locally or in production.
 *
 * On the server there is no origin to be relative to, so it calls the API
 * directly: `API_URL` in a deployment, localhost otherwise. Setting
 * `NEXT_PUBLIC_API_URL` overrides both and makes the browser call the API
 * cross-origin, which then does require `CORS_ORIGINS` on the backend.
 */
const BASE =
  typeof window === "undefined"
    ? (process.env.NEXT_PUBLIC_API_URL ??
       process.env.API_URL ??
       "http://127.0.0.1:8000")
    : (process.env.NEXT_PUBLIC_API_URL ?? "");

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      "Can't reach the Nomad API. Is the backend running on port 8000?",
      0,
    );
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
      if (Array.isArray(detail)) detail = detail[0]?.msg ?? "Invalid request";
    } catch {
      /* keep statusText */
    }
    throw new ApiError(String(detail), res.status);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });

export const api = {
  health: () =>
    request<{ status: string; providers: Record<string, string> }>("/api/health"),

  providers: () =>
    request<{
      providers: Record<
        string,
        {
          configured: boolean;
          mode: string;
          fallback?: string;
          model?: string | null;
          last_error?: string | null;
        }
      >;
    }>("/api/providers"),

  // --- trips -------------------------------------------------------------
  listTrips: () => request<TripSummary[]>("/api/trips"),
  getTrip: (id: string) => request<Trip>(`/api/trips/${id}`),
  createTrip: (prefs: Omit<TripPreferences, "currency"> & { currency?: string }) =>
    post<Trip>("/api/trips", prefs),
  deleteTrip: (id: string) =>
    request<{ deleted: string }>(`/api/trips/${id}`, { method: "DELETE" }),
  regenerateTrip: (id: string) => post<Trip>(`/api/trips/${id}/regenerate`),

  // --- map, weather, packing, local --------------------------------------
  getMap: (id: string) => request<MapPayload>(`/api/trips/${id}/map`),
  getNearby: (id: string, placeId: string) =>
    request<NearbyPlace[]>(`/api/trips/${id}/places/${placeId}/nearby`),
  refreshWeather: (id: string) => post<Trip>(`/api/trips/${id}/weather/refresh`),
  togglePacking: (id: string, itemId: string, packed: boolean) =>
    request<Trip>(`/api/trips/${id}/packing/${itemId}`, {
      method: "PATCH",
      body: JSON.stringify({ packed }),
    }),
  regeneratePacking: (id: string) => post<Trip>(`/api/trips/${id}/packing/regenerate`),
  getLocalInfo: (id: string) => request<LocalInfo>(`/api/trips/${id}/local`),
  getOffline: (id: string) => request<OfflineBundle>(`/api/trips/${id}/offline`),
  offlinePdfUrl: (id: string) => `${BASE}/api/trips/${id}/offline.pdf`,
  getShareLink: (id: string) =>
    request<{ token: string; path: string }>(`/api/trips/${id}/share`),

  // --- companion ---------------------------------------------------------
  chat: (id: string, message: string, dayNumber?: number) =>
    post<{ message: ChatMessage; trip: Trip }>(`/api/trips/${id}/chat`, {
      message,
      day_number: dayNumber ?? null,
    }),
  chatPrompts: (id: string) => request<string[]>(`/api/trips/${id}/chat/prompts`),
  clearChat: (id: string) =>
    request<Trip>(`/api/trips/${id}/chat`, { method: "DELETE" }),

  listAlerts: (id: string) => request<ProactiveAlert[]>(`/api/trips/${id}/alerts`),
  scanAlerts: (id: string) =>
    post<{ new: ProactiveAlert[]; trip: Trip }>(`/api/trips/${id}/alerts/scan`),
  applyAlert: (id: string, alertId: string) =>
    post<{ alert: ProactiveAlert; trip: Trip }>(
      `/api/trips/${id}/alerts/${alertId}/apply`,
    ),
  undoAlert: (id: string, alertId: string) =>
    post<{ alert: ProactiveAlert; trip: Trip }>(
      `/api/trips/${id}/alerts/${alertId}/undo`,
    ),
  dismissAlert: (id: string, alertId: string) =>
    post<{ alert: ProactiveAlert; trip: Trip }>(
      `/api/trips/${id}/alerts/${alertId}/dismiss`,
    ),

  // --- expenses ----------------------------------------------------------
  addExpense: (
    id: string,
    body: {
      label: string;
      amount: number;
      category: ExpenseCategory;
      date?: string;
      note?: string;
    },
  ) => post<Trip>(`/api/trips/${id}/expenses`, body),
  deleteExpense: (id: string, expenseId: string) =>
    request<Trip>(`/api/trips/${id}/expenses/${expenseId}`, { method: "DELETE" }),
  expenseStats: (id: string) =>
    request<ExpenseStats>(`/api/trips/${id}/expenses/stats`),

  // --- journal -----------------------------------------------------------
  autowriteJournal: (id: string) => post<Trip>(`/api/trips/${id}/journal/autowrite`),
  writeJournalDay: (id: string, dayNumber: number, mood?: Mood, note?: string) =>
    post<Trip>(`/api/trips/${id}/journal/day`, {
      day_number: dayNumber,
      mood: mood ?? null,
      note: note ?? null,
    }),
  retrospective: (id: string) =>
    request<Retrospective>(`/api/trips/${id}/journal/retrospective`),

  // --- tools -------------------------------------------------------------
  searchDestinations: (q: string, limit = 6) =>
    request<
      { label: string; primary: string; secondary: string; curated?: boolean }[]
    >(`/api/destinations/search?q=${encodeURIComponent(q)}&limit=${limit}`),

  destinations: (q?: string) =>
    request<DestinationOption[]>(
      `/api/destinations${q ? `?q=${encodeURIComponent(q)}` : ""}`,
    ),
  convertCurrency: (amount: number, base: string, target: string) =>
    request<{
      amount: number;
      base: string;
      target: string;
      rate: number;
      converted: number;
      base_symbol: string;
      target_symbol: string;
      source: string;
    }>(`/api/currency/convert?amount=${amount}&base=${base}&target=${target}`),
  rates: () =>
    request<{
      base: string;
      rates: Record<string, number>;
      symbols: Record<string, string>;
    }>("/api/currency/rates"),
  timezone: (destination: string, homeOffsetHours: number) =>
    request<{
      destination: string;
      timezone: string;
      utc_offset_hours: number;
      local_time: string;
      local_date: string;
      home_time: string;
      difference_hours: number;
      summary: string;
    }>(
      `/api/timezone?destination=${encodeURIComponent(destination)}&home_offset_hours=${homeOffsetHours}`,
    ),
  sharedTrip: (token: string) => request<any>(`/api/shared/${token}`),
};

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Stable 0-359 hue from any string, so a place always looks the same. */
export function hashHue(seed: string): number {
  let h = 0;
  for (let i = 0; i < seed.length; i++) {
    h = (h << 5) - h + seed.charCodeAt(i);
    h |= 0;
  }
  return Math.abs(h) % 360;
}

const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: "$",
  EUR: "€",
  GBP: "£",
  JPY: "¥",
  IDR: "Rp",
  INR: "₹",
  AUD: "A$",
  CAD: "C$",
  THB: "฿",
  SGD: "S$",
};

export function currencySymbol(code: string) {
  return CURRENCY_SYMBOLS[code?.toUpperCase()] ?? `${code} `;
}

export function money(amount: number, currency = "USD", compact = false) {
  const symbol = currencySymbol(currency);
  const value = compact && Math.abs(amount) >= 1000
    ? `${(amount / 1000).toFixed(1)}k`
    : Math.abs(amount) >= 100 || Number.isInteger(amount)
      ? Math.round(amount).toLocaleString()
      : amount.toFixed(2);
  return `${amount < 0 ? "-" : ""}${symbol}${value.replace("-", "")}`;
}

export function formatDate(iso: string, opts?: Intl.DateTimeFormatOptions) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    ...opts,
  });
}

export function formatTime(hhmm: string) {
  const [h, m] = hhmm.split(":").map(Number);
  const suffix = h >= 12 ? "pm" : "am";
  const hour = h % 12 || 12;
  return m === 0 ? `${hour}${suffix}` : `${hour}:${String(m).padStart(2, "0")}${suffix}`;
}

export function duration(minutes: number) {
  if (minutes < 60) return `${minutes} min`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m ? `${h}h ${m}m` : `${h}h`;
}

export function daysBetween(startIso: string, endIso: string) {
  const ms =
    new Date(`${endIso}T00:00:00`).getTime() -
    new Date(`${startIso}T00:00:00`).getTime();
  return Math.max(Math.round(ms / 86_400_000) + 1, 1);
}

export function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export function addDaysIso(iso: string, days: number) {
  const d = new Date(`${iso}T00:00:00`);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

export function isPast(iso: string) {
  return iso < todayIso();
}

export function isToday(iso: string) {
  return iso === todayIso();
}

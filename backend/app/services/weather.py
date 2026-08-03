"""Weather forecasts.

Uses OpenWeather's One Call / forecast API when OPENWEATHER_API_KEY is set,
otherwise a deterministic climate model. The mock is seeded from destination
and date, so a given trip always shows the same forecast across reloads --
which matters, because the proactive engine reasons about it.
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta

import httpx

from ..core.config import get_settings
from ..models.schemas import Coordinates, WeatherAlert, WeatherDay
from .places import Destination

# base (min, max) °C and rain propensity 0-1 per climate band
_CLIMATE: dict[str, tuple[float, float, float]] = {
    "humid-subtropical": (14.0, 24.0, 0.34),
    "oceanic": (9.0, 18.0, 0.42),
    "tropical": (24.0, 31.0, 0.48),
    "mediterranean": (14.0, 26.0, 0.24),
    "temperate": (10.0, 20.0, 0.33),
    "arid": (18.0, 34.0, 0.06),
}

_CONDITION_TEXT = {
    "clear": "Clear skies",
    "clouds": "Partly cloudy",
    "rain": "Rain showers",
    "storm": "Thunderstorms",
    "snow": "Snow",
    "fog": "Morning fog",
}


def _noise(*parts: object) -> float:
    seed = "|".join(str(p) for p in parts)
    h = int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16)
    return (h % 10_000) / 10_000


def _seasonal_shift(day: date, lat: float) -> float:
    """Rough northern/southern-hemisphere seasonal swing in °C."""
    from math import cos, pi

    # Peak warmth around day 200 in the north, inverted in the south.
    phase = cos((day.timetuple().tm_yday - 200) / 365 * 2 * pi)
    amplitude = 9.0 * min(abs(lat) / 50.0, 1.0)
    return -phase * amplitude * (1 if lat >= 0 else -1)


def _mock_forecast(dest: Destination, start: date, days: int) -> list[WeatherDay]:
    lo, hi, rain_bias = _CLIMATE.get(dest.climate, _CLIMATE["temperate"])
    shift = _seasonal_shift(start, dest.center.lat)

    forecast: list[WeatherDay] = []
    for i in range(days):
        d = start + timedelta(days=i)
        n = _noise(dest.key, d.isoformat())
        wet = _noise(dest.key, "wet", d.isoformat())

        temp_min = round(lo + shift + (n - 0.5) * 5, 1)
        temp_max = round(hi + shift + (n - 0.5) * 5, 1)

        if wet < rain_bias * 0.28:
            condition = "storm"
            precip = 70 + int(n * 25)
        elif wet < rain_bias:
            condition = "rain"
            precip = 55 + int(n * 30)
        elif wet < rain_bias + 0.28:
            condition = "clouds"
            precip = 15 + int(n * 20)
        elif temp_max < 2:
            condition = "snow"
            precip = 60 + int(n * 20)
        else:
            condition = "clear"
            precip = int(n * 12)

        forecast.append(
            WeatherDay(
                date=d,
                condition=condition,
                description=_CONDITION_TEXT[condition],
                temp_min_c=temp_min,
                temp_max_c=temp_max,
                precipitation_chance=min(precip, 95),
                wind_kph=round(6 + n * 22, 1),
                humidity=int(48 + wet * 45),
                sunrise="06:%02d" % int(n * 55),
                sunset="19:%02d" % int(wet * 55),
                onset_hour=(11 + int(n * 8)) if condition in ("rain", "storm") else None,
            )
        )

    # A multi-day trip with no weather event never exercises the feature that
    # makes this product different. Nudge one mid-trip day into rain.
    if days >= 3 and not any(f.condition in ("rain", "storm") for f in forecast):
        target = forecast[1]
        target.condition = "rain"
        target.description = _CONDITION_TEXT["rain"]
        target.precipitation_chance = 78
        target.onset_hour = 14
        target.temp_max_c = round(target.temp_max_c - 3, 1)

    return forecast


def _live_forecast(
    center: Coordinates, start: date, days: int, api_key: str
) -> list[WeatherDay] | None:
    """OpenWeather 5-day/3-hour forecast, aggregated to daily."""
    try:
        r = httpx.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={
                "lat": center.lat,
                "lng": center.lng,
                "lon": center.lng,
                "appid": api_key,
                "units": "metric",
            },
            timeout=8.0,
        )
        r.raise_for_status()
        blocks = r.json().get("list", [])
    except Exception:
        return None

    if not blocks:
        return None

    buckets: dict[str, list[dict]] = {}
    for b in blocks:
        buckets.setdefault(b["dt_txt"][:10], []).append(b)

    mapping = {
        "Rain": "rain",
        "Drizzle": "rain",
        "Thunderstorm": "storm",
        "Snow": "snow",
        "Clear": "clear",
        "Clouds": "clouds",
    }

    out: list[WeatherDay] = []
    for i in range(days):
        d = start + timedelta(days=i)
        rows = buckets.get(d.isoformat())
        if not rows:
            break
        temps = [row["main"]["temp"] for row in rows]
        mains = [row["weather"][0]["main"] for row in rows]
        headline = max(set(mains), key=mains.count)
        for pref in ("Thunderstorm", "Snow", "Rain"):
            if pref in mains:
                headline = pref
                break
        onset = None
        if headline in ("Rain", "Thunderstorm", "Drizzle", "Snow"):
            onset = next(
                (int(row["dt_txt"][11:13]) for row in rows
                 if row["weather"][0]["main"] == headline),
                None,
            )
        out.append(
            WeatherDay(
                date=d,
                condition=mapping.get(headline, "clouds"),
                description=rows[0]["weather"][0]["description"].capitalize(),
                temp_min_c=round(min(temps), 1),
                temp_max_c=round(max(temps), 1),
                precipitation_chance=int(max(row.get("pop", 0) for row in rows) * 100),
                wind_kph=round(max(row["wind"]["speed"] for row in rows) * 3.6, 1),
                humidity=int(sum(row["main"]["humidity"] for row in rows) / len(rows)),
                onset_hour=onset,
            )
        )

    return out or None


def forecast(dest: Destination, start: date, days: int) -> list[WeatherDay]:
    settings = get_settings()
    if settings.openweather_api_key:
        live = _live_forecast(
            dest.center, start, days, settings.openweather_api_key
        )
        if live:
            # OpenWeather free tier only covers 5 days; extend with the model.
            if len(live) < days:
                tail = _mock_forecast(dest, start, days)[len(live):]
                live.extend(tail)
            return live
    return _mock_forecast(dest, start, days)


def build_alerts(forecast_days: list[WeatherDay]) -> list[WeatherAlert]:
    """Turn a forecast into user-facing warnings."""
    alerts: list[WeatherAlert] = []
    for f in forecast_days:
        when = f"{f.onset_hour % 12 or 12} {'AM' if f.onset_hour < 12 else 'PM'}" if f.onset_hour is not None else None

        if f.condition == "storm":
            alerts.append(
                WeatherAlert(
                    date=f.date,
                    severity="severe",
                    title="Thunderstorms expected",
                    message=(
                        f"Storms with a {f.precipitation_chance}% chance of rain"
                        + (f" from around {when}" if when else "")
                        + ". Outdoor plans are not going to hold."
                    ),
                    recommend_indoor=True,
                )
            )
        elif f.condition == "rain" and f.precipitation_chance >= 55:
            alerts.append(
                WeatherAlert(
                    date=f.date,
                    severity="warning",
                    title="Heavy rain likely",
                    message=(
                        f"{f.precipitation_chance}% chance of rain"
                        + (f" starting around {when}" if when else "")
                        + ". Worth moving outdoor stops indoors."
                    ),
                    recommend_indoor=True,
                )
            )
        elif f.temp_max_c >= 33:
            alerts.append(
                WeatherAlert(
                    date=f.date,
                    severity="warning",
                    title=f"Heat warning — {f.temp_max_c:.0f}°C",
                    message="Plan the walking for early morning and take a long midday break.",
                )
            )
        elif f.temp_min_c <= 0:
            alerts.append(
                WeatherAlert(
                    date=f.date,
                    severity="info",
                    title=f"Freezing overnight — {f.temp_min_c:.0f}°C",
                    message="Pack thermal layers and check that outdoor sites are still open.",
                )
            )
        elif f.wind_kph >= 45:
            alerts.append(
                WeatherAlert(
                    date=f.date,
                    severity="info",
                    title="Strong winds",
                    message=f"Gusts near {f.wind_kph:.0f} km/h — viewpoints and boat trips may close.",
                )
            )
    return alerts

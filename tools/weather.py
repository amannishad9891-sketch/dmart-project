"""tools/weather.py - get_weather(city, date) for the five store cities.

WEATHER_MODE=stub (default) returns deterministic values from a fixed formula.
WEATHER_MODE=live calls the free Open-Meteo archive API (optional, not graded for its output).
Weather data by Open-Meteo.com https://open-meteo.com/
"""
import os
import re
from datetime import date

COORDS = {
    "Mumbai": (19.0760, 72.8777),
    "Pune": (18.5204, 73.8567),
    "Hyderabad": (17.3850, 78.4867),
    "Bengaluru": (12.9716, 77.5946),
    "Ahmedabad": (23.0225, 72.5714),
}
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
TIMEOUT_SECONDS = 10


def _valid_date(text):
    """Exactly YYYY-MM-DD and a real calendar date."""
    if not isinstance(text, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _stub(city, d):
    doy = d.timetuple().tm_yday      # 1 January is 1
    n = len(city)
    return {"temperature_c": 20 + (n + doy) % 15,
            "humidity_pct": 40 + (3 * n + doy) % 50,
            "wind_kmh": 5 + doy % 10,
            "rain_mm": 6.5 if doy % 4 == 0 else 0.0}


def _live(city, text):
    try:
        import requests                      # needed only for live mode
    except ImportError:
        return {"ok": False, "error": "the requests library is not installed"}
    lat, lon = COORDS[city]
    params = {"latitude": lat, "longitude": lon, "start_date": text, "end_date": text,
              "timezone": "Asia/Kolkata",
              "daily": "temperature_2m_mean,relative_humidity_2m_mean,wind_speed_10m_max,precipitation_sum"}
    try:
        resp = requests.get(ARCHIVE_URL, params=params, timeout=TIMEOUT_SECONDS)
        if resp.status_code != 200:
            return {"ok": False, "error": f"weather service returned status {resp.status_code}"}
        daily = resp.json()["daily"]
        return {"temperature_c": daily["temperature_2m_mean"][0],
                "humidity_pct": daily["relative_humidity_2m_mean"][0],
                "wind_kmh": daily["wind_speed_10m_max"][0],
                "rain_mm": daily["precipitation_sum"][0]}
    except Exception as exc:                 # network error, timeout, bad JSON
        return {"ok": False, "error": f"weather request failed: {exc}"}


def get_weather(city, date_text):
    if city not in COORDS:
        return {"ok": False, "error": f"unsupported city: {city}"}
    d = _valid_date(date_text)
    if d is None:
        return {"ok": False, "error": f"invalid date: {date_text}"}
    mode = os.environ.get("WEATHER_MODE", "stub").lower()
    values = _live(city, date_text) if mode == "live" else _stub(city, d)
    if values.get("ok") is False:
        return values
    out = {"ok": True, "city": city, "date": date_text, "mode": "live" if mode == "live" else "stub"}
    out.update(values)
    return out
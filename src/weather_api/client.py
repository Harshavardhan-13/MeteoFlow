import time
from datetime import UTC, datetime
from typing import Any

import httpx

from weather_api.locations import Location

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

WEATHER_FIELDS = (
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "is_day",
    "precipitation",
    "rain",
    "showers",
    "snowfall",
    "weather_code",
    "cloud_cover",
    "pressure_msl",
    "surface_pressure",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
)
DAILY_FIELDS = ("sunrise", "sunset", "daylight_duration", "sunshine_duration")
AIR_QUALITY_FIELDS = (
    "us_aqi",
    "pm2_5",
    "pm10",
    "ozone",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "carbon_monoxide",
    "uv_index",
)


class OpenMeteoClient:
    def __init__(self, timeout: float = 30, max_retries: int = 3) -> None:
        self.max_retries = max_retries
        self.client = httpx.Client(timeout=timeout)

    def __enter__(self) -> "OpenMeteoClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.client.close()

    def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self.client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError("Open-Meteo returned a non-object response")
                return payload
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt + 1 < self.max_retries:
                    time.sleep(2**attempt)
        raise RuntimeError("Open-Meteo request failed") from last_error

    @staticmethod
    def _base_params(location: Location) -> dict[str, Any]:
        return {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "timezone": location.timezone,
        }

    def fetch_weather(self, location: Location, past_days: int = 0) -> dict[str, Any]:
        params = self._base_params(location) | {
            "current": ",".join(WEATHER_FIELDS),
            "hourly": ",".join(WEATHER_FIELDS),
            "daily": ",".join(DAILY_FIELDS),
            "past_days": past_days,
            "forecast_days": 1,
        }
        return self._get(FORECAST_URL, params)

    def fetch_air_quality(
        self, location: Location, past_days: int = 0
    ) -> dict[str, Any]:
        params = self._base_params(location) | {
            "current": ",".join(AIR_QUALITY_FIELDS),
            "hourly": ",".join(AIR_QUALITY_FIELDS),
            "past_days": past_days,
            "forecast_days": 1,
        }
        return self._get(AIR_QUALITY_URL, params)


def fetched_at() -> str:
    return datetime.now(UTC).isoformat()

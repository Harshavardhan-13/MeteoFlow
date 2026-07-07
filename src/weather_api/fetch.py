import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from weather_api.client import OpenMeteoClient, fetched_at
from weather_api.conditions import condition_for
from weather_api.config import Settings
from weather_api.db import ensure_schema, latest_weather_times, save_results
from weather_api.locations import LOCATIONS, Location, get_location


def build_result(
    location: Location,
    weather_payload: dict[str, Any],
    air_quality_payload: dict[str, Any],
) -> dict[str, Any]:
    current = weather_payload.get("current")
    daily = weather_payload.get("daily")
    air_quality = air_quality_payload.get("current")
    if not isinstance(current, dict) or not isinstance(daily, dict):
        raise ValueError("Weather response is missing current or daily data")
    if not isinstance(air_quality, dict):
        raise ValueError("Air-quality response is missing current data")

    solar_by_date = {
        date: {
            "date": date,
            "sunrise": daily["sunrise"][index],
            "sunrise_symbol": "🌅",
            "sunset": daily["sunset"][index],
            "sunset_symbol": "🌇",
            "daylight_duration_seconds": daily["daylight_duration"][index],
            "sunshine_duration_seconds": daily["sunshine_duration"][index],
        }
        for index, date in enumerate(daily["time"])
    }
    solar = solar_by_date[current["time"][:10]]
    return build_observation(location, current, solar, air_quality)


def build_observation(
    location: Location,
    weather: dict[str, Any],
    solar: dict[str, Any],
    air_quality: dict[str, Any],
) -> dict[str, Any]:
    condition = condition_for(int(weather["weather_code"]), bool(weather["is_day"]))
    return {
        "location_slug": location.slug,
        "city": location.city,
        "state": location.state_code,
        "latitude": location.latitude,
        "longitude": location.longitude,
        "timezone": location.timezone,
        "fetched_at_utc": fetched_at(),
        "weather": weather
        | {"condition": condition.label, "weather_symbol": condition.symbol},
        "solar": solar,
        "air_quality": air_quality,
        "units": {
            "temperature": "°C",
            "precipitation": "mm",
            "snowfall": "cm",
            "wind": "km/h",
            "pressure": "hPa",
            "pollutants": "µg/m³",
        },
    }


def _series_rows(section: dict[str, Any]) -> dict[str, dict[str, Any]]:
    times = section.get("time")
    if not isinstance(times, list):
        raise ValueError("Hourly API response is missing its time series")
    rows: dict[str, dict[str, Any]] = {}
    for index, timestamp in enumerate(times):
        rows[timestamp] = {
            field: values[index]
            for field, values in section.items()
            if isinstance(values, list) and index < len(values)
        }
    return rows


def build_hourly_results(
    location: Location,
    weather_payload: dict[str, Any],
    air_quality_payload: dict[str, Any],
    after: datetime | None,
) -> list[dict[str, Any]]:
    hourly_weather = weather_payload.get("hourly")
    hourly_air_quality = air_quality_payload.get("hourly")
    daily = weather_payload.get("daily")
    sections = (hourly_weather, hourly_air_quality, daily)
    if not all(isinstance(section, dict) for section in sections):
        raise ValueError("Open-Meteo response is missing hourly or daily data")

    weather_rows = _series_rows(hourly_weather)
    air_quality_rows = _series_rows(hourly_air_quality)
    solar_rows = _series_rows(daily)
    timezone = ZoneInfo(location.timezone)
    now = datetime.now(timezone)
    after_local = after.astimezone(timezone) if after else None
    results: list[dict[str, Any]] = []

    for timestamp, weather in weather_rows.items():
        observed_at = datetime.fromisoformat(timestamp).replace(tzinfo=timezone)
        if observed_at > now or (after_local and observed_at <= after_local):
            continue
        air_quality = air_quality_rows.get(timestamp)
        solar = solar_rows.get(timestamp[:10])
        if air_quality and solar:
            results.append(build_observation(location, weather, solar, air_quality))
    return results


def fetch_locations(
    locations: tuple[Location, ...],
    latest_times: dict[str, datetime] | None = None,
) -> list[dict[str, Any]]:
    latest_times = latest_times or {}
    results: list[dict[str, Any]] = []
    with OpenMeteoClient() as client:
        for location in locations:
            after = latest_times.get(location.slug)
            local_today = datetime.now(ZoneInfo(location.timezone)).date()
            past_days = 0
            if after:
                last_local_date = after.astimezone(ZoneInfo(location.timezone)).date()
                past_days = (local_today - last_local_date).days
                if past_days > 92:
                    raise RuntimeError(
                        f"{location.city} has a gap longer than Open-Meteo's 92-day limit"
                    )
            weather_payload = client.fetch_weather(location, past_days=max(past_days, 0))
            air_quality_payload = client.fetch_air_quality(
                location, past_days=max(past_days, 0)
            )
            results.extend(
                build_hourly_results(
                    location, weather_payload, air_quality_payload, after
                )
            )

            current = build_result(location, weather_payload, air_quality_payload)
            current_time = datetime.fromisoformat(current["weather"]["time"]).replace(
                tzinfo=ZoneInfo(location.timezone)
            )
            if not after or current_time > after.astimezone(ZoneInfo(location.timezone)):
                results.append(current)
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch current Open-Meteo data")
    parser.add_argument(
        "--city",
        choices=[location.slug for location in LOCATIONS],
        help="Fetch one city; omit this option to fetch every city",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON output file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    locations = (get_location(args.city),) if args.city else LOCATIONS
    database_url = Settings.from_env().database_url
    ensure_schema(database_url)
    results = fetch_locations(locations, latest_weather_times(database_url))
    saved = save_results(database_url, results)
    output = json.dumps(results, ensure_ascii=False, indent=2)
    print(output)
    print(f"Saved {saved} new observation(s) to PostgreSQL.", file=sys.stderr)
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

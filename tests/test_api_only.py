from datetime import datetime
from zoneinfo import ZoneInfo

from weather_api.conditions import condition_for
from weather_api.db import observation_values
from weather_api.fetch import build_hourly_results, build_result
from weather_api.locations import LOCATIONS


def test_expected_locations_are_configured() -> None:
    assert [location.city for location in LOCATIONS] == [
        "New York",
        "Chicago",
        "San Francisco",
        "Las Vegas",
        "College Park",
        "Washington",
    ]


def test_clear_night_uses_moon_symbol() -> None:
    assert condition_for(0, False).symbol == "🌙"


def test_build_result_combines_weather_solar_and_aqi() -> None:
    weather = {
        "current": {
            "time": "2026-06-20T12:00",
            "temperature_2m": 27.0,
            "relative_humidity_2m": 55,
            "weather_code": 61,
            "is_day": 1,
        },
        "daily": {
            "time": ["2026-06-20"],
            "sunrise": ["2026-06-20T05:42"],
            "sunset": ["2026-06-20T20:37"],
            "daylight_duration": [53700],
            "sunshine_duration": [40000],
        },
    }
    air_quality = {"current": {"time": "2026-06-20T12:00", "us_aqi": 42}}

    result = build_result(LOCATIONS[4], weather, air_quality)

    assert result["city"] == "College Park"
    assert result["location_slug"] == "college-park-md"
    assert result["weather"]["temperature_2m"] == 27.0
    assert result["weather"]["weather_symbol"] == "🌦️"
    assert result["air_quality"]["us_aqi"] == 42

    values = observation_values(result)
    assert values["temperature_c"] == 27.0
    assert values["weather_observed_at"].tzinfo is not None


def test_hourly_results_only_include_rows_after_last_fetch() -> None:
    weather = {
        "hourly": {
            "time": ["2026-06-20T11:00", "2026-06-20T12:00"],
            "temperature_2m": [26.0, 27.0],
            "weather_code": [2, 1],
            "is_day": [1, 1],
        },
        "daily": {
            "time": ["2026-06-20"],
            "sunrise": ["2026-06-20T05:42"],
            "sunset": ["2026-06-20T20:37"],
            "daylight_duration": [53700],
            "sunshine_duration": [40000],
        },
    }
    air_quality = {
        "hourly": {
            "time": ["2026-06-20T11:00", "2026-06-20T12:00"],
            "us_aqi": [40, 42],
        }
    }
    after = datetime(2026, 6, 20, 11, 0, tzinfo=ZoneInfo("America/New_York"))

    results = build_hourly_results(LOCATIONS[4], weather, air_quality, after)

    assert [result["weather"]["time"] for result in results] == ["2026-06-20T12:00"]

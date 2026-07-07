from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import psycopg
from psycopg.types.json import Jsonb

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS weather_api_observations (
    id BIGSERIAL PRIMARY KEY,
    location_slug TEXT NOT NULL,
    city TEXT NOT NULL,
    state_code TEXT NOT NULL,
    timezone TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    weather_observed_at TIMESTAMPTZ NOT NULL,
    air_quality_observed_at TIMESTAMPTZ NOT NULL,
    temperature_c DOUBLE PRECISION NOT NULL,
    apparent_temperature_c DOUBLE PRECISION,
    relative_humidity_pct DOUBLE PRECISION,
    precipitation_mm DOUBLE PRECISION,
    rain_mm DOUBLE PRECISION,
    showers_mm DOUBLE PRECISION,
    snowfall_cm DOUBLE PRECISION,
    weather_code INTEGER,
    weather_condition TEXT,
    weather_symbol TEXT,
    cloud_cover_pct DOUBLE PRECISION,
    sea_level_pressure_hpa DOUBLE PRECISION,
    surface_pressure_hpa DOUBLE PRECISION,
    wind_speed_kmh DOUBLE PRECISION,
    wind_direction_deg DOUBLE PRECISION,
    wind_gusts_kmh DOUBLE PRECISION,
    sunrise_at TIMESTAMPTZ,
    sunset_at TIMESTAMPTZ,
    us_aqi DOUBLE PRECISION,
    pm2_5_ug_m3 DOUBLE PRECISION,
    pm10_ug_m3 DOUBLE PRECISION,
    ozone_ug_m3 DOUBLE PRECISION,
    nitrogen_dioxide_ug_m3 DOUBLE PRECISION,
    sulphur_dioxide_ug_m3 DOUBLE PRECISION,
    carbon_monoxide_ug_m3 DOUBLE PRECISION,
    uv_index DOUBLE PRECISION,
    raw_data JSONB NOT NULL,
    UNIQUE (location_slug, weather_observed_at, air_quality_observed_at)
);

CREATE INDEX IF NOT EXISTS weather_api_observations_city_time_idx
    ON weather_api_observations (city, weather_observed_at DESC);
"""

CREATE_LATEST_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS latest_weather_api_conditions
    (LIKE weather_api_observations INCLUDING DEFAULTS);

CREATE UNIQUE INDEX IF NOT EXISTS latest_weather_api_conditions_location_idx
    ON latest_weather_api_conditions (location_slug);
"""

REFRESH_LATEST_TABLE_SQL = """
TRUNCATE latest_weather_api_conditions;
INSERT INTO latest_weather_api_conditions
SELECT DISTINCT ON (location_slug) *
FROM weather_api_observations
ORDER BY location_slug, weather_observed_at DESC;
"""

INSERT_SQL = """
INSERT INTO weather_api_observations (
    location_slug, city, state_code, timezone, fetched_at,
    weather_observed_at, air_quality_observed_at,
    temperature_c, apparent_temperature_c, relative_humidity_pct,
    precipitation_mm, rain_mm, showers_mm, snowfall_cm,
    weather_code, weather_condition, weather_symbol, cloud_cover_pct,
    sea_level_pressure_hpa, surface_pressure_hpa,
    wind_speed_kmh, wind_direction_deg, wind_gusts_kmh,
    sunrise_at, sunset_at, us_aqi, pm2_5_ug_m3, pm10_ug_m3,
    ozone_ug_m3, nitrogen_dioxide_ug_m3, sulphur_dioxide_ug_m3,
    carbon_monoxide_ug_m3, uv_index, raw_data
) VALUES (
    %(location_slug)s, %(city)s, %(state_code)s, %(timezone)s, %(fetched_at)s,
    %(weather_observed_at)s, %(air_quality_observed_at)s,
    %(temperature_c)s, %(apparent_temperature_c)s, %(relative_humidity_pct)s,
    %(precipitation_mm)s, %(rain_mm)s, %(showers_mm)s, %(snowfall_cm)s,
    %(weather_code)s, %(weather_condition)s, %(weather_symbol)s, %(cloud_cover_pct)s,
    %(sea_level_pressure_hpa)s, %(surface_pressure_hpa)s,
    %(wind_speed_kmh)s, %(wind_direction_deg)s, %(wind_gusts_kmh)s,
    %(sunrise_at)s, %(sunset_at)s, %(us_aqi)s, %(pm2_5_ug_m3)s, %(pm10_ug_m3)s,
    %(ozone_ug_m3)s, %(nitrogen_dioxide_ug_m3)s, %(sulphur_dioxide_ug_m3)s,
    %(carbon_monoxide_ug_m3)s, %(uv_index)s, %(raw_data)s
)
ON CONFLICT (location_slug, weather_observed_at, air_quality_observed_at)
DO UPDATE SET
    fetched_at = EXCLUDED.fetched_at,
    temperature_c = EXCLUDED.temperature_c,
    apparent_temperature_c = EXCLUDED.apparent_temperature_c,
    relative_humidity_pct = EXCLUDED.relative_humidity_pct,
    precipitation_mm = EXCLUDED.precipitation_mm,
    rain_mm = EXCLUDED.rain_mm,
    showers_mm = EXCLUDED.showers_mm,
    snowfall_cm = EXCLUDED.snowfall_cm,
    weather_code = EXCLUDED.weather_code,
    weather_condition = EXCLUDED.weather_condition,
    weather_symbol = EXCLUDED.weather_symbol,
    cloud_cover_pct = EXCLUDED.cloud_cover_pct,
    sea_level_pressure_hpa = EXCLUDED.sea_level_pressure_hpa,
    surface_pressure_hpa = EXCLUDED.surface_pressure_hpa,
    wind_speed_kmh = EXCLUDED.wind_speed_kmh,
    wind_direction_deg = EXCLUDED.wind_direction_deg,
    wind_gusts_kmh = EXCLUDED.wind_gusts_kmh,
    sunrise_at = EXCLUDED.sunrise_at,
    sunset_at = EXCLUDED.sunset_at,
    us_aqi = EXCLUDED.us_aqi,
    pm2_5_ug_m3 = EXCLUDED.pm2_5_ug_m3,
    pm10_ug_m3 = EXCLUDED.pm10_ug_m3,
    ozone_ug_m3 = EXCLUDED.ozone_ug_m3,
    nitrogen_dioxide_ug_m3 = EXCLUDED.nitrogen_dioxide_ug_m3,
    sulphur_dioxide_ug_m3 = EXCLUDED.sulphur_dioxide_ug_m3,
    carbon_monoxide_ug_m3 = EXCLUDED.carbon_monoxide_ug_m3,
    uv_index = EXCLUDED.uv_index,
    raw_data = EXCLUDED.raw_data;
"""


def _local_timestamp(value: str, timezone: str) -> datetime:
    timestamp = datetime.fromisoformat(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=ZoneInfo(timezone))
    return timestamp


def observation_values(result: dict[str, Any]) -> dict[str, Any]:
    weather = result["weather"]
    solar = result["solar"]
    air_quality = result["air_quality"]
    timezone = result["timezone"]
    return {
        "location_slug": result["location_slug"],
        "city": result["city"],
        "state_code": result["state"],
        "timezone": timezone,
        "fetched_at": datetime.fromisoformat(result["fetched_at_utc"]),
        "weather_observed_at": _local_timestamp(weather["time"], timezone),
        "air_quality_observed_at": _local_timestamp(air_quality["time"], timezone),
        "temperature_c": weather["temperature_2m"],
        "apparent_temperature_c": weather.get("apparent_temperature"),
        "relative_humidity_pct": weather.get("relative_humidity_2m"),
        "precipitation_mm": weather.get("precipitation"),
        "rain_mm": weather.get("rain"),
        "showers_mm": weather.get("showers"),
        "snowfall_cm": weather.get("snowfall"),
        "weather_code": weather.get("weather_code"),
        "weather_condition": weather.get("condition"),
        "weather_symbol": weather.get("weather_symbol"),
        "cloud_cover_pct": weather.get("cloud_cover"),
        "sea_level_pressure_hpa": weather.get("pressure_msl"),
        "surface_pressure_hpa": weather.get("surface_pressure"),
        "wind_speed_kmh": weather.get("wind_speed_10m"),
        "wind_direction_deg": weather.get("wind_direction_10m"),
        "wind_gusts_kmh": weather.get("wind_gusts_10m"),
        "sunrise_at": _local_timestamp(solar["sunrise"], timezone),
        "sunset_at": _local_timestamp(solar["sunset"], timezone),
        "us_aqi": air_quality.get("us_aqi"),
        "pm2_5_ug_m3": air_quality.get("pm2_5"),
        "pm10_ug_m3": air_quality.get("pm10"),
        "ozone_ug_m3": air_quality.get("ozone"),
        "nitrogen_dioxide_ug_m3": air_quality.get("nitrogen_dioxide"),
        "sulphur_dioxide_ug_m3": air_quality.get("sulphur_dioxide"),
        "carbon_monoxide_ug_m3": air_quality.get("carbon_monoxide"),
        "uv_index": air_quality.get("uv_index"),
        "raw_data": Jsonb(result),
    }


def _ensure_schema(cursor: psycopg.Cursor[Any]) -> None:
    cursor.execute(CREATE_TABLE_SQL)
    cursor.execute(
        """
        SELECT c.relkind
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = current_schema()
          AND c.relname = 'latest_weather_api_conditions'
        """
    )
    relation = cursor.fetchone()
    if relation and relation[0] in {"v", "m"}:
        cursor.execute("DROP VIEW latest_weather_api_conditions")
    cursor.execute(CREATE_LATEST_TABLE_SQL)


def ensure_schema(database_url: str) -> None:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            _ensure_schema(cursor)
        connection.commit()


def latest_weather_times(database_url: str) -> dict[str, datetime]:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            _ensure_schema(cursor)
            cursor.execute(
                """
                SELECT location_slug, max(weather_observed_at)
                FROM weather_api_observations
                GROUP BY location_slug
                """
            )
            rows = cursor.fetchall()
        connection.commit()
    return {location_slug: observed_at for location_slug, observed_at in rows}


def save_results(database_url: str, results: list[dict[str, Any]]) -> int:
    with psycopg.connect(database_url) as connection:
        with connection.cursor() as cursor:
            _ensure_schema(cursor)
            for result in results:
                cursor.execute(INSERT_SQL, observation_values(result))
            cursor.execute(REFRESH_LATEST_TABLE_SQL)
        connection.commit()
    return len(results)

import pandas as pd
import psycopg
import streamlit as st
from psycopg.rows import dict_row

from weather_api.config import Settings
from weather_api.db import ensure_schema, latest_weather_times, save_results
from weather_api.fetch import fetch_locations
from weather_api.locations import LOCATIONS

DATABASE_URL = Settings.from_env().database_url

st.set_page_config(
    page_title="Weather Dashboard",
    page_icon="🌤️",
    layout="wide",
)


@st.cache_data(ttl=60)
def run_query(sql: str, parameters: tuple = ()) -> pd.DataFrame:
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql, parameters)
            return pd.DataFrame(cursor.fetchall())


def format_time(value: object) -> str:
    if pd.isna(value):
        return "Not available"
    if hasattr(value, "strftime"):
        return value.strftime("%b %d, %I:%M %p")
    return str(value)


def aqi_label(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "Unknown"
    if value <= 50:
        return "Good"
    if value <= 100:
        return "Moderate"
    if value <= 150:
        return "Unhealthy for sensitive groups"
    if value <= 200:
        return "Unhealthy"
    if value <= 300:
        return "Very unhealthy"
    return "Hazardous"


st.title("🌤️ Weather and Air Quality Dashboard")
st.caption(
    "Source: Open-Meteo weather and air-quality APIs. "
    "Data is stored in PostgreSQL and displayed from the latest weather table."
)

try:
    ensure_schema(DATABASE_URL)
except psycopg.OperationalError as exc:
    st.error("PostgreSQL is not reachable.")
    st.info(
        "Start the Docker database with `docker compose up -d`, "
        "then refresh this Streamlit page."
    )
    with st.expander("Technical error"):
        st.code(str(exc))
    st.stop()

if st.sidebar.button("Fetch latest API data"):
    with st.spinner("Fetching Open-Meteo data..."):
        results = fetch_locations(
            LOCATIONS,
            latest_weather_times(DATABASE_URL),
        )
        saved = save_results(DATABASE_URL, results)
        st.cache_data.clear()

    st.sidebar.success(f"Saved {saved} observations")
    st.rerun()

cities = run_query(
    """
    SELECT DISTINCT city
    FROM latest_weather_api_conditions
    ORDER BY city
    """
)

if cities.empty:
    st.warning("No weather data is stored yet.")
    st.info("Click **Fetch latest API data** in the sidebar to load data.")
    st.stop()

selected_city = st.sidebar.selectbox("Select a city", cities["city"])

summary = run_query(
    """
    SELECT
        city,
        state_code,
        weather_symbol,
        weather_condition,
        weather_observed_at AT TIME ZONE timezone AS local_time,
        temperature_c,
        relative_humidity_pct,
        wind_speed_kmh,
        precipitation_mm,
        snowfall_cm,
        us_aqi
    FROM latest_weather_api_conditions
    ORDER BY city
    """
)

latest = run_query(
    """
    SELECT
        city,
        state_code,
        weather_observed_at AT TIME ZONE timezone AS local_time,
        temperature_c,
        apparent_temperature_c,
        relative_humidity_pct,
        weather_symbol,
        weather_condition,
        wind_speed_kmh,
        wind_direction_deg,
        wind_gusts_kmh,
        precipitation_mm,
        rain_mm,
        showers_mm,
        snowfall_cm,
        us_aqi,
        pm2_5_ug_m3,
        pm10_ug_m3,
        ozone_ug_m3,
        uv_index,
        sunrise_at AT TIME ZONE timezone AS sunrise,
        sunset_at AT TIME ZONE timezone AS sunset
    FROM latest_weather_api_conditions
    WHERE city = %s
    """,
    (selected_city,),
)

if latest.empty:
    st.warning("No data is available for this city.")
    st.stop()

current = latest.iloc[0]

st.header(
    f"{current['weather_symbol']} "
    f"{current['city']}, {current['state_code']}"
)

st.caption(
    f"Observed: {format_time(current['local_time'])} — "
    f"{current['weather_condition']}"
)

temperature, feels_like, humidity, aqi = st.columns(4)

temperature.metric(
    "Temperature",
    f"{current['temperature_c']:.1f} °C",
)

feels_like.metric(
    "Feels like",
    f"{current['apparent_temperature_c']:.1f} °C",
)

humidity.metric(
    "Humidity",
    f"{current['relative_humidity_pct']:.0f}%",
)

aqi.metric(
    "US AQI",
    f"{current['us_aqi']:.0f}",
    aqi_label(current["us_aqi"]),
)

wind, gusts, precipitation, snow = st.columns(4)

wind.metric(
    "Wind speed",
    f"{current['wind_speed_kmh']:.1f} km/h",
)
gusts.metric(
    "Wind gusts",
    f"{current['wind_gusts_kmh']:.1f} km/h",
)
precipitation.metric(
    "🌧️ Precipitation",
    f"{current['precipitation_mm']:.1f} mm",
)
snow.metric(
    "❄️ Snowfall",
    f"{current['snowfall_cm']:.1f} cm",
)

sunrise, sunset, uv = st.columns(3)
sunrise.metric("🌅 Sunrise", format_time(current["sunrise"]))
sunset.metric("🌇 Sunset", format_time(current["sunset"]))
uv.metric("UV index", f"{current['uv_index']:.1f}")

history = run_query(
    """
    SELECT
        weather_observed_at AT TIME ZONE timezone AS local_time,
        temperature_c,
        apparent_temperature_c,
        relative_humidity_pct,
        wind_speed_kmh,
        precipitation_mm,
        us_aqi,
        pm2_5_ug_m3,
        pm10_ug_m3
    FROM weather_api_observations
    WHERE city = %s
    ORDER BY weather_observed_at
    """,
    (selected_city,),
)

overview_tab, trends_tab, air_tab, data_tab = st.tabs(
    ["Overview", "Trends", "Air quality", "Data table"]
)

with overview_tab:
    st.subheader("Latest conditions across all cities")
    readable_summary = summary.rename(
        columns={
            "city": "City",
            "state_code": "State",
            "weather_symbol": "Symbol",
            "weather_condition": "Condition",
            "local_time": "Observed",
            "temperature_c": "Temp °C",
            "relative_humidity_pct": "Humidity %",
            "wind_speed_kmh": "Wind km/h",
            "precipitation_mm": "Precip mm",
            "snowfall_cm": "Snow cm",
            "us_aqi": "US AQI",
        }
    )
    st.dataframe(
        readable_summary,
        width="stretch",
        hide_index=True,
        column_config={
            "Observed": st.column_config.DatetimeColumn(format="MMM DD, h:mm a"),
            "Temp °C": st.column_config.NumberColumn(format="%.1f"),
            "Humidity %": st.column_config.NumberColumn(format="%.0f"),
            "Wind km/h": st.column_config.NumberColumn(format="%.1f"),
            "Precip mm": st.column_config.NumberColumn(format="%.1f"),
            "Snow cm": st.column_config.NumberColumn(format="%.1f"),
            "US AQI": st.column_config.NumberColumn(format="%.0f"),
        },
    )

with trends_tab:
    st.subheader("Weather trends")
    if history.empty:
        st.warning("No historical rows are available for this city.")
    else:
        chart_data = history.set_index("local_time")
        st.line_chart(chart_data[["temperature_c", "apparent_temperature_c"]])
        st.line_chart(chart_data[["relative_humidity_pct", "wind_speed_kmh"]])
        st.bar_chart(chart_data[["precipitation_mm"]])

with air_tab:
    st.subheader("Air-quality trends")
    if history.empty:
        st.warning("No air-quality rows are available for this city.")
    else:
        air_chart = history.set_index("local_time")
        st.line_chart(air_chart[["us_aqi"]])
        st.line_chart(air_chart[["pm2_5_ug_m3", "pm10_ug_m3"]])
        st.caption(
            "US AQI is the main readability metric. PM2.5 and PM10 show pollutant concentration."
        )

with data_tab:
    st.subheader("Historical data")
    readable_history = history.rename(
        columns={
            "local_time": "Observed",
            "temperature_c": "Temp °C",
            "apparent_temperature_c": "Feels like °C",
            "relative_humidity_pct": "Humidity %",
            "wind_speed_kmh": "Wind km/h",
            "precipitation_mm": "Precip mm",
            "us_aqi": "US AQI",
            "pm2_5_ug_m3": "PM2.5 µg/m³",
            "pm10_ug_m3": "PM10 µg/m³",
        }
    )
    st.dataframe(
        readable_history,
        width="stretch",
        hide_index=True,
        column_config={
            "Observed": st.column_config.DatetimeColumn(format="MMM DD, h:mm a"),
            "Temp °C": st.column_config.NumberColumn(format="%.1f"),
            "Feels like °C": st.column_config.NumberColumn(format="%.1f"),
            "Humidity %": st.column_config.NumberColumn(format="%.0f"),
            "Wind km/h": st.column_config.NumberColumn(format="%.1f"),
            "Precip mm": st.column_config.NumberColumn(format="%.1f"),
            "US AQI": st.column_config.NumberColumn(format="%.0f"),
            "PM2.5 µg/m³": st.column_config.NumberColumn(format="%.1f"),
            "PM10 µg/m³": st.column_config.NumberColumn(format="%.1f"),
        },
    )

# Open-Meteo Weather ETL Pipeline

Python ETL pipeline that extracts weather and air-quality data from Open-Meteo,
loads incremental observations into PostgreSQL, and visualizes the latest and
historical conditions in Streamlit.

## What this project demonstrates

- API data ingestion from Open-Meteo weather and air-quality endpoints
- Incremental loading based on the latest stored observation timestamp
- PostgreSQL schema creation with constraints, indexes, and JSONB raw storage
- Docker Compose setup for local PostgreSQL
- Streamlit dashboard for readable weather and AQI exploration
- Basic automated tests

## Architecture

```text
Open-Meteo APIs
      ↓
Python extract/transform code
      ↓
PostgreSQL in Docker
      ↓
Streamlit dashboard
```

## Data collected

The pipeline currently tracks six U.S. locations:

- New York, NY
- Chicago, IL
- San Francisco, CA
- Las Vegas, NV
- College Park, MD
- Washington, DC

Stored fields include temperature, apparent temperature, humidity,
precipitation, rain, showers, snowfall, weather condition, weather symbol,
cloud cover, pressure, wind speed, wind direction, wind gusts, sunrise, sunset,
US AQI, PM2.5, PM10, ozone, nitrogen dioxide, sulfur dioxide, carbon monoxide,
UV index, and the raw API response as JSONB.

## Project structure

```text
.
├── docker-compose.yml              # Local PostgreSQL service
├── streamlit_app.py                # Streamlit dashboard
├── pyproject.toml                  # Package metadata and dependencies
├── requirements.txt                # Runtime dependencies
├── requirements-dev.txt            # Runtime + test/lint dependencies
├── src/weather_api/
│   ├── client.py                   # Open-Meteo API client
│   ├── config.py                   # Environment/database settings
│   ├── conditions.py               # Weather code to label/symbol mapping
│   ├── db.py                       # PostgreSQL schema and inserts
│   ├── fetch.py                    # ETL command-line entry point
│   └── locations.py                # City configuration
└── tests/
    └── test_api_only.py            # Unit tests for transformations
```

## Requirements

- Python 3.13
- Docker Desktop
- Git

No Open-Meteo API key is required.

## Quick start

Clone the repository and enter the project folder:

```bash
git clone <your-repository-url>
cd weather_etl_pipeline
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

Create the local environment file:

```bash
cp .env.example .env
```

Start PostgreSQL:

```bash
docker compose up -d
```

Fetch weather data:

```bash
python -m weather_api.fetch
```

Run the dashboard:

```bash
python -m streamlit run streamlit_app.py
```

Open the app:

```text
http://localhost:8501
```

## Database configuration

The default local database URL is:

```text
postgresql://weather_etl_user:weather_etl_password@localhost:5432/weather_etl
```

It matches the PostgreSQL service in `docker-compose.yml`.

To use a different database, set `DATABASE_URL` in `.env`:

```text
DATABASE_URL=postgresql://user:password@localhost:5432/database_name
```

## Main tables

The first fetch creates two tables:

- `weather_api_observations`: historical observations with one row per location
  and observation timestamp.
- `latest_weather_api_conditions`: one latest row per location, refreshed after
  each successful load.

The historical table uses a unique constraint on:

```text
location_slug, weather_observed_at, air_quality_observed_at
```

That prevents duplicate observations when the fetch command is run repeatedly.

## Common commands

Start PostgreSQL:

```bash
docker compose up -d
```

Check container status:

```bash
docker compose ps
```

Fetch all cities:

```bash
python -m weather_api.fetch
```

Fetch one city:

```bash
python -m weather_api.fetch --city college-park-md
```

Run Streamlit:

```bash
python -m streamlit run streamlit_app.py
```

Open `psql` inside the PostgreSQL container:

```bash
docker compose exec postgres psql -U weather_etl_user -d weather_etl
```

Query latest conditions:

```sql
SELECT city, weather_observed_at, temperature_c, weather_symbol, us_aqi
FROM latest_weather_api_conditions
ORDER BY city;
```

Stop PostgreSQL but keep data:

```bash
docker compose stop
```

Stop PostgreSQL and remove containers/network but keep the volume:

```bash
docker compose down
```

Delete the local database volume:

```bash
docker compose down -v
```

Use `down -v` carefully because it deletes the local PostgreSQL data.

## Testing and linting

Run tests:

```bash
pytest
```

Run lint checks:

```bash
ruff check .
```

Check installed dependencies:

```bash
python -m pip check
```

## Notes for GitHub

- `.env` is ignored so database credentials are not committed.
- `.env.example` is committed so other users know which variables to set.
- Python caches, virtual environments, generated package metadata, and local
  document/export files are ignored.

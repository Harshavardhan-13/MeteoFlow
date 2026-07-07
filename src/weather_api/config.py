import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DATABASE_URL = (
    "postgresql://weather_etl_user:weather_etl_password@localhost:5432/weather_etl"
)


def _load_dotenv() -> None:
    """Load simple KEY=VALUE pairs from a local .env file if it exists.

    This keeps the project easy to run without adding another dependency.
    Existing terminal environment variables win over values in .env.
    """
    project_root = Path(__file__).resolve().parents[2]
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        env_path = project_root / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        clean_line = line.strip()
        if not clean_line or clean_line.startswith("#") or "=" not in clean_line:
            continue
        key, value = clean_line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str

    @classmethod
    def from_env(cls) -> "Settings":
        _load_dotenv()
        return cls(database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL))

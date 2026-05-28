from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(*args, **kwargs):
        return False


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _as_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8001"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    storage_backend: str = os.getenv("COLLEGE_B_STORAGE", "mock")
    use_mock_externals: bool = _as_bool(os.getenv("USE_MOCK_EXTERNALS"), True)
    college_id: str = os.getenv("COLLEGE_ID", "B")
    integration_host: str = os.getenv("INTEGRATION_HOST", "http://localhost:8081")
    secret_key: str = os.getenv("SECRET_KEY", "changeme")
    oracle_dsn: str = os.getenv("ORACLE_DSN", "")
    oracle_user: str = os.getenv("ORACLE_USER", "")
    oracle_password: str = os.getenv("ORACLE_PASSWORD", "")

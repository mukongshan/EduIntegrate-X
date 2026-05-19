from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _as_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    storage_backend: str = os.getenv("COLLEGE_A_STORAGE", "mock")
    use_mock_externals: bool = _as_bool(os.getenv("USE_MOCK_EXTERNALS"), True)
    college_id: str = os.getenv("COLLEGE_ID", "A")
    integration_host: str = os.getenv("INTEGRATION_HOST", "http://localhost:8081")
    secret_key: str = os.getenv("SECRET_KEY", "changeme")
    mssql_server: str = os.getenv("MSSQL_SERVER", "")
    mssql_host: str = os.getenv("MSSQL_HOST", "")
    mssql_port: int = int(os.getenv("MSSQL_PORT", "1433"))
    mssql_database: str = os.getenv("MSSQL_DATABASE", "")
    mssql_driver: str = os.getenv("MSSQL_DRIVER", "ODBC Driver 18 for SQL Server")
    mssql_trusted_connection: bool = _as_bool(os.getenv("MSSQL_TRUSTED_CONNECTION"), True)
    mssql_user: str = os.getenv("MSSQL_USER", "")
    mssql_password: str = os.getenv("MSSQL_PASSWORD", "")

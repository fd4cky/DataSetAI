#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT_DIR / ".env"


def env_any(*keys: str, default=None):
    for key in keys:
        value = os.getenv(key)
        if value not in (None, ""):
            return value
    return default


def required_env(*keys: str, label: str | None = None) -> str:
    value = env_any(*keys)
    if value not in (None, ""):
        return value

    setting_name = label or keys[0]
    raise SystemExit(
        f"{setting_name} is not configured. Copy .env.example to .env and fill in "
        f"{keys[0]} before checking the database connection."
    )


def main() -> int:
    if not ENV_FILE.exists():
        raise SystemExit(
            "Missing .env file. Copy .env.example to .env before checking the database connection."
        )

    load_dotenv(ENV_FILE)

    connection_kwargs = {
        "dbname": required_env("DB_NAME", "POSTGRES_DB", label="DB_NAME"),
        "user": required_env("DB_USER", "POSTGRES_USER", label="DB_USER"),
        "password": required_env("DB_PASSWORD", "POSTGRES_PASSWORD", label="DB_PASSWORD"),
        "host": required_env("DB_HOST", "POSTGRES_HOST", label="DB_HOST"),
        "port": required_env("DB_PORT", "POSTGRES_PORT", label="DB_PORT"),
        "connect_timeout": 5,
    }

    try:
        with psycopg.connect(**connection_kwargs) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
    except Exception as exc:
        raise SystemExit(
            "Database connection failed. Make sure the SSH tunnel is running and the DB_* values "
            f"in .env are correct.\nDetails: {exc}"
        ) from exc

    print(
        "Database connection OK: "
        f"{connection_kwargs['user']}@{connection_kwargs['host']}:{connection_kwargs['port']}/"
        f"{connection_kwargs['dbname']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

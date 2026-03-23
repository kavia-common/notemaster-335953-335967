import os
from dataclasses import dataclass
from typing import Optional

import psycopg
from psycopg.rows import dict_row


@dataclass(frozen=True)
class DatabaseSettings:
    """Database connection settings resolved from environment variables."""

    url: str


def _normalize_postgres_url(url: str) -> str:
    """
    Normalize postgres connection URL.

    Some platforms provide `postgres://...` while psycopg expects `postgresql://...`.
    """
    if url.startswith("postgres://"):
        return "postgresql://" + url.removeprefix("postgres://")
    return url


def _build_postgres_url_from_env() -> str:
    """
    Build a postgres connection URL from POSTGRES_* environment variables.

    Contract:
      - If POSTGRES_URL is set, use it (after normalization).
      - Otherwise require POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT.
      - POSTGRES_HOST is optional (defaults to localhost).
    """
    url = os.getenv("POSTGRES_URL")
    if url:
        return _normalize_postgres_url(url)

    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    db = os.getenv("POSTGRES_DB")
    port = os.getenv("POSTGRES_PORT")
    host = os.getenv("POSTGRES_HOST", "localhost")

    missing = [
        k
        for k, v in [
            ("POSTGRES_USER", user),
            ("POSTGRES_PASSWORD", password),
            ("POSTGRES_DB", db),
            ("POSTGRES_PORT", port),
        ]
        if not v
    ]
    if missing:
        raise RuntimeError(
            "Database is not configured. Provide POSTGRES_URL or all of: "
            "POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_PORT. Missing: "
            + ", ".join(missing)
        )

    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


# PUBLIC_INTERFACE
def get_db_settings() -> DatabaseSettings:
    """
    Resolve DB settings from the runtime environment.

    Returns:
        DatabaseSettings: normalized settings used to establish DB connections.

    Raises:
        RuntimeError: if required env vars are missing.
    """
    return DatabaseSettings(url=_build_postgres_url_from_env())


# PUBLIC_INTERFACE
def get_connection() -> psycopg.Connection:
    """
    Create a new psycopg connection.

    Uses dict_row so queries can naturally return dict-like rows.

    Returns:
        psycopg.Connection: A new connection instance. Caller owns lifecycle (must close()).
    """
    settings = get_db_settings()
    return psycopg.connect(settings.url, row_factory=dict_row)


def fetch_one(conn: psycopg.Connection, query: str, params: Optional[dict] = None) -> Optional[dict]:
    """Fetch a single row as a dict (or None)."""
    with conn.cursor() as cur:
        cur.execute(query, params or {})
        return cur.fetchone()


def fetch_all(conn: psycopg.Connection, query: str, params: Optional[dict] = None) -> list[dict]:
    """Fetch all rows as a list of dicts."""
    with conn.cursor() as cur:
        cur.execute(query, params or {})
        return list(cur.fetchall())


def execute(conn: psycopg.Connection, query: str, params: Optional[dict] = None) -> int:
    """Execute a statement and return the affected rowcount."""
    with conn.cursor() as cur:
        cur.execute(query, params or {})
        return cur.rowcount

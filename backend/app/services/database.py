from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Generator

import psycopg
from psycopg.rows import dict_row

from app.config import get_database_url


@contextmanager
def connection() -> Generator[psycopg.Connection[Any], None, None]:
    conn = psycopg.connect(get_database_url(), row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()


def init_schema() -> None:
    """Create tables and indexes if missing (idempotent)."""
    try:
        _init_schema_inner()
    except psycopg.OperationalError as e:
        raise RuntimeError(
            "PostgreSQL connection failed. Typical fixes:\n"
            "  • Start the dev DB from backend/: docker compose up -d\n"
            "  • If you changed POSTGRES_PASSWORD after the first run, reset the volume: "
            "docker compose down -v && docker compose up -d\n"
            "  • If another Postgres uses the same host port, stop it or set BLOOM_DATABASE_URL "
            "(Compose defaults to 5433 on the host to avoid local Postgres on 5432).\n"
            f"  • Current DSN host/db (from env): {get_database_url().split('@', 1)[-1] if '@' in get_database_url() else get_database_url()}"
        ) from e


def _init_schema_inner() -> None:
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(32) NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT (TIMEZONE('utc', NOW()))
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS analyses (
                    id BIGSERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT (TIMEZONE('utc', NOW())),
                    full_text TEXT NOT NULL,
                    text_preview VARCHAR(600) NOT NULL,
                    summary_json JSONB NOT NULL,
                    analysis_json JSONB NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_analyses_user_created
                ON analyses (user_id, created_at DESC)
                """
            )
            cur.execute(
                """
                ALTER TABLE analyses
                ADD COLUMN IF NOT EXISTS characters_json JSONB NOT NULL DEFAULT '{}'::jsonb
                """
            )
        conn.commit()


def truncate_all_tables() -> None:
    """Remove all rows (for isolated tests)."""
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE analyses, users RESTART IDENTITY CASCADE")
        conn.commit()

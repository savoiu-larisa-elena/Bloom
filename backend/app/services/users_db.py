from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from app.services.database import connection, init_schema


def _ensure_schema() -> None:
    init_schema()


def username_valid(username: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_]{3,32}", username))


def create_user(username: str, password_hash: str) -> int:
    _ensure_schema()
    created = datetime.now(timezone.utc)
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (username, password_hash, created_at)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (username.lower(), password_hash, created),
            )
            row = cur.fetchone()
        conn.commit()
    assert row is not None
    return int(row["id"])


def get_user_by_username(username: str) -> dict[str, Any] | None:
    _ensure_schema()
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, password_hash FROM users WHERE username = %s",
                (username.lower().strip(),),
            )
            row = cur.fetchone()
    if not row:
        return None
    return {"id": int(row["id"]), "username": row["username"], "password_hash": row["password_hash"]}


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    _ensure_schema()
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, username FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
    if not row:
        return None
    return {"id": int(row["id"]), "username": row["username"]}


def get_user_by_id_with_hash(user_id: int) -> dict[str, Any] | None:
    """Like get_user_by_id but includes password_hash (server-side auth only)."""
    _ensure_schema()
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, username, password_hash FROM users WHERE id = %s",
                (user_id,),
            )
            row = cur.fetchone()
    if not row:
        return None
    return {
        "id": int(row["id"]),
        "username": row["username"],
        "password_hash": row["password_hash"],
    }


def update_user_credentials(
    user_id: int,
    *,
    new_username: str | None = None,
    new_password_hash: str | None = None,
) -> str:
    """Update username and/or password. Returns the username after update."""
    if new_username is None and new_password_hash is None:
        raise ValueError("Nothing to update")
    _ensure_schema()
    with connection() as conn:
        with conn.cursor() as cur:
            if new_username is not None and new_password_hash is not None:
                cur.execute(
                    "UPDATE users SET username = %s, password_hash = %s WHERE id = %s",
                    (new_username, new_password_hash, user_id),
                )
            elif new_username is not None:
                cur.execute(
                    "UPDATE users SET username = %s WHERE id = %s",
                    (new_username, user_id),
                )
            elif new_password_hash is not None:
                cur.execute(
                    "UPDATE users SET password_hash = %s WHERE id = %s",
                    (new_password_hash, user_id),
                )
            cur.execute("SELECT username FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
        conn.commit()
    assert row is not None
    return str(row["username"])

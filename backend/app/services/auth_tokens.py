from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

_ALGO = "HS256"
_DEFAULT_SECRET = "change-me-bloom-dev-only"


def _secret() -> str:
    return os.environ.get("BLOOM_JWT_SECRET", _DEFAULT_SECRET).strip() or _DEFAULT_SECRET


def create_access_token(*, user_id: int, username: str, expires_days: float | None = None) -> str:
    days = expires_days
    if days is None:
        days = float(os.environ.get("BLOOM_JWT_EXPIRE_DAYS", "14"))
    exp = datetime.now(timezone.utc) + timedelta(days=days)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "exp": exp,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, _secret(), algorithm=_ALGO)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, _secret(), algorithms=[_ALGO])

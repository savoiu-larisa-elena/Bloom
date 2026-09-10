from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.services.auth_tokens import decode_access_token
from app.services.users_db import get_user_by_id

_bearer = HTTPBearer(auto_error=False)


def get_optional_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> int | None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        uid = int(payload["sub"])
    except (JWTError, KeyError, TypeError, ValueError):
        return None
    if get_user_by_id(uid) is None:
        return None
    return uid


def get_required_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> int:
    uid = get_optional_user_id(credentials)
    if uid is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Sign in to access this resource.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return uid

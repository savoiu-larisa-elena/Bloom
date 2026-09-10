from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_optional_user_id, get_required_user_id
from app.schemas.auth import LoginRequest, ProfileUpdateRequest, RegisterRequest, TokenResponse
from app.services.auth_passwords import hash_password, verify_password
from app.services.auth_tokens import create_access_token
from app.services.users_db import (
    create_user,
    get_user_by_id,
    get_user_by_id_with_hash,
    get_user_by_username,
    update_user_credentials,
    username_valid,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest):
    u = body.username.strip().lower()
    if not username_valid(u):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be 3–32 characters: letters, digits, underscore only.",
        )
    if get_user_by_username(u):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken.")
    hid = create_user(u, hash_password(body.password))
    row = get_user_by_id(hid)
    assert row is not None
    token = create_access_token(user_id=hid, username=row["username"])
    return TokenResponse(access_token=token, username=row["username"], user_id=hid)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    row = get_user_by_username(body.username.strip().lower())
    if not row or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )
    token = create_access_token(user_id=row["id"], username=row["username"])
    return TokenResponse(access_token=token, username=row["username"], user_id=row["id"])


@router.get("/me")
def me(user_id: int = Depends(get_required_user_id)):
    row = get_user_by_id(user_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return {"user_id": row["id"], "username": row["username"]}


@router.patch("/me", response_model=TokenResponse)
def update_me(body: ProfileUpdateRequest, user_id: int = Depends(get_required_user_id)):
    row = get_user_by_id_with_hash(user_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    if not verify_password(body.current_password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        )

    new_username_lower: str | None = None
    if body.new_username is not None:
        nu = body.new_username.strip().lower()
        if nu != row["username"]:
            if not username_valid(nu):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username must be 3–32 characters: letters, digits, underscore only.",
                )
            if get_user_by_username(nu):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken.")
            new_username_lower = nu

    new_hash = hash_password(body.new_password) if body.new_password else None

    if new_username_lower is None and new_hash is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No changes: username is unchanged and no new password was provided.",
        )

    final_username = update_user_credentials(
        user_id,
        new_username=new_username_lower,
        new_password_hash=new_hash,
    )
    token = create_access_token(user_id=user_id, username=final_username)
    return TokenResponse(access_token=token, username=final_username, user_id=user_id)


@router.get("/session")
def session(user_id: int | None = Depends(get_optional_user_id)):
    if user_id is None:
        return {"authenticated": False}
    row = get_user_by_id(user_id)
    if not row:
        return {"authenticated": False}
    return {"authenticated": True, "user_id": row["id"], "username": row["username"]}

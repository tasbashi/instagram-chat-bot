"""Auth routes — register, login, me."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.config import settings
from app.deps import CurrentUser, DBSession
from app.models.user import User
from app.schemas import TokenOut, UserLogin, UserOut, UserRegister

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _create_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: UserRegister, db: DBSession) -> TokenOut:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=body.email,
        password_hash=bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode(),
        full_name=body.full_name,
    )
    db.add(user)
    await db.flush()

    return TokenOut(access_token=_create_token(str(user.id)))


@router.post("/login")
async def login(body: UserLogin, db: DBSession) -> TokenOut:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not bcrypt.checkpw(body.password.encode(), user.password_hash.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return TokenOut(access_token=_create_token(str(user.id)))


@router.get("/me")
async def me(current_user: CurrentUser) -> UserOut:
    return UserOut.model_validate(current_user)

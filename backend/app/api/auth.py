"""Auth routes — register, login, verify-email, resend-code, me."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.config import settings
from app.deps import CurrentUser, DBSession
from app.models.user import User
from app.schemas import (
    RegisterOut,
    ResendCodeRequest,
    TokenOut,
    UserLogin,
    UserOut,
    UserRegister,
    VerifyEmailRequest,
)
from app.services.email_service import send_verification_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _create_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _generate_code() -> str:
    """Generate a 6-digit numeric verification code."""
    return f"{secrets.randbelow(1_000_000):06d}"


# ── Register ────────────────────────────────────────────────────────


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: UserRegister, db: DBSession) -> RegisterOut:
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    code = _generate_code()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.verification_code_expiry_minutes
    )

    user = User(
        email=body.email,
        password_hash=bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode(),
        full_name=body.full_name,
        verification_code=code,
        verification_code_expires_at=expires_at,
    )
    db.add(user)
    await db.flush()

    await send_verification_email(body.email, code)

    return RegisterOut(
        message="Verification code sent to your email",
        email=body.email,
    )


# ── Verify Email ────────────────────────────────────────────────────


@router.post("/verify-email")
async def verify_email(body: VerifyEmailRequest, db: DBSession) -> TokenOut:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.is_email_verified:
        return TokenOut(access_token=_create_token(str(user.id)))

    if not user.verification_code or not user.verification_code_expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No verification code found. Please request a new one.",
        )

    if datetime.now(timezone.utc) > user.verification_code_expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a new one.",
        )

    if user.verification_code != body.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code",
        )

    user.is_email_verified = True
    user.verification_code = None
    user.verification_code_expires_at = None
    await db.flush()

    return TokenOut(access_token=_create_token(str(user.id)))


# ── Resend Code ─────────────────────────────────────────────────────


@router.post("/resend-code")
async def resend_code(body: ResendCodeRequest, db: DBSession) -> RegisterOut:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified",
        )

    # Rate limit: can't resend if previous code has more than 4 min left
    if user.verification_code_expires_at:
        remaining = (user.verification_code_expires_at - datetime.now(timezone.utc)).total_seconds()
        if remaining > (settings.verification_code_expiry_minutes - 1) * 60:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Please wait before requesting a new code",
            )

    code = _generate_code()
    user.verification_code = code
    user.verification_code_expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.verification_code_expiry_minutes
    )
    await db.flush()

    await send_verification_email(body.email, code)

    return RegisterOut(
        message="Verification code sent to your email",
        email=body.email,
    )


# ── Login ───────────────────────────────────────────────────────────


@router.post("/login")
async def login(body: UserLogin, db: DBSession) -> TokenOut:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user or not bcrypt.checkpw(body.password.encode(), user.password_hash.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified",
        )

    return TokenOut(access_token=_create_token(str(user.id)))


# ── Me ──────────────────────────────────────────────────────────────


@router.get("/me")
async def me(current_user: CurrentUser) -> UserOut:
    return UserOut.model_validate(current_user)

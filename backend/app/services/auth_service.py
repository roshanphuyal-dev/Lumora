import asyncio
import uuid

from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    InvalidTokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import TokenResponse


def _issue_tokens(user_id: uuid.UUID) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


async def register_user(db: AsyncSession, email: str, password: str, full_name: str) -> User:
    existing = await db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    user = User(
        email=email,
        hashed_password=await hash_password(password),
        full_name=full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> TokenResponse:
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
    )
    user = await db.scalar(select(User).where(User.email == email))
    if user is None or user.hashed_password is None:
        raise invalid_credentials
    if not await verify_password(password, user.hashed_password):
        raise invalid_credentials
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    return _issue_tokens(user.id)


async def login_with_google(db: AsyncSession, google_token: str) -> TokenResponse:
    settings = get_settings()
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google login is not configured",
        )

    try:
        claims = await asyncio.to_thread(
            google_id_token.verify_oauth2_token,
            google_token,
            google_requests.Request(),
            settings.google_client_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token"
        ) from exc

    google_id = claims["sub"]
    email = claims["email"]

    user = await db.scalar(select(User).where(User.google_id == google_id))
    if user is None:
        user = await db.scalar(select(User).where(User.email == email))
        if user is not None:
            user.google_id = google_id
        else:
            user = User(
                email=email,
                google_id=google_id,
                full_name=claims.get("name", email),
            )
            db.add(user)
        await db.commit()
        await db.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    return _issue_tokens(user.id)


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenResponse:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
    )
    try:
        user_id = decode_token(refresh_token, TokenType.REFRESH)
    except InvalidTokenError as exc:
        raise unauthorized from exc

    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None or not user.is_active:
        raise unauthorized

    return _issue_tokens(user.id)

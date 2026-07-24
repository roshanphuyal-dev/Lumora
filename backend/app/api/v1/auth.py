from fastapi import APIRouter, status

from app.core.dependencies import DbSession
from app.schemas.auth import (
    GoogleLoginRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserRead
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: DbSession) -> UserRead:
    user = await auth_service.register_user(db, payload.email, payload.password, payload.full_name)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    return await auth_service.authenticate_user(db, payload.email, payload.password)


@router.post("/google", response_model=TokenResponse)
async def login_google(payload: GoogleLoginRequest, db: DbSession) -> TokenResponse:
    return await auth_service.login_with_google(db, payload.id_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: DbSession) -> TokenResponse:
    return await auth_service.refresh_tokens(db, payload.refresh_token)

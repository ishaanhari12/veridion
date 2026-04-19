import uuid
import os

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.core.security import get_current_user_payload, require_any_user
from app.db.session import get_db
from app.models.models import User
from app.schemas.auth import (
    RefreshRequest,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
    WalletResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])
limiter = Limiter(key_func=get_remote_address)

# In production, enforce strict limits to prevent brute force attacks.
# In development/test, use very high limits so tests are never blocked.
_env = os.getenv("ENVIRONMENT", "development")
_IS_PROD = _env == "production"
_REGISTER_LIMIT = "10/minute" if _IS_PROD else "1000/minute"
_LOGIN_LIMIT    = "10/minute" if _IS_PROD else "1000/minute"
_REFRESH_LIMIT  = "20/minute" if _IS_PROD else "1000/minute"


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit(_REGISTER_LIMIT)
def register(
    request: Request,
    data: UserRegister,
    db: Session = Depends(get_db),
):
    """
    Register a new user account.
    A GBP wallet is created automatically.
    Rate limited to 10/minute per IP in production.
    """
    ip = request.client.host if request.client else None
    return AuthService.register(db, data, ip)


@router.post("/login", response_model=TokenResponse)
@limiter.limit(_LOGIN_LIMIT)
def login(
    request: Request,
    data: UserLogin,
    db: Session = Depends(get_db),
):
    """
    Authenticate with email and password.
    Returns JWT access token (30 min) and refresh token (7 days).
    Rate limited to 10/minute in production to prevent brute force.
    """
    ip = request.client.host if request.client else None
    return AuthService.login(db, data, ip)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit(_REFRESH_LIMIT)
def refresh(
    request: Request,
    data: RefreshRequest,
    db: Session = Depends(get_db),
):
    """Exchange a valid refresh token for a new token pair."""
    return AuthService.refresh(db, data.refresh_token)


@router.get("/me", response_model=UserResponse)
def me(
    payload: dict = Depends(require_any_user),
    db: Session = Depends(get_db),
):
    """Return the currently authenticated user profile."""
    user = db.query(User).filter(
        User.id == uuid.UUID(payload["sub"])
    ).first()
    return user


@router.get("/me/wallet", response_model=WalletResponse)
def my_wallet(
    payload: dict = Depends(require_any_user),
    db: Session = Depends(get_db),
):
    """Return the authenticated user wallet balance."""
    user = db.query(User).filter(
        User.id == uuid.UUID(payload["sub"])
    ).first()
    return user.wallet

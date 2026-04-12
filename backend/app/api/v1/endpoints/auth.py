import uuid

from fastapi import APIRouter, Depends, Request
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


@router.post("/register", response_model=UserResponse, status_code=201)
def register(data: UserRegister, request: Request, db: Session = Depends(get_db)):
    """
    Register a new user account.
    A GBP wallet is created automatically on registration.
    """
    ip = request.client.host if request.client else None
    return AuthService.register(db, data, ip)


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, request: Request, db: Session = Depends(get_db)):
    """
    Authenticate with email and password.
    Returns a JWT access token (30 min) and refresh token (7 days).
    """
    ip = request.client.host if request.client else None
    return AuthService.login(db, data, ip)


@router.post("/refresh", response_model=TokenResponse)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new token pair."""
    return AuthService.refresh(db, data.refresh_token)


@router.get("/me", response_model=UserResponse)
def me(
    payload: dict = Depends(require_any_user),
    db: Session = Depends(get_db),
):
    """Return the currently authenticated user's profile."""
    user = db.query(User).filter(User.id == uuid.UUID(payload["sub"])).first()
    return user


@router.get("/me/wallet", response_model=WalletResponse)
def my_wallet(
    payload: dict = Depends(require_any_user),
    db: Session = Depends(get_db),
):
    """Return the authenticated user's wallet balance."""
    user = db.query(User).filter(User.id == uuid.UUID(payload["sub"])).first()
    return user.wallet

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.models import User, Wallet, AuditLog
from app.schemas.auth import UserRegister, UserLogin, TokenResponse


class AuthService:

    @staticmethod
    def register(db: Session, data: UserRegister, ip: str | None = None) -> User:
        if db.query(User).filter(User.email == data.email).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )

        user = User(
            email=data.email,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            role="user",
        )
        db.add(user)
        db.flush()  # get user.id before committing

        # Every new user gets a wallet automatically
        wallet = Wallet(user_id=user.id, balance=Decimal("0.00"), currency="GBP")
        db.add(wallet)

        # Audit log
        db.add(AuditLog(
            user_id=user.id,
            action="register",
            resource="user",
            resource_id=str(user.id),
            ip_address=ip,
            details=f"New user registered: {user.email}",
        ))

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def login(db: Session, data: UserLogin, ip: str | None = None) -> TokenResponse:
        user = db.query(User).filter(User.email == data.email).first()

        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled",
            )
        if user.is_blacklisted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is restricted",
            )

        db.add(AuditLog(
            user_id=user.id,
            action="login",
            resource="user",
            resource_id=str(user.id),
            ip_address=ip,
            details="Successful login",
        ))
        db.commit()

        return TokenResponse(
            access_token=create_access_token(user.id, user.role),
            refresh_token=create_refresh_token(user.id),
        )

    @staticmethod
    def refresh(db: Session, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        user = db.query(User).filter(User.id == payload["sub"]).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        return TokenResponse(
            access_token=create_access_token(user.id, user.role),
            refresh_token=create_refresh_token(user.id),
        )

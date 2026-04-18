import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey,
    Index, Numeric, String, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# ─── Enums ────────────────────────────────────────────────────────────────────

class TransactionStatus(str, PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FLAGGED = "flagged"
    BLOCKED = "blocked"
    FAILED = "failed"


class TransactionType(str, PyEnum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"


# ─── User ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_blacklisted: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    wallet: Mapped["Wallet"] = relationship(
        "Wallet", back_populates="user",
        uselist=False, cascade="all, delete-orphan"
    )
    sent_transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", foreign_keys="Transaction.sender_id",
        back_populates="sender"
    )
    received_transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", foreign_keys="Transaction.receiver_id",
        back_populates="receiver"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="user"
    )


# ─── Wallet ───────────────────────────────────────────────────────────────────

class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"),
        unique=True, nullable=False
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=2), nullable=False, default=Decimal("0.00")
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    user: Mapped["User"] = relationship("User", back_populates="wallet")


# ─── Transaction ──────────────────────────────────────────────────────────────

class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sender_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    receiver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=18, scale=2), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")
    transaction_type: Mapped[str] = mapped_column(
        Enum(TransactionType), nullable=False
    )
    status: Mapped[str] = mapped_column(
        Enum(TransactionStatus), nullable=False,
        default=TransactionStatus.PENDING
    )
    fraud_score: Mapped[float | None] = mapped_column(
        Numeric(precision=5, scale=4), nullable=True
    )
    fraud_flagged: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    sender: Mapped["User"] = relationship(
        "User", foreign_keys=[sender_id], back_populates="sent_transactions"
    )
    receiver: Mapped["User"] = relationship(
        "User", foreign_keys=[receiver_id], back_populates="received_transactions"
    )

    __table_args__ = (
        Index("ix_transactions_sender_created", "sender_id", "created_at"),
        Index("ix_transactions_status", "status"),
        Index("ix_transactions_fraud_flagged", "fraud_flagged"),
    )


# ─── AuditLog ─────────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    user: Mapped["User"] = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
        Index("ix_audit_logs_action", "action"),
    )

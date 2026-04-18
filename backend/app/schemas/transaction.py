import math
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator


# ─── Requests ─────────────────────────────────────────────────────────────────

class DepositRequest(BaseModel):
    amount: Decimal

    @field_validator("amount")
    @classmethod
    def amount_valid(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be greater than zero")
        if v > Decimal("100000"):
            raise ValueError("Single deposit cannot exceed £100,000")
        return round(v, 2)


class WithdrawRequest(BaseModel):
    amount: Decimal

    @field_validator("amount")
    @classmethod
    def amount_valid(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be greater than zero")
        return round(v, 2)


class TransferRequest(BaseModel):
    receiver_email: str
    amount: Decimal
    description: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_valid(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be greater than zero")
        if v > Decimal("50000"):
            raise ValueError("Single transfer cannot exceed £50,000")
        return round(v, 2)


class AdminStatusUpdate(BaseModel):
    new_status: str


# ─── Responses ────────────────────────────────────────────────────────────────

class TransactionResponse(BaseModel):
    id: uuid.UUID
    sender_id: uuid.UUID | None
    receiver_id: uuid.UUID | None
    amount: Decimal
    currency: str
    transaction_type: str
    status: str
    fraud_score: float | None
    fraud_flagged: bool
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedTransactions(BaseModel):
    items: list[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

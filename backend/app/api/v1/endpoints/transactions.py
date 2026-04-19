import uuid
import os

from fastapi import APIRouter, Depends, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.core.security import require_analyst_or_admin, require_any_user
from app.db.session import get_db
from app.schemas.transaction import (
    AdminStatusUpdate,
    DepositRequest,
    PaginatedTransactions,
    TransactionResponse,
    TransferRequest,
    WithdrawRequest,
)
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/transactions", tags=["Transactions"])
limiter = Limiter(key_func=get_remote_address)

_env = os.getenv("ENVIRONMENT", "development")
_IS_PROD = _env == "production"
_DEPOSIT_LIMIT  = "30/minute" if _IS_PROD else "1000/minute"
_WITHDRAW_LIMIT = "30/minute" if _IS_PROD else "1000/minute"
_TRANSFER_LIMIT = "20/minute" if _IS_PROD else "1000/minute"


@router.post("/deposit", response_model=TransactionResponse, status_code=201)
@limiter.limit(_DEPOSIT_LIMIT)
def deposit(
    request: Request,
    data: DepositRequest,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_any_user),
):
    """Add funds to your wallet. Rate limited to 30/minute in production."""
    return TransactionService.deposit(db, payload, data, request)


@router.post("/withdraw", response_model=TransactionResponse, status_code=201)
@limiter.limit(_WITHDRAW_LIMIT)
def withdraw(
    request: Request,
    data: WithdrawRequest,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_any_user),
):
    """Withdraw funds from your wallet. Rate limited to 30/minute in production."""
    return TransactionService.withdraw(db, payload, data, request)


@router.post("/transfer", response_model=TransactionResponse, status_code=201)
@limiter.limit(_TRANSFER_LIMIT)
def transfer(
    request: Request,
    data: TransferRequest,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_any_user),
):
    """
    Transfer funds to another user by email.
    Every transfer is fraud-scored before money moves.
    Rate limited to 20/minute in production — lower due to fraud risk.
    """
    return TransactionService.transfer(db, payload, data, request)


@router.get("/history", response_model=PaginatedTransactions)
def history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    payload: dict = Depends(require_any_user),
):
    """Get your transaction history, newest first."""
    return TransactionService.get_history(db, payload, page, page_size, status)


@router.patch("/{transaction_id}/status", response_model=TransactionResponse)
def update_status(
    transaction_id: uuid.UUID,
    data: AdminStatusUpdate,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_analyst_or_admin),
):
    """Manually approve or block a flagged transaction. Analyst/admin only."""
    return TransactionService.admin_update_status(
        db, payload, transaction_id, data.new_status
    )

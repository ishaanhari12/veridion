import uuid

from fastapi import APIRouter, Depends, Query, Request
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


@router.post("/deposit", response_model=TransactionResponse, status_code=201)
def deposit(
    data: DepositRequest,
    request: Request,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_any_user),
):
    """
    Add funds to your wallet.
    Any authenticated user can deposit. No fraud scoring on deposits.
    """
    return TransactionService.deposit(db, payload, data, request)


@router.post("/withdraw", response_model=TransactionResponse, status_code=201)
def withdraw(
    data: WithdrawRequest,
    request: Request,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_any_user),
):
    """
    Withdraw funds from your wallet.
    Will fail with 422 if you have insufficient balance.
    """
    return TransactionService.withdraw(db, payload, data, request)


@router.post("/transfer", response_model=TransactionResponse, status_code=201)
def transfer(
    data: TransferRequest,
    request: Request,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_any_user),
):
    """
    Transfer funds to another user by their email address.

    Every transfer is scored by the fraud engine before money moves:
    - Score > 0.85 → BLOCKED (money does not move)
    - Score > 0.50 → FLAGGED (money moves, flagged for analyst review)
    - Score <= 0.50 → COMPLETED (normal transaction)
    """
    return TransactionService.transfer(db, payload, data, request)


@router.get("/history", response_model=PaginatedTransactions)
def history(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Results per page"),
    status: str | None = Query(default=None, description="Filter by status"),
    db: Session = Depends(get_db),
    payload: dict = Depends(require_any_user),
):
    """
    Get your transaction history, newest first.
    Optionally filter by status: pending, completed, flagged, blocked, failed.
    """
    return TransactionService.get_history(db, payload, page, page_size, status)


@router.patch("/{transaction_id}/status", response_model=TransactionResponse)
def update_status(
    transaction_id: uuid.UUID,
    data: AdminStatusUpdate,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_analyst_or_admin),
):
    """
    Manually approve or block a flagged transaction.
    Requires analyst or admin role. Every change is audit logged.
    """
    return TransactionService.admin_update_status(
        db, payload, transaction_id, data.new_status
    )

import math
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    AuditLog, Transaction, TransactionStatus,
    TransactionType, User,
)
from app.schemas.transaction import (
    DepositRequest, PaginatedTransactions,
    TransferRequest, WithdrawRequest,
)
from app.services.audit_service import AuditService
from app.services.fraud_client import FraudClient


def _get_user(db: Session, payload: dict) -> User:
    """Fetch the authenticated user from the database."""
    user = db.query(User).filter(
        User.id == uuid.UUID(payload["sub"])
    ).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


def _sender_stats(db: Session, sender_id: uuid.UUID) -> tuple[float, int]:
    """
    Calculate two ML features for fraud scoring:
    1. The sender's historical average transaction amount
    2. How many transactions they've sent in the last 5 minutes (velocity)
    High velocity + unusual amount = likely fraud.
    """
    five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)

    avg = db.query(func.avg(Transaction.amount)).filter(
        Transaction.sender_id == sender_id,
        Transaction.status == TransactionStatus.COMPLETED,
    ).scalar()

    recent_count = db.query(func.count(Transaction.id)).filter(
        Transaction.sender_id == sender_id,
        Transaction.created_at >= five_min_ago,
    ).scalar()

    return float(avg or 0.0), int(recent_count or 0)


class TransactionService:

    # ── Deposit ───────────────────────────────────────────────────────────────

    @staticmethod
    def deposit(
        db: Session,
        payload: dict,
        data: DepositRequest,
        request: Request | None = None,
    ) -> Transaction:
        user = _get_user(db, payload)
        ip = request.client.host if request and request.client else None

        # Create transaction record
        txn = Transaction(
            receiver_id=user.id,
            amount=data.amount,
            currency=user.wallet.currency,
            transaction_type=TransactionType.DEPOSIT,
            status=TransactionStatus.COMPLETED,
            ip_address=ip,
        )
        db.add(txn)

        # Credit the wallet — atomically with the transaction record
        user.wallet.balance += data.amount

        AuditService.log(
            db,
            action="deposit",
            resource="transaction",
            user_id=user.id,
            resource_id=str(txn.id),
            ip_address=ip,
            details=f"Deposited £{data.amount}",
        )

        db.commit()
        db.refresh(txn)
        return txn

    # ── Withdrawal ────────────────────────────────────────────────────────────

    @staticmethod
    def withdraw(
        db: Session,
        payload: dict,
        data: WithdrawRequest,
        request: Request | None = None,
    ) -> Transaction:
        user = _get_user(db, payload)
        ip = request.client.host if request and request.client else None

        if user.wallet.balance < data.amount:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Insufficient funds. Current balance: £{user.wallet.balance}",
            )

        txn = Transaction(
            sender_id=user.id,
            amount=data.amount,
            currency=user.wallet.currency,
            transaction_type=TransactionType.WITHDRAWAL,
            status=TransactionStatus.COMPLETED,
            ip_address=ip,
        )
        db.add(txn)

        # Debit the wallet atomically
        user.wallet.balance -= data.amount

        AuditService.log(
            db,
            action="withdrawal",
            resource="transaction",
            user_id=user.id,
            resource_id=str(txn.id),
            ip_address=ip,
            details=f"Withdrew £{data.amount}",
        )

        db.commit()
        db.refresh(txn)
        return txn

    # ── Transfer ──────────────────────────────────────────────────────────────

    @staticmethod
    def transfer(
        db: Session,
        payload: dict,
        data: TransferRequest,
        request: Request | None = None,
    ) -> Transaction:
        sender = _get_user(db, payload)
        ip = request.client.host if request and request.client else None

        # Basic validations before touching the database
        if str(sender.email) == data.receiver_email:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="You cannot transfer money to yourself",
            )

        receiver = db.query(User).filter(
            User.email == data.receiver_email
        ).first()
        if not receiver or not receiver.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipient not found",
            )

        if sender.wallet.balance < data.amount:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Insufficient funds. Current balance: £{sender.wallet.balance}",
            )

        # Build ML features for fraud scoring
        avg_amount, recent_count = _sender_stats(db, sender.id)
        is_new_receiver = not db.query(Transaction).filter(
            Transaction.sender_id == sender.id,
            Transaction.receiver_id == receiver.id,
            Transaction.status == TransactionStatus.COMPLETED,
        ).first()

        # Create transaction in PENDING state — money has not moved yet
        txn = Transaction(
            sender_id=sender.id,
            receiver_id=receiver.id,
            amount=data.amount,
            currency=sender.wallet.currency,
            transaction_type=TransactionType.TRANSFER,
            status=TransactionStatus.PENDING,
            description=data.description,
            ip_address=ip,
        )
        db.add(txn)
        db.flush()  # Gets txn.id without committing — needed for fraud scoring

        # Score the transaction with the fraud engine
        fraud_result = FraudClient.score(
            transaction_id=str(txn.id),
            amount=float(data.amount),
            sender_id=str(sender.id),
            sender_avg_amount=avg_amount,
            sender_tx_count_last_5min=recent_count,
            is_new_receiver=is_new_receiver,
        )
        score = float(fraud_result["fraud_score"])
        txn.fraud_score = score

        # ── Decision gate ─────────────────────────────────────────────────────
        # This is the core of the platform. Based on the fraud score:
        # > 0.85 = BLOCK  — money does not move
        # > 0.50 = FLAG   — money moves but marked for analyst review
        # <= 0.50 = PASS  — normal completed transaction

        if score >= settings.fraud_block_threshold:
            txn.status = TransactionStatus.BLOCKED
            txn.fraud_flagged = True
            AuditService.log(
                db,
                action="transfer_blocked",
                resource="transaction",
                user_id=sender.id,
                resource_id=str(txn.id),
                ip_address=ip,
                details=f"Blocked. Fraud score: {score:.4f}. Amount: £{data.amount}",
            )

        elif score >= settings.fraud_flag_threshold:
            # Money moves but flagged for review
            txn.status = TransactionStatus.FLAGGED
            txn.fraud_flagged = True
            sender.wallet.balance -= data.amount
            receiver.wallet.balance += data.amount
            AuditService.log(
                db,
                action="transfer_flagged",
                resource="transaction",
                user_id=sender.id,
                resource_id=str(txn.id),
                ip_address=ip,
                details=f"Flagged. Fraud score: {score:.4f}. Amount: £{data.amount}",
            )

        else:
            # Clean transaction — debit sender, credit receiver atomically
            txn.status = TransactionStatus.COMPLETED
            sender.wallet.balance -= data.amount
            receiver.wallet.balance += data.amount
            AuditService.log(
                db,
                action="transfer_completed",
                resource="transaction",
                user_id=sender.id,
                resource_id=str(txn.id),
                ip_address=ip,
                details=f"Completed. Amount: £{data.amount}. Score: {score:.4f}",
            )

        db.commit()
        db.refresh(txn)
        return txn

    # ── History ───────────────────────────────────────────────────────────────

    @staticmethod
    def get_history(
        db: Session,
        payload: dict,
        page: int = 1,
        page_size: int = 20,
        status_filter: str | None = None,
    ) -> PaginatedTransactions:
        user = _get_user(db, payload)
        page_size = min(page_size, 100)  # cap at 100 per page

        query = db.query(Transaction).filter(
            (Transaction.sender_id == user.id) |
            (Transaction.receiver_id == user.id)
        )

        if status_filter:
            query = query.filter(Transaction.status == status_filter)

        total = query.count()
        items = (
            query
            .order_by(Transaction.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return PaginatedTransactions(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=max(1, math.ceil(total / page_size)),
        )

    # ── Admin: update status ──────────────────────────────────────────────────

    @staticmethod
    def admin_update_status(
        db: Session,
        payload: dict,
        transaction_id: uuid.UUID,
        new_status: str,
    ) -> Transaction:
        """
        Allows an admin or analyst to manually approve or block
        a flagged transaction after reviewing it.
        """
        allowed = {TransactionStatus.COMPLETED.value, TransactionStatus.BLOCKED.value}
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Status must be one of: {list(allowed)}",
            )

        txn = db.query(Transaction).filter(
            Transaction.id == transaction_id
        ).first()
        if not txn:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transaction not found",
            )

        old_status = txn.status
        txn.status = new_status

        AuditService.log(
            db,
            action="admin_status_update",
            resource="transaction",
            user_id=uuid.UUID(payload["sub"]),
            resource_id=str(txn.id),
            details=f"Status changed: {old_status} → {new_status}",
        )

        db.commit()
        db.refresh(txn)
        return txn

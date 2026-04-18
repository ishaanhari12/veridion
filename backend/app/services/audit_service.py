import uuid
from sqlalchemy.orm import Session
from app.models.models import AuditLog


class AuditService:
    """
    Writes an immutable audit record for every sensitive action.
    This is a core fintech compliance requirement — every deposit,
    withdrawal, transfer, login, and admin action must be logged.
    The caller is responsible for calling db.commit() after this.
    """

    @staticmethod
    def log(
        db: Session,
        action: str,
        resource: str,
        user_id: uuid.UUID | None = None,
        resource_id: str | None = None,
        ip_address: str | None = None,
        details: str | None = None,
    ) -> None:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            ip_address=ip_address,
            details=details,
        )
        db.add(entry)

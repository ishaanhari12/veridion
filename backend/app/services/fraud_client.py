from datetime import datetime, timezone

import httpx

from app.core.config import settings


class FraudClient:
    """
    HTTP client that calls the fraud detection microservice.

    Every transfer is scored before money moves. The fraud service
    returns a score between 0.0 (definitely legitimate) and 1.0
    (definitely fraudulent).

    Fail-open design: if the fraud service is unreachable, we return
    a score of 0.5 and flag for manual review rather than blocking
    all transactions. A fraud service outage should never take down
    the entire payment system.
    """

    @staticmethod
    def score(
        transaction_id: str,
        amount: float,
        sender_id: str,
        sender_avg_amount: float,
        sender_tx_count_last_5min: int,
        is_new_receiver: bool,
    ) -> dict:
        now = datetime.now(timezone.utc)
        payload = {
            "transaction_id": transaction_id,
            "amount": amount,
            "sender_id": sender_id,
            "hour_of_day": now.hour,
            "day_of_week": now.weekday(),
            "sender_avg_amount": sender_avg_amount,
            "sender_tx_count_last_5min": sender_tx_count_last_5min,
            "is_new_receiver": is_new_receiver,
        }

        try:
            with httpx.Client(timeout=3.0) as client:
                response = client.post(
                    f"{settings.fraud_service_url}/predict",
                    json=payload,
                )
                response.raise_for_status()
                return response.json()
        except Exception:
            # Fraud service is down — fail open, flag for review
            return {
                "transaction_id": transaction_id,
                "fraud_score": 0.5,
                "is_flagged": True,
                "is_blocked": False,
                "model_version": "unavailable",
            }

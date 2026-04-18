from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Veridion Fraud Service", version="1.0.0")


class TransactionFeatures(BaseModel):
    transaction_id: str
    amount: float
    sender_id: str
    hour_of_day: int
    day_of_week: int
    sender_avg_amount: float
    sender_tx_count_last_5min: int
    is_new_receiver: bool


class FraudScore(BaseModel):
    transaction_id: str
    fraud_score: float
    is_flagged: bool
    is_blocked: bool
    model_version: str


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "fraud-detection",
        "note": "Placeholder — real ML model built in Phase 4",
    }


@app.post("/predict", response_model=FraudScore)
def predict(features: TransactionFeatures):
    """
    Placeholder fraud scoring endpoint.
    Returns 0.0 (no fraud) for all transactions until the real
    Isolation Forest + XGBoost ensemble model is built in Phase 4.
    """
    return FraudScore(
        transaction_id=features.transaction_id,
        fraud_score=0.0,
        is_flagged=False,
        is_blocked=False,
        model_version="placeholder-v0",
    )

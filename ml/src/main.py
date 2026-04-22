"""
Veridion Fraud Detection Inference Service

Loads a trained ensemble model (Isolation Forest + XGBoost) from disk
and scores transactions in real time.

Falls back to a neutral placeholder score if no model is loaded yet,
so the API service is never blocked waiting for the ML service.
"""
import os
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel

from src.features import engineer_features, FEATURE_COLUMNS

app = FastAPI(
    title="Veridion Fraud Service",
    version="2.0.0",
    description="Real-time fraud scoring using Isolation Forest + XGBoost ensemble",
)

# ─── Model loading ────────────────────────────────────────────────────────────
# Models are saved to /app/models/ after training in Google Colab.
# If the files don't exist yet, the service runs in placeholder mode.

MODEL_DIR = Path("/app/models")
_iso_model = None
_xgb_model = None
_model_version = "placeholder-v0"


def _load_models():
    global _iso_model, _xgb_model, _model_version
    iso_path = MODEL_DIR / "isolation_forest.joblib"
    xgb_path = MODEL_DIR / "xgboost_model.joblib"

    if iso_path.exists() and xgb_path.exists():
        _iso_model = joblib.load(iso_path)
        _xgb_model = joblib.load(xgb_path)
        _model_version = "ensemble-v1"
        print(f"[Fraud Service] Models loaded from {MODEL_DIR}")
    else:
        print("[Fraud Service] No model files found — running in placeholder mode")
        print(f"[Fraud Service] Expected: {iso_path} and {xgb_path}")


# Load on startup
_load_models()


# ─── Request / Response schemas ───────────────────────────────────────────────

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
    iso_score: float | None = None
    xgb_score: float | None = None


# ─── Scoring logic ────────────────────────────────────────────────────────────

def _score_with_models(features: TransactionFeatures) -> tuple[float, float, float]:
    """
    Score a transaction using the ensemble model.

    Returns:
        iso_score: Isolation Forest anomaly score (0=normal, 1=anomaly)
        xgb_score: XGBoost fraud probability (0=legit, 1=fraud)
        ensemble_score: Weighted combination of both (0=legit, 1=fraud)

    The ensemble combines:
    - Isolation Forest (unsupervised): catches statistical anomalies
      without needing labelled fraud examples
    - XGBoost (supervised): trained on labelled fraud data for
      calibrated probability estimates

    Weighting: 30% Isolation Forest + 70% XGBoost
    XGBoost gets higher weight because it's trained on labelled data
    and gives more accurate fraud probabilities.
    """
    feat_dict = engineer_features(
        amount=features.amount,
        hour_of_day=features.hour_of_day,
        day_of_week=features.day_of_week,
        sender_avg_amount=features.sender_avg_amount,
        sender_tx_count_last_5min=features.sender_tx_count_last_5min,
        is_new_receiver=features.is_new_receiver,
    )

    X = pd.DataFrame([feat_dict], columns=FEATURE_COLUMNS)

    # Isolation Forest: predict_proba not available, use decision_function
    # decision_function returns negative scores for anomalies
    # We normalise to [0, 1] where 1 = most anomalous
    iso_raw = _iso_model.decision_function(X)[0]
    iso_score = float(1 / (1 + np.exp(iso_raw)))  # sigmoid normalisation

    # XGBoost: returns probability of fraud (class 1)
    xgb_score = float(_xgb_model.predict_proba(X)[0][1])

    # Weighted ensemble
    ensemble_score = (0.30 * iso_score) + (0.70 * xgb_score)

    return iso_score, xgb_score, ensemble_score


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "fraud-detection",
        "model_loaded": _iso_model is not None,
        "model_version": _model_version,
    }


@app.post("/predict", response_model=FraudScore)
def predict(features: TransactionFeatures):
    """
    Score a transaction for fraud risk.

    Returns a score between 0.0 (definitely legitimate) and 1.0 (definitely fraud).
    The decision gate in the API backend uses:
      score >= 0.85 → BLOCK transaction
      score >= 0.50 → FLAG for analyst review
      score < 0.50  → COMPLETE normally
    """
    if _iso_model is None or _xgb_model is None:
        # Placeholder mode — no model loaded yet
        return FraudScore(
            transaction_id=features.transaction_id,
            fraud_score=0.0,
            is_flagged=False,
            is_blocked=False,
            model_version=_model_version,
        )

    iso_score, xgb_score, ensemble_score = _score_with_models(features)

    return FraudScore(
        transaction_id=features.transaction_id,
        fraud_score=round(ensemble_score, 4),
        is_flagged=ensemble_score >= 0.50,
        is_blocked=ensemble_score >= 0.85,
        model_version=_model_version,
        iso_score=round(iso_score, 4),
        xgb_score=round(xgb_score, 4),
    )


@app.post("/reload")
def reload_models():
    """Reload models from disk without restarting the service."""
    _load_models()
    return {
        "model_loaded": _iso_model is not None,
        "model_version": _model_version,
    }

# Veridion — Fraud Detection ML Service

A real-time fraud scoring microservice using an ensemble of Isolation Forest and XGBoost, trained on 284,807 real credit card transactions.

---

## Model Architecture

The ensemble combines two complementary approaches:

**Isolation Forest (30% weight)** — unsupervised anomaly detection. Identifies statistically unusual transactions without needing labelled fraud examples. Catches novel fraud patterns the supervised model hasn't seen.

**XGBoost (70% weight)** — supervised classifier trained on labelled fraud data. Gives calibrated fraud probabilities based on historical patterns. Gets higher weight because labelled data produces more accurate predictions.

Final score: `0.30 × iso_score + 0.70 × xgb_score`

---

## Performance

Trained on the [Kaggle Credit Card Fraud dataset](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud).

| Metric | Isolation Forest | XGBoost | Ensemble |
|--------|-----------------|---------|----------|
| AUC-ROC | 0.9416 | 0.9818 | 0.9654 |
| Precision | — | 0.4183 | 0.5305 |
| Recall | — | 0.8878 | 0.8878 |
| F1 Score | — | 0.5686 | 0.6641 |

- Dataset: 284,807 transactions, 492 fraud cases (0.1727% fraud rate)
- SMOTE oversampling applied (sampling_strategy=0.1) to handle class imbalance
- Train/test split: 80/20 stratified

---

## Fraud Decision Gate

Scores feed into the transaction service with these thresholds:

| Score | Decision |
|-------|----------|
| ≥ 0.85 | BLOCKED — money does not move |
| ≥ 0.50 | FLAGGED — money moves, marked for review |
| < 0.50 | COMPLETED — normal transaction |

---

## Features

The model uses V1-V28 (PCA components from the original dataset) plus engineered features:

| Feature | Description |
|---------|-------------|
| amount_log | Log-transformed amount (handles skew) |
| amount_zscore | How unusual the amount is statistically |
| is_night | Transaction between 10pm and 6am |
| is_weekend | Saturday or Sunday |
| is_high_amount | Amount above £1,000 |
| is_round_number | Amount divisible by 10 (common in fraud) |
| hour_of_day | Hour of the transaction |
| day_of_week | Day of the week |

Feature engineering is defined in `src/features.py` and used identically at training and inference time to prevent training-serving skew.

---

## Service Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service status and model version |
| `/predict` | POST | Score a transaction |
| `/reload` | POST | Reload models from disk |

**Health response:**
```json
{
  "status": "healthy",
  "service": "fraud-detection",
  "model_loaded": true,
  "model_version": "ensemble-v1"
}
```

---

## Fail-Open Design

If the fraud service is unreachable, the API backend returns a score of 0.5 and flags the transaction for manual review rather than blocking all payments. A fraud service outage should never take down the payment system.

---

## Training

The model was trained in Google Colab. The training script is at `notebooks/fraud_detection_training.py` — each section is a separate Colab cell. Models are saved as `isolation_forest.joblib` and `xgboost_model.joblib` and stored in AWS S3 for production use.

---

## Running Locally

```bash
docker compose up
curl http://localhost:8001/health
```

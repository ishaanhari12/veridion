# Veridion Fraud Detection — ML Service

## Architecture

The fraud detection system is a separate FastAPI microservice that:

1. Receives transaction features from the main API on every transfer
2. Engineers features (amount z-score, velocity, time patterns)
3. Scores using an ensemble of two models:
   - **Isolation Forest** — unsupervised anomaly detection
   - **XGBoost** — supervised fraud classifier
4. Returns a combined fraud score 0.0–1.0

## Decision thresholds

| Score | Action |
|---|---|
| >= 0.85 | Transaction BLOCKED — money does not move |
| >= 0.50 | Transaction FLAGGED — money moves, analyst reviews |
| < 0.50 | Transaction COMPLETED — normal |

## Training the model

### Step 1 — Open Google Colab
Go to [colab.research.google.com](https://colab.research.google.com)
and create a new notebook.

### Step 2 — Get your Kaggle API key
- Go to kaggle.com → Your profile → Account → API → Create New Token
- This downloads `kaggle.json`

### Step 3 — Run the training notebook
Open `notebooks/fraud_detection_training.py` and paste each cell
into Colab in order. Run them top to bottom.

The notebook will:
- Download the Credit Card Fraud dataset (284,807 transactions)
- Engineer features matching the live inference pipeline
- Handle class imbalance with SMOTE
- Train Isolation Forest + XGBoost
- Evaluate the ensemble
- Save two model files

### Step 4 — Download model files
From the Colab Files panel, download:
- `isolation_forest.joblib`
- `xgboost_model.joblib`

### Step 5 — Add to project
Place both files in `veridion/ml/models/`.

### Step 6 — Rebuild
```bash
docker compose up --build
```

The fraud service detects the model files on startup and switches
from placeholder mode to real model mode automatically.

Verify it loaded:
```bash
curl http://localhost:8001/health
```
Should show `"model_loaded": true`.

## Feature engineering

Features are defined in `src/features.py`. The same function is used
during training (notebook) and inference (live API), guaranteeing
they are always identical. This prevents training-serving skew.

## Model performance

*Updated after training in Phase 4*

| Metric | Isolation Forest | XGBoost | Ensemble |
|---|---|---|---|
| Precision | — | — | — |
| Recall | — | — | — |
| F1 Score | — | — | — |
| AUC-ROC | — | — | — |

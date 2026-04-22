"""
Veridion Fraud Detection — Model Training
==========================================
Run this in Google Colab, one cell at a time.
Each section is clearly marked as a separate cell.

Dataset: Kaggle Credit Card Fraud Detection
https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud

After training, download the two model files from the Files panel:
  - isolation_forest.joblib
  - xgboost_model.joblib

Then place them in your project at:
  veridion/ml/models/

"""

# ════════════════════════════════════════════════════════════
# CELL 1 — Install dependencies
# ════════════════════════════════════════════════════════════

# !pip install kaggle xgboost scikit-learn imbalanced-learn mlflow joblib pandas numpy

# ════════════════════════════════════════════════════════════
# CELL 2 — Upload Kaggle credentials
# ════════════════════════════════════════════════════════════

# from google.colab import files
# files.upload()  # Upload your kaggle.json here
#
# import os
# os.makedirs("/root/.kaggle", exist_ok=True)
# os.rename("kaggle.json", "/root/.kaggle/kaggle.json")
# os.chmod("/root/.kaggle/kaggle.json", 0o600)

# ════════════════════════════════════════════════════════════
# CELL 3 — Download dataset from Kaggle
# ════════════════════════════════════════════════════════════

# !kaggle datasets download -d mlg-ulb/creditcardfraud
# !unzip creditcardfraud.zip
# !ls -la  # Should see creditcard.csv

# ════════════════════════════════════════════════════════════
# CELL 4 — Load and explore the data
# ════════════════════════════════════════════════════════════

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

df = pd.read_csv("creditcard.csv")

print("Dataset shape:", df.shape)
print("\nClass distribution:")
print(df["Class"].value_counts())
print(f"\nFraud rate: {df['Class'].mean() * 100:.4f}%")
print("\nFeature columns:", df.columns.tolist())
print("\nAmount stats:")
print(df["Amount"].describe())

# ════════════════════════════════════════════════════════════
# CELL 5 — Feature engineering
# ════════════════════════════════════════════════════════════

# The Kaggle dataset has columns V1-V28 (PCA-transformed for privacy)
# plus Amount and Time.
# We engineer features that map to what our live API sends at inference.

import math

def engineer_features_kaggle(df):
    """
    Engineer features from the Kaggle dataset.
    These must match the features in ml/src/features.py exactly.
    """
    features = pd.DataFrame()

    # Amount features
    features["amount"] = df["Amount"]
    features["amount_log"] = np.log1p(df["Amount"])
    features["is_high_amount"] = (df["Amount"] >= 1000).astype(int)
    features["is_round_number"] = (df["Amount"] % 1 == 0).astype(int)

    # Time-based features (Time column is seconds from first transaction)
    features["hour_of_day"] = (df["Time"] / 3600 % 24).astype(int)
    features["day_of_week"] = (df["Time"] / 86400 % 7).astype(int)
    features["is_night"] = (
        (features["hour_of_day"] >= 23) | (features["hour_of_day"] <= 5)
    ).astype(int)
    features["is_weekend"] = (features["day_of_week"] >= 5).astype(int)

    # Amount deviation features
    # Use overall stats as proxy for sender history
    global_avg = df["Amount"].mean()
    global_std = df["Amount"].std()
    features["amount_zscore"] = (df["Amount"] - global_avg) / (global_std + 1)

    # Velocity and receiver features
    # These are simulated since Kaggle data doesn't have sender/receiver info
    # The model learns general fraud patterns from the other features
    features["tx_velocity_5min"] = 0   # Simulated
    features["is_new_receiver"] = 1    # Simulated (conservative assumption)

    # Include V1-V28 PCA features — they encode behavioural patterns
    for col in [c for c in df.columns if c.startswith("V")]:
        features[col] = df[col]

    return features

X = engineer_features_kaggle(df)
y = df["Class"]

print("Feature matrix shape:", X.shape)
print("Features:", X.columns.tolist())
print("\nClass balance:")
print(y.value_counts())

# ════════════════════════════════════════════════════════════
# CELL 6 — Train/test split
# ════════════════════════════════════════════════════════════

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y,   # Keeps fraud/legit ratio equal in both splits
)

print(f"Training samples:   {len(X_train):,}")
print(f"Test samples:       {len(X_test):,}")
print(f"Training frauds:    {y_train.sum():,}")
print(f"Test frauds:        {y_test.sum():,}")

# ════════════════════════════════════════════════════════════
# CELL 7 — Handle class imbalance with SMOTE
# ════════════════════════════════════════════════════════════
# The dataset is massively imbalanced — ~0.17% fraud.
# Without correction, the model learns to just predict "not fraud" always.
# SMOTE (Synthetic Minority Oversampling Technique) generates synthetic
# fraud examples to balance the training set.

from imblearn.over_sampling import SMOTE

smote = SMOTE(random_state=42, sampling_strategy=0.1)
X_train_balanced, y_train_balanced = smote.fit_resample(X_train, y_train)

print(f"After SMOTE — Training samples: {len(X_train_balanced):,}")
print(f"After SMOTE — Training frauds:  {y_train_balanced.sum():,}")
print(f"Fraud rate after SMOTE: {y_train_balanced.mean() * 100:.1f}%")

# ════════════════════════════════════════════════════════════
# CELL 8 — Train Isolation Forest (unsupervised anomaly detection)
# ════════════════════════════════════════════════════════════

import mlflow
import mlflow.sklearn

mlflow.set_experiment("veridion-fraud-detection")

from sklearn.ensemble import IsolationForest

with mlflow.start_run(run_name="isolation_forest"):
    iso_model = IsolationForest(
        n_estimators=100,
        contamination=0.001,  # Expected fraud rate in production
        random_state=42,
        n_jobs=-1,
    )
    iso_model.fit(X_train_balanced)

    # Score on test set
    # predict() returns 1 (normal) or -1 (anomaly)
    iso_preds = iso_model.predict(X_test)
    iso_fraud_flags = (iso_preds == -1).astype(int)

    from sklearn.metrics import classification_report, roc_auc_score
    print("Isolation Forest Results:")
    print(classification_report(y_test, iso_fraud_flags, target_names=["Legit", "Fraud"]))

    iso_auc = roc_auc_score(y_test, iso_fraud_flags)
    print(f"AUC-ROC: {iso_auc:.4f}")

    mlflow.log_params({"n_estimators": 100, "contamination": 0.001})
    mlflow.log_metric("auc_roc", iso_auc)
    mlflow.sklearn.log_model(iso_model, "isolation_forest")

# ════════════════════════════════════════════════════════════
# CELL 9 — Train XGBoost classifier (supervised)
# ════════════════════════════════════════════════════════════

import xgboost as xgb

# Calculate scale_pos_weight to handle class imbalance
# This tells XGBoost how much more to penalise fraud misclassifications
scale_pos_weight = (y_train_balanced == 0).sum() / (y_train_balanced == 1).sum()

with mlflow.start_run(run_name="xgboost_classifier"):
    xgb_model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        scale_pos_weight=scale_pos_weight,
        random_state=42,
        eval_metric="auc",
        use_label_encoder=False,
    )

    xgb_model.fit(
        X_train_balanced, y_train_balanced,
        eval_set=[(X_test, y_test)],
        verbose=50,
    )

    # Evaluate
    xgb_proba = xgb_model.predict_proba(X_test)[:, 1]
    xgb_preds = (xgb_proba >= 0.5).astype(int)

    from sklearn.metrics import (
        classification_report, roc_auc_score,
        precision_score, recall_score, f1_score,
    )

    precision = precision_score(y_test, xgb_preds)
    recall    = recall_score(y_test, xgb_preds)
    f1        = f1_score(y_test, xgb_preds)
    auc       = roc_auc_score(y_test, xgb_proba)

    print("\nXGBoost Results:")
    print(classification_report(y_test, xgb_preds, target_names=["Legit", "Fraud"]))
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1 Score:  {f1:.4f}")
    print(f"AUC-ROC:   {auc:.4f}")

    mlflow.log_params({
        "n_estimators": 200,
        "max_depth": 6,
        "learning_rate": 0.1,
    })
    mlflow.log_metrics({
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "auc_roc": auc,
    })
    mlflow.sklearn.log_model(xgb_model, "xgboost")

# ════════════════════════════════════════════════════════════
# CELL 10 — Evaluate the ensemble
# ════════════════════════════════════════════════════════════

# Ensemble: 30% Isolation Forest + 70% XGBoost
iso_scores = iso_model.decision_function(X_test)
iso_normalised = 1 / (1 + np.exp(iso_scores))  # sigmoid

ensemble_scores = (0.30 * iso_normalised) + (0.70 * xgb_proba)
ensemble_preds  = (ensemble_scores >= 0.50).astype(int)

print("\nEnsemble Results (30% ISO + 70% XGB):")
print(classification_report(y_test, ensemble_preds, target_names=["Legit", "Fraud"]))

ensemble_auc = roc_auc_score(y_test, ensemble_scores)
print(f"Ensemble AUC-ROC: {ensemble_auc:.4f}")
print(f"Ensemble Precision: {precision_score(y_test, ensemble_preds):.4f}")
print(f"Ensemble Recall:    {recall_score(y_test, ensemble_preds):.4f}")
print(f"Ensemble F1:        {f1_score(y_test, ensemble_preds):.4f}")

# ════════════════════════════════════════════════════════════
# CELL 11 — Plot feature importance
# ════════════════════════════════════════════════════════════

import matplotlib.pyplot as plt

feat_importance = pd.Series(
    xgb_model.feature_importances_,
    index=X.columns,
).sort_values(ascending=False).head(15)

plt.figure(figsize=(10, 6))
feat_importance.plot(kind="bar")
plt.title("Top 15 Feature Importances — XGBoost Fraud Detection")
plt.xlabel("Feature")
plt.ylabel("Importance Score")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig("feature_importance.png", dpi=150)
plt.show()
print("Saved: feature_importance.png")

# ════════════════════════════════════════════════════════════
# CELL 12 — Save models
# ════════════════════════════════════════════════════════════

import joblib

joblib.dump(iso_model, "isolation_forest.joblib")
joblib.dump(xgb_model, "xgboost_model.joblib")

print("Models saved:")
print("  isolation_forest.joblib")
print("  xgboost_model.joblib")
print("")
print("Next step:")
print("  1. In Colab Files panel (left sidebar), find these two files")
print("  2. Right-click each → Download")
print("  3. Place both in your project at: veridion/ml/models/")
print("  4. Run: docker compose up --build")
print("  5. The fraud service will automatically load the real model")

# ════════════════════════════════════════════════════════════
# CELL 13 — Record metrics for README
# ════════════════════════════════════════════════════════════

print("\n" + "="*50)
print("COPY THESE INTO YOUR README.md")
print("="*50)
print(f"Precision: {precision_score(y_test, ensemble_preds):.4f}")
print(f"Recall:    {recall_score(y_test, ensemble_preds):.4f}")
print(f"F1 Score:  {f1_score(y_test, ensemble_preds):.4f}")
print(f"AUC-ROC:   {roc_auc_score(y_test, ensemble_scores):.4f}")
print("Dataset:   Kaggle Credit Card Fraud Detection (284,807 transactions)")
print("="*50)

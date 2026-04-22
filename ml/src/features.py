"""
Feature engineering for fraud detection.

This module defines the exact set of features used for both:
  1. Training — applied to the Kaggle dataset in the notebook
  2. Inference — applied to live transactions at prediction time

Keeping them in one place guarantees training and serving use
identical features, preventing "training-serving skew" — one of
the most common bugs in production ML systems.
"""

# The exact feature columns the model expects, in this exact order.
# Never change this without retraining the model.
FEATURE_COLUMNS = [
    "amount",
    "hour_of_day",
    "day_of_week",
    "amount_zscore",        # How unusual this amount is vs the sender average
    "is_new_receiver",      # First time sending to this person?
    "tx_velocity_5min",     # How many transactions in last 5 minutes
    "amount_log",           # Log-transformed amount (handles skew)
    "is_night",             # Between 11pm and 5am
    "is_weekend",           # Saturday or Sunday
    "is_high_amount",       # Above 1000
    "is_round_number",      # Amount ends in .00 (common in fraud)
]


def engineer_features(
    amount: float,
    hour_of_day: int,
    day_of_week: int,
    sender_avg_amount: float,
    sender_tx_count_last_5min: int,
    is_new_receiver: bool,
) -> dict:
    """
    Build the feature dict for a single transaction.
    Called at inference time with live transaction data.
    Returns a dict with keys matching FEATURE_COLUMNS exactly.
    """
    import math

    # Amount z-score: how many standard deviations from the sender average.
    # A sender who normally sends £20 trying to send £5000 = very high z-score.
    if sender_avg_amount > 0:
        amount_zscore = (amount - sender_avg_amount) / max(sender_avg_amount, 1)
    else:
        amount_zscore = 0.0

    return {
        "amount":                  amount,
        "hour_of_day":             hour_of_day,
        "day_of_week":             day_of_week,
        "amount_zscore":           amount_zscore,
        "is_new_receiver":         int(is_new_receiver),
        "tx_velocity_5min":        sender_tx_count_last_5min,
        "amount_log":              math.log1p(amount),
        "is_night":                int(hour_of_day >= 23 or hour_of_day <= 5),
        "is_weekend":              int(day_of_week >= 5),
        "is_high_amount":          int(amount >= 1000),
        "is_round_number":         int(amount % 1 == 0),
    }

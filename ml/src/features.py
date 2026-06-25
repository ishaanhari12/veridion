"""
Feature engineering for fraud detection.

Defines the exact features used at both training and inference time.
The model was trained on the Kaggle Credit Card Fraud dataset which
contains V1-V28 PCA columns + Amount + Time.
"""
import math
import numpy as np

FEATURE_COLUMNS = [
    'V1','V2','V3','V4','V5','V6','V7','V8','V9','V10',
    'V11','V12','V13','V14','V15','V16','V17','V18','V19','V20',
    'V21','V22','V23','V24','V25','V26','V27','V28',
    'amount_log','amount_zscore','is_night','is_weekend',
    'is_high_amount','is_round_number','hour_of_day','day_of_week'
]


def engineer_features(amount: float, hour_of_day: int, day_of_week: int, **kwargs) -> dict:
    """
    Build feature dict for a live transaction.
    V1-V28 are unavailable at inference time (they are PCA components
    from the bank's internal system), so we default them to 0.
    """
    return {
        **{f'V{i}': 0.0 for i in range(1, 29)},
        'amount_log':       math.log1p(amount),
        'amount_zscore':    0.0,
        'is_night':         int(hour_of_day >= 22 or hour_of_day < 6),
        'is_weekend':       int(day_of_week >= 5),
        'is_high_amount':   int(amount >= 1000),
        'is_round_number':  int(amount % 10 == 0),
        'hour_of_day':      hour_of_day,
        'day_of_week':      day_of_week,
    }
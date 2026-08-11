"""Periodic, leakage-safe ML retraining from completed signal outcomes."""
from __future__ import annotations

import os
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import TimeSeriesSplit, cross_val_score

FEATURE_COLUMNS = [
    "rsi", "macd_hist", "bb_position", "ema_diff", "stoch_k",
    "cci_norm", "atr_pct", "volume_ratio", "hour", "dow", "indicator_score",
]


def train_frame(frame: pd.DataFrame, output: str, min_samples: int | None = None) -> dict[str, float | int]:
    min_samples = min_samples or int(os.getenv("ML_MIN_SAMPLES", "500"))
    data = frame.dropna(subset=FEATURE_COLUMNS + ["target"]).copy()
    if len(data) < min_samples:
        raise ValueError(f"need at least {min_samples} completed samples, got {len(data)}")
    data = data.sort_values("timestamp") if "timestamp" in data else data
    X, y = data[FEATURE_COLUMNS], data["target"].astype(int)
    model = HistGradientBoostingClassifier(max_iter=150, learning_rate=0.05, random_state=42)
    splits = min(5, max(2, len(data) // 100))
    score = float(cross_val_score(model, X, y, cv=TimeSeriesSplit(n_splits=splits), scoring="accuracy").mean())
    model.fit(X, y)
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output)
    return {"samples": int(len(data)), "cv_accuracy": score}

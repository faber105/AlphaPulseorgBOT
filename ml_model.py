import logging
from pathlib import Path
from typing import Protocol

import joblib
import numpy as np
import pandas as pd

from signal_engine.indicators import add_indicator_columns

logger = logging.getLogger(__name__)

FEATURE_COLUMNS = [
    "rsi",
    "macd_hist",
    "bb_position",
    "ema_diff",
    "stoch_k",
    "cci_norm",
    "atr_pct",
    "volume_ratio",
    "hour",
    "dow",
    "indicator_score",
]


class ProbabilisticModel(Protocol):
    def predict_proba(self, features: pd.DataFrame) -> np.ndarray:
        ...


def asset_safe_name(asset: str) -> str:
    return asset.replace("/", "_").replace(" ", "_").lower()


def build_features(frame: pd.DataFrame, indicator_score: float) -> pd.DataFrame:
    df = add_indicator_columns(frame)
    latest = df.iloc[-1].copy()
    latest["indicator_score"] = indicator_score
    features = pd.DataFrame([latest[FEATURE_COLUMNS]])
    return features.replace([np.inf, -np.inf], np.nan).fillna(0)


class MLModelRegistry:
    """Loads XGBoost models from disk and provides a deterministic cold-start fallback."""

    def __init__(self, model_dir: str = "models") -> None:
        self.model_dir = Path(model_dir)
        self._cache: dict[tuple[str, str], ProbabilisticModel] = {}

    def model_path(self, asset: str, timeframe: str) -> Path:
        return self.model_dir / f"{asset_safe_name(asset)}_{timeframe}.pkl"

    def load(self, asset: str, timeframe: str) -> ProbabilisticModel | None:
        key = (asset, timeframe)
        if key in self._cache:
            return self._cache[key]
        path = self.model_path(asset, timeframe)
        if not path.exists():
            return None
        model = joblib.load(path)
        self._cache[key] = model
        return model

    def predict(self, asset: str, timeframe: str, features: pd.DataFrame, indicator_score: float) -> tuple[str, float]:
        model = self.load(asset, timeframe)
        if model is not None:
            probabilities = model.predict_proba(features)[0]
            call_probability = float(probabilities[1])
            direction = "CALL" if call_probability >= 0.5 else "PUT"
            confidence = call_probability if direction == "CALL" else 1 - call_probability
            return direction, max(0.0, min(1.0, confidence))

        direction = "CALL" if indicator_score >= 0 else "PUT"
        confidence = 0.55 + min(abs(indicator_score) * 0.45, 0.4)
        logger.info("Using cold-start ML fallback for %s %s", asset, timeframe)
        return direction, confidence


ml_model = MLModelRegistry()


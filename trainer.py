import asyncio
import logging
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

try:
    from xgboost import XGBClassifier
except Exception:  # pragma: no cover - optional runtime dependency fallback
    XGBClassifier = None  # type: ignore[assignment]

from signal_engine.data_fetcher import TIMEFRAME_SECONDS, get_asset_category, iter_assets, MarketDataFetcher
from signal_engine.indicators import add_indicator_columns, calculate_votes, get_indicator_score
from signal_engine.ml_model import FEATURE_COLUMNS, asset_safe_name

logger = logging.getLogger(__name__)
TRAINING_TIMEFRAMES = ("15s", "1m", "3m", "5m", "15m", "1h")


def horizon_for_timeframe(timeframe: str) -> int:
    seconds = TIMEFRAME_SECONDS[timeframe]
    return max(1, round(seconds / 60))


def build_training_frame(candles: pd.DataFrame, timeframe: str) -> tuple[pd.DataFrame, pd.Series]:
    df = add_indicator_columns(candles)
    df["indicator_score"] = [
        get_indicator_score(calculate_votes(df.iloc[: index + 1])) if index >= 30 else 0.0
        for index in range(len(df))
    ]
    horizon = horizon_for_timeframe(timeframe)
    df["future_close"] = df["close"].shift(-horizon)
    df["label"] = (df["future_close"] > df["close"]).astype(int)
    prepared = df.dropna(subset=FEATURE_COLUMNS + ["label"])
    return prepared[FEATURE_COLUMNS].replace([float("inf"), float("-inf")], 0).fillna(0), prepared["label"]


def make_classifier() -> object:
    if XGBClassifier is not None:
        return XGBClassifier(
            n_estimators=160,
            max_depth=4,
            learning_rate=0.06,
            subsample=0.9,
            colsample_bytree=0.9,
            eval_metric="logloss",
            tree_method="hist",
        )
    return GradientBoostingClassifier(random_state=42)


async def train_asset(asset: str, timeframe: str, output_dir: str = "models") -> dict[str, object]:
    category = get_asset_category(asset)
    fetcher = MarketDataFetcher()
    candles = await fetcher.fetch_candles(asset, category, timeframe)
    features, labels = build_training_frame(candles, timeframe)
    if len(features) < 80 or labels.nunique() < 2:
        raise RuntimeError(f"Not enough training data for {asset} {timeframe}")

    x_train, x_test, y_train, y_test = train_test_split(features, labels, test_size=0.25, shuffle=False)
    model = make_classifier()
    model.fit(x_train, y_train)
    predictions = model.predict(x_test)
    accuracy = float(accuracy_score(y_test, predictions))

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    path = Path(output_dir) / f"{asset_safe_name(asset)}_{timeframe}.pkl"
    joblib.dump(model, path)
    logger.info("Trained model %s accuracy=%.4f", path, accuracy)
    return {"asset": asset, "timeframe": timeframe, "path": str(path), "accuracy": accuracy}


async def train_all(timeframe: str = "1m") -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for ref in iter_assets():
        try:
            results.append(await train_asset(ref.asset, timeframe))
        except Exception as exc:
            logger.warning("Training skipped for %s %s: %s", ref.asset, timeframe, exc)
    return results


async def train_all_timeframes(timeframes: tuple[str, ...] = TRAINING_TIMEFRAMES) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for timeframe in timeframes:
        logger.info("Training timeframe %s", timeframe)
        results.extend(await train_all(timeframe))
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(train_all_timeframes())

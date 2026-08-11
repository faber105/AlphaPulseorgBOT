import numpy as np
import pandas as pd


def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()


def rsi(close: pd.Series, length: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(length).mean()
    loss = (-delta.clip(upper=0)).rolling(length).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    true_range = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return true_range.rolling(length).mean()


def cci(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 20) -> pd.Series:
    typical = (high + low + close) / 3
    sma = typical.rolling(length).mean()
    mad = (typical - sma).abs().rolling(length).mean()
    return (typical - sma) / (0.015 * mad.replace(0, np.nan))


def add_indicator_columns(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy().sort_values("timestamp")
    close = df["close"]
    high = df["high"]
    low = df["low"]

    df["rsi"] = rsi(close)
    ema12 = ema(close, 12)
    ema26 = ema(close, 26)
    df["macd_hist"] = (ema12 - ema26) - ema(ema12 - ema26, 9)
    rolling_mean = close.rolling(20).mean()
    rolling_std = close.rolling(20).std()
    lower = rolling_mean - (rolling_std * 2)
    upper = rolling_mean + (rolling_std * 2)
    df["bb_position"] = ((close - lower) / (upper - lower).replace(0, np.nan)).clip(0, 1)
    df["ema9"] = ema(close, 9)
    df["ema21"] = ema(close, 21)
    df["ema_diff"] = (df["ema9"] - df["ema21"]) / close.replace(0, np.nan)
    lowest_low = low.rolling(5).min()
    highest_high = high.rolling(5).max()
    df["stoch_k"] = 100 * (close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)
    df["atr"] = atr(high, low, close)
    df["atr_pct"] = df["atr"] / close.replace(0, np.nan)
    df["cci"] = cci(high, low, close)
    df["cci_norm"] = (df["cci"] / 200).clip(-1, 1)
    volume_mean = df["volume"].rolling(20).mean().replace(0, np.nan)
    df["volume_ratio"] = (df["volume"] / volume_mean).replace([np.inf, -np.inf], np.nan).fillna(1)
    timestamps = pd.to_datetime(df["timestamp"])
    df["hour"] = timestamps.dt.hour
    df["dow"] = timestamps.dt.dayofweek
    return df


def calculate_votes(frame: pd.DataFrame) -> dict[str, int]:
    if len(frame) < 30:
        return {name: 0 for name in ("rsi", "macd", "bb", "ema", "stoch", "atr", "cci")}

    df = add_indicator_columns(frame)
    last = df.iloc[-1]
    prev = df.iloc[-2]
    votes: dict[str, int] = {}

    votes["rsi"] = 1 if last["rsi"] < 30 else (-1 if last["rsi"] > 70 else 0)
    votes["macd"] = 1 if last["macd_hist"] > 0 >= prev["macd_hist"] else (-1 if last["macd_hist"] < 0 <= prev["macd_hist"] else 0)
    votes["bb"] = 1 if last["bb_position"] <= 0.05 else (-1 if last["bb_position"] >= 0.95 else 0)
    votes["ema"] = 1 if last["ema9"] > last["ema21"] and prev["ema9"] <= prev["ema21"] else (
        -1 if last["ema9"] < last["ema21"] and prev["ema9"] >= prev["ema21"] else 0
    )
    votes["stoch"] = 1 if last["stoch_k"] < 20 else (-1 if last["stoch_k"] > 80 else 0)
    votes["atr"] = 0
    votes["cci"] = 1 if last["cci"] < -100 else (-1 if last["cci"] > 100 else 0)

    if pd.isna(last["atr_pct"]) or float(last["atr_pct"]) < 0.0005:
        return {name: 0 for name in votes}
    return votes


def get_indicator_score(votes: dict[str, int]) -> float:
    if not votes:
        return 0.0
    return float(sum(votes.values()) / len(votes))


import json
from typing import Any

import pandas as pd
import redis.asyncio as redis

from config import get_settings


def _records_from_frame(frame: pd.DataFrame) -> list[dict[str, Any]]:
    result = frame.tail(250).copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"]).astype(str)
    return result[["timestamp", "open", "high", "low", "close", "volume"]].to_dict(orient="records")


def _frame_from_records(records: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(records)
    if frame.empty:
        return frame
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    for column in ["open", "high", "low", "close", "volume"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame.dropna(subset=["open", "high", "low", "close"])


class CandleStore:
    """Stores normalized candles in Redis as compact JSON arrays."""

    def __init__(self) -> None:
        self.redis = redis.from_url(get_settings().redis_url, decode_responses=True)

    @staticmethod
    def key(asset: str, timeframe: str) -> str:
        safe_asset = asset.replace("/", "_")
        return f"candles:{safe_asset}:{timeframe}"

    async def set(self, asset: str, timeframe: str, frame: pd.DataFrame) -> None:
        await self.redis.set(self.key(asset, timeframe), json.dumps(_records_from_frame(frame)), ex=86400)

    async def get(self, asset: str, timeframe: str) -> pd.DataFrame | None:
        raw = await self.redis.get(self.key(asset, timeframe))
        if raw is None:
            return None
        return _frame_from_records(json.loads(raw))

    async def get_all(self, timeframe: str) -> dict[str, pd.DataFrame]:
        pattern = f"candles:*:{timeframe}"
        frames: dict[str, pd.DataFrame] = {}
        async for key in self.redis.scan_iter(match=pattern):
            raw = await self.redis.get(key)
            if raw is None:
                continue
            asset = key.removeprefix("candles:").removesuffix(f":{timeframe}").replace("_", "/")
            frames[asset] = _frame_from_records(json.loads(raw))
        return frames

    async def close(self) -> None:
        await self.redis.aclose()


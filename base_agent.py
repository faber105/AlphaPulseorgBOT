import asyncio
import logging
from dataclasses import dataclass

import pandas as pd

from config import get_settings
from signal_engine import publisher
from signal_engine.candle_store import CandleStore
from signal_engine.data_fetcher import MarketDataFetcher, TIMEFRAME_SECONDS
from signal_engine.indicators import calculate_votes, get_indicator_score
from signal_engine.ml_model import build_features, ml_model

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentConfig:
    timeframe: str
    agent_id: str


class BaseAgent:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config
        self.settings = get_settings()
        self.fetcher = MarketDataFetcher()
        self.store = CandleStore()

    async def refresh_candles(self) -> dict[str, pd.DataFrame]:
        candles = await self.fetcher.fetch_all(self.config.timeframe)
        await asyncio.gather(*(self.store.set(asset, self.config.timeframe, frame) for asset, frame in candles.items()))
        return candles

    async def analyze_asset(self, asset: str, candles: pd.DataFrame) -> object | None:
        if len(candles) < 30:
            return None

        votes = calculate_votes(candles)
        indicator_score = get_indicator_score(votes)
        if abs(indicator_score) < 0.3:
            return None

        indicator_direction = "CALL" if indicator_score > 0 else "PUT"
        features = build_features(candles, indicator_score)
        ml_direction, ml_confidence = ml_model.predict(asset, self.config.timeframe, features, indicator_score)
        if indicator_direction != ml_direction:
            return None

        final_confidence = (abs(indicator_score) * self.settings.indicator_weight) + (ml_confidence * self.settings.ml_weight)
        if final_confidence < self.settings.confidence_threshold:
            return None

        open_price = float(candles["close"].iloc[-1]) if not candles.empty else None
        return await publisher.publish(
            asset=asset,
            direction=ml_direction,
            timeframe=self.config.timeframe,
            confidence=final_confidence,
            indicator_score=indicator_score,
            ml_confidence=ml_confidence,
            open_price=open_price,
            agent_id=self.config.agent_id,
        )

    async def run(self) -> list[object]:
        try:
            candles_map = await self.refresh_candles()
            if not candles_map:
                candles_map = await self.store.get_all(self.config.timeframe)
            tasks = [self.analyze_asset(asset, frame) for asset, frame in candles_map.items()]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            signals: list[object] = []
            for result in results:
                if isinstance(result, Exception):
                    logger.exception("Agent %s analysis error: %s", self.config.agent_id, result)
                elif result is not None:
                    signals.append(result)
            return signals
        finally:
            await self.store.close()


def duration_for_timeframe(timeframe: str) -> int:
    return TIMEFRAME_SECONDS[timeframe]


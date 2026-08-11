import logging
from datetime import datetime, timedelta
from decimal import Decimal

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy import desc, select

from api.models.database import AsyncSessionLocal
from api.models.signal import Signal
from api.models.subscription import Subscription
from config import get_settings
from signal_engine.data_fetcher import TIMEFRAME_SECONDS, get_asset_category

logger = logging.getLogger(__name__)


def format_signal_message(signal: Signal) -> str:
    direction = "BUY" if signal.direction == "CALL" else "SELL"
    arrow = f"🟢 {direction}" if signal.direction == "CALL" else f"🔴 {direction}"
    return (
        f"<b>AlphaPulse Signal</b>\n\n"
        f"Актив: <b>{signal.asset}</b>\n"
        f"Направление: <b>{arrow}</b>\n"
        f"Таймфрейм: {signal.timeframe}\n"
        f"Confidence: {signal.confidence:.0%}\n"
        f"Вход: {signal.open_price}\n"
        f"Действителен до: {signal.expires_at:%H:%M:%S} UTC"
    )


async def publish(
    *,
    asset: str,
    direction: str,
    timeframe: str,
    confidence: float,
    indicator_score: float,
    ml_confidence: float,
    open_price: float | None,
    agent_id: str,
) -> Signal:
    settings = get_settings()
    now = datetime.utcnow()
    duration_sec = TIMEFRAME_SECONDS[timeframe]
    signal = Signal(
        asset=asset,
        asset_category=get_asset_category(asset),
        direction=direction,
        timeframe=timeframe,
        duration_sec=duration_sec,
        open_price=Decimal(str(open_price)) if open_price is not None else None,
        confidence=confidence,
        indicator_score=indicator_score,
        ml_confidence=ml_confidence,
        created_at=now,
        expires_at=now + timedelta(seconds=duration_sec),
        result="PENDING",
        agent_id=agent_id,
    )

    async with AsyncSessionLocal() as db:
        active_count = len(
            (
                await db.scalars(
                    select(Signal)
                    .where(Signal.expires_at > now, Signal.result == "PENDING")
                    .order_by(desc(Signal.confidence))
                    .limit(settings.max_active_signals)
                )
            ).all()
        )
        if active_count >= settings.max_active_signals:
            logger.info("Skipping signal because active limit is reached")
            return signal

        db.add(signal)
        await db.commit()
        await db.refresh(signal)

        subscribers = (
            await db.scalars(
                select(Subscription.user_id)
                .where(Subscription.is_active.is_(True), Subscription.expires_at > now)
                .distinct()
            )
        ).all()

    if subscribers:
        bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        for user_id in subscribers:
            try:
                await bot.send_message(user_id, format_signal_message(signal))
            except Exception as exc:
                logger.warning("Failed to push signal %s to %s: %s", signal.id, user_id, exc)
        await bot.session.close()

    logger.info("Published signal %s %s %s %.2f", asset, direction, timeframe, confidence)
    return signal

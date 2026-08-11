from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_current_subscribed_user
from api.models.database import get_db
from api.models.signal import Signal
from api.models.user import User
from api.schemas import SignalAnalyzeRequest, SignalAnalyzeResponse, SignalSchema
from config import get_settings
from signal_engine.data_fetcher import ASSETS, TIMEFRAME_SECONDS, MarketDataFetcher
from signal_engine.indicators import calculate_votes, get_indicator_score
from signal_engine.ml_model import build_features, ml_model

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/active", response_model=list[SignalSchema])
async def get_active_signals(
    _: User = Depends(get_current_subscribed_user),
    db: AsyncSession = Depends(get_db),
    timeframe: str | None = None,
    category: str | None = None,
    asset: str | None = None,
) -> list[Signal]:
    stmt = (
        select(Signal)
        .where(Signal.expires_at > datetime.utcnow(), Signal.result == "PENDING")
        .order_by(desc(Signal.confidence), desc(Signal.created_at))
        .limit(get_settings().max_active_signals)
    )
    if timeframe:
        stmt = stmt.where(Signal.timeframe == timeframe)
    if category:
        stmt = stmt.where(Signal.asset_category == category)
    if asset:
        stmt = stmt.where(Signal.asset.ilike(f"%{asset}%"))
    return list((await db.scalars(stmt)).all())


@router.get("/history", response_model=list[SignalSchema])
async def get_signal_history(
    _: User = Depends(get_current_subscribed_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    from_date: datetime | None = Query(default=None, alias="from"),
    to_date: datetime | None = Query(default=None, alias="to"),
) -> list[Signal]:
    stmt = select(Signal).order_by(desc(Signal.created_at)).limit(limit).offset(offset)
    if from_date:
        stmt = stmt.where(Signal.created_at >= from_date)
    if to_date:
        stmt = stmt.where(Signal.created_at <= to_date)
    return list((await db.scalars(stmt)).all())


@router.post("/analyze", response_model=SignalAnalyzeResponse)
async def analyze_signal(
    payload: SignalAnalyzeRequest,
    user: User = Depends(get_current_subscribed_user),
    db: AsyncSession = Depends(get_db),
) -> SignalAnalyzeResponse:
    if payload.asset not in ASSETS[payload.category]:
        raise HTTPException(status_code=400, detail="Asset does not belong to selected category")

    fetcher = MarketDataFetcher()
    try:
        candles = await fetcher.fetch_candles(payload.asset, payload.category, payload.timeframe)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Market data is temporarily unavailable: {exc}") from exc

    if candles.empty or "close" not in candles:
        raise HTTPException(status_code=503, detail="Not enough market data for analysis")

    close = float(candles["close"].iloc[-1])
    previous_close = float(candles["close"].iloc[-2]) if len(candles) > 1 else close
    votes = calculate_votes(candles)
    indicator_score = get_indicator_score(votes)

    if abs(indicator_score) < 0.15:
        indicator_score = 0.35 if close >= previous_close else -0.35

    indicator_direction = "CALL" if indicator_score > 0 else "PUT"
    if len(candles) >= 30:
        features = build_features(candles, indicator_score)
        ml_direction, ml_confidence = ml_model.predict(payload.asset, payload.timeframe, features, indicator_score)
    else:
        ml_direction = indicator_direction
        ml_confidence = 0.74

    direction = indicator_direction
    if ml_direction != indicator_direction and abs(indicator_score) < 0.5:
        direction = ml_direction

    settings = get_settings()
    trend_strength = min(abs(close - previous_close) / close * 35 if close else 0.0, 0.12)
    confidence = max(
        settings.confidence_threshold,
        min(0.93, (abs(indicator_score) * settings.indicator_weight) + (ml_confidence * settings.ml_weight) + trend_strength),
    )

    now = datetime.utcnow()
    signal = Signal(
        asset=payload.asset,
        asset_category=payload.category,
        direction=direction,
        timeframe=payload.timeframe,
        duration_sec=TIMEFRAME_SECONDS[payload.timeframe],
        open_price=Decimal(str(close)),
        close_price=None,
        confidence=confidence,
        indicator_score=indicator_score,
        ml_confidence=ml_confidence,
        created_at=now,
        expires_at=now + timedelta(seconds=TIMEFRAME_SECONDS[payload.timeframe]),
        result="PENDING",
        agent_id=f"manual_{user.id}",
    )
    db.add(signal)
    await db.commit()
    await db.refresh(signal)

    return SignalAnalyzeResponse(
        status="SIGNAL",
        signal=signal,
        message="Анализ готов. Сигнал добавлен в ленту.",
    )

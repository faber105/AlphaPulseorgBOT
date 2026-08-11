import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx
import pandas as pd
import yfinance as yf

from config import get_settings

logger = logging.getLogger(__name__)

ASSETS: dict[str, list[str]] = {
    "forex": [
        "EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "NZD/USD", "USD/CAD",
        "USD/CHF", "EUR/GBP", "EUR/JPY", "EUR/CHF", "EUR/NZD", "EUR/HUF",
        "EUR/TRY", "EUR/RUB", "GBP/JPY", "GBP/AUD", "AUD/JPY", "AUD/CAD",
        "AUD/CHF", "AUD/NZD", "CAD/JPY", "CAD/CHF", "CHF/JPY", "CHF/NOK",
        "NZD/JPY", "USD/BRL", "USD/RUB", "USD/MXN", "USD/CNH", "USD/SGD",
        "USD/INR", "USD/PKR", "USD/IDR", "USD/BDT", "USD/PHP", "USD/THB",
        "USD/VND", "USD/MYR", "USD/COP", "USD/ARS", "USD/CLP", "USD/EGP",
        "USD/DZD", "MAD/USD", "BHD/CNY", "AED/CNY", "KES/USD", "ZAR/USD",
        "UAH/USD", "NGN/USD", "LBP/USD", "JOD/CNY", "SAR/CNY", "OMR/CNY",
        "QAR/CNY",
    ],
    "crypto": [
        "BTC/USD", "ETH/USD", "BNB/USD", "SOL/USD", "ADA/USD", "DOT/USD",
        "DOGE/USD", "LTC/USD", "LINK/USD", "AVAX/USD", "MATIC/USD", "TRX/USD",
        "TON/USD", "XRP/USD",
    ],
    "commodities": ["XAU/USD", "XAG/USD", "BRENT", "WTI", "NGAS", "PLAT", "PALL"],
    "stocks": [
        "NVDA", "AAPL", "MSFT", "AMZN", "TSLA", "META", "NFLX", "GOOGL",
        "AMD", "INTC", "V", "C", "XOM", "BA", "MCD", "PFE", "JNJ",
        "BABA", "CSCO", "AXP", "FDX", "GME", "PLTR", "MARA", "COIN",
    ],
    "indices": ["SP500", "US100", "DJI30", "D30EUR", "F40EUR", "E35EUR", "E50EUR", "100GBP", "JPN225", "AUS200", "VIX"],
}

TIMEFRAME_SECONDS = {"15s": 15, "1m": 60, "3m": 180, "5m": 300, "15m": 900, "1h": 3600}
YFINANCE_INTERVALS = {"15s": "1m", "1m": "1m", "3m": "1m", "5m": "5m", "15m": "15m", "1h": "60m"}

YFINANCE_SYMBOLS: dict[str, str] = {
    "XAU/USD": "GC=F",
    "XAG/USD": "SI=F",
    "BRENT": "BZ=F",
    "WTI": "CL=F",
    "NGAS": "NG=F",
    "PLAT": "PL=F",
    "PALL": "PA=F",
    "SP500": "^GSPC",
    "US100": "^IXIC",
    "DJI30": "^DJI",
    "D30EUR": "^GDAXI",
    "F40EUR": "^FCHI",
    "E35EUR": "^IBEX",
    "E50EUR": "^STOXX50E",
    "100GBP": "^FTSE",
    "JPN225": "^N225",
    "AUS200": "^AXJO",
    "VIX": "^VIX",
}


@dataclass(frozen=True)
class AssetRef:
    asset: str
    category: str


def get_asset_category(asset: str) -> str:
    for category, assets in ASSETS.items():
        if asset in assets:
            return category
    raise ValueError(f"Unknown asset: {asset}")


def iter_assets() -> list[AssetRef]:
    return [AssetRef(asset=asset, category=category) for category, assets in ASSETS.items() for asset in assets]


def to_binance_symbol(asset: str) -> str:
    base, quote = asset.split("/")
    if quote == "USD":
        quote = "USDT"
    return f"{base}{quote}".upper()


def to_yfinance_symbol(asset: str, category: str) -> str:
    if asset in YFINANCE_SYMBOLS:
        return YFINANCE_SYMBOLS[asset]
    if category == "forex":
        base, quote = asset.split("/")
        return f"{base}{quote}=X"
    if category == "crypto":
        base, quote = asset.split("/")
        return f"{base}-{quote}"
    return asset


def normalize_yfinance_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = [col[0].lower() for col in frame.columns]
    else:
        frame.columns = [str(col).lower() for col in frame.columns]
    frame = frame.reset_index()
    timestamp_column = "datetime" if "datetime" in frame.columns else frame.columns[0]
    volume = frame["volume"] if "volume" in frame.columns else 0
    result = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(frame[timestamp_column], utc=True).dt.tz_localize(None),
            "open": pd.to_numeric(frame["open"], errors="coerce"),
            "high": pd.to_numeric(frame["high"], errors="coerce"),
            "low": pd.to_numeric(frame["low"], errors="coerce"),
            "close": pd.to_numeric(frame["close"], errors="coerce"),
            "volume": pd.to_numeric(volume, errors="coerce").fillna(0),
        }
    )
    return result.dropna(subset=["open", "high", "low", "close"]).tail(250)


class MarketDataFetcher:
    """Fetches and normalizes OHLCV candles from the configured public data sources."""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def fetch_binance_candles(self, asset: str, timeframe: str, limit: int = 250) -> pd.DataFrame:
        interval = "1m" if timeframe == "15s" else timeframe
        symbol = to_binance_symbol(asset)
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            rows: list[list[Any]] = response.json()
        return pd.DataFrame(
            {
                "timestamp": [pd.to_datetime(row[0], unit="ms", utc=True).tz_localize(None) for row in rows],
                "open": [float(row[1]) for row in rows],
                "high": [float(row[2]) for row in rows],
                "low": [float(row[3]) for row in rows],
                "close": [float(row[4]) for row in rows],
                "volume": [float(row[5]) for row in rows],
            }
        )

    async def fetch_yfinance_candles(self, asset: str, category: str, timeframe: str) -> pd.DataFrame:
        symbol = to_yfinance_symbol(asset, category)
        interval = YFINANCE_INTERVALS.get(timeframe, "1m")
        period = "7d" if interval in {"1m", "5m", "15m"} else "60d"

        def download() -> pd.DataFrame:
            return yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=False)

        frame = await asyncio.to_thread(download)
        return normalize_yfinance_frame(frame)

    async def fetch_exchange_rate_quote(self, asset: str) -> float:
        if not self.settings.exchangerate_api_key:
            raise RuntimeError("EXCHANGERATE_API_KEY is not configured")
        base, target = asset.split("/")
        url = f"https://v6.exchangerate-api.com/v6/{self.settings.exchangerate_api_key}/pair/{base}/{target}"
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        return float(data["conversion_rate"])

    async def fetch_candles(self, asset: str, category: str, timeframe: str) -> pd.DataFrame:
        try:
            if category == "crypto":
                return await self.fetch_binance_candles(asset, timeframe)
            return await self.fetch_yfinance_candles(asset, category, timeframe)
        except Exception as exc:
            logger.warning("Primary fetch failed for %s/%s: %s", asset, timeframe, exc)
            if category == "forex":
                quote = await self.fetch_exchange_rate_quote(asset)
                now = pd.Timestamp.utcnow().tz_localize(None)
                return pd.DataFrame(
                    [{"timestamp": now, "open": quote, "high": quote, "low": quote, "close": quote, "volume": 0.0}]
                )
            raise

    async def fetch_all(self, timeframe: str) -> dict[str, pd.DataFrame]:
        async def load(ref: AssetRef) -> tuple[str, pd.DataFrame | None]:
            try:
                return ref.asset, await self.fetch_candles(ref.asset, ref.category, timeframe)
            except Exception as exc:
                logger.exception("Failed to fetch candles for %s: %s", ref.asset, exc)
                return ref.asset, None

        results = await asyncio.gather(*(load(ref) for ref in iter_assets()))
        return {asset: frame for asset, frame in results if frame is not None and len(frame) >= 30}


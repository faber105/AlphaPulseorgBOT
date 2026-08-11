"""Pocket Option market adapter.

The platform does not publish a stable, supported public trading API. This module
therefore defaults to demo mode and data-only operation. It refuses live trading
unless explicitly enabled in code and configuration, so accidental real-money
orders cannot happen during testing.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class PocketOptionConfig:
    enabled: bool = False
    demo: bool = True
    ssid: str = ""
    websocket_url: str = ""
    asset: str = "EURUSD"
    timeframe: str = "1m"

    @classmethod
    def from_env(cls) -> "PocketOptionConfig":
        return cls(
            enabled=os.getenv("POCKET_OPTION_ENABLED", "false").lower() == "true",
            demo=os.getenv("POCKET_OPTION_DEMO", "true").lower() == "true",
            ssid=os.getenv("POCKET_OPTION_SSID", ""),
            websocket_url=os.getenv("POCKET_OPTION_WS_URL", ""),
            asset=os.getenv("POCKET_OPTION_ASSET", "EURUSD"),
            timeframe=os.getenv("POCKET_OPTION_TIMEFRAME", "1m"),
        )


class PocketOptionDemoAdapter:
    """Safe integration boundary for candles and demo execution.

    No credentials are logged. No live order path exists in this first version.
    A provider-specific WebSocket implementation can be injected once its current
    protocol and account permissions are verified.
    """

    def __init__(self, config: PocketOptionConfig | None = None) -> None:
        self.config = config or PocketOptionConfig.from_env()
        if self.config.enabled and not self.config.demo:
            raise RuntimeError("Live Pocket Option mode is disabled in this adapter")

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self.config.enabled,
            "demo": self.config.demo,
            "asset": self.config.asset,
            "timeframe": self.config.timeframe,
            "connected": False,
            "mode": "data-only until provider protocol is configured",
        }

    async def fetch_candles(self, limit: int = 250) -> list[dict[str, Any]]:
        if not self.config.enabled:
            return []
        if not self.config.websocket_url:
            raise RuntimeError("POCKET_OPTION_WS_URL is required for demo market data")
        raise NotImplementedError(
            "Configure the verified Pocket Option demo WebSocket protocol before use"
        )

    async def place_demo_order(self, direction: str, amount: float, duration: int) -> dict[str, Any]:
        if not self.config.enabled or not self.config.demo:
            raise RuntimeError("Demo adapter is disabled or not in demo mode")
        if direction not in {"CALL", "PUT"} or amount <= 0 or duration <= 0:
            raise ValueError("Invalid demo order")
        return {"accepted": False, "reason": "execution is intentionally disabled pending protocol verification"}

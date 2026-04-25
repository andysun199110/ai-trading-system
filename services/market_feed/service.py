from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import fmean
from typing import Any

from services.market_feed.mt5_http_provider import fetch_bars as fetch_bars_http
from services.market_feed.mt5_wine_provider import fetch_bars
from shared.constants.domain import SYMBOL_XAUUSD


@dataclass
class ServiceResult:
    status: str
    payload: dict[str, Any]


class Service:
    """Builds normalized market snapshots for XAUUSD across H1/M15/M5."""

    def run(self, payload: dict[str, Any] | None = None) -> ServiceResult:
        data = payload or {}
        symbol = data.get("symbol", SYMBOL_XAUUSD)
        if symbol != SYMBOL_XAUUSD:
            return ServiceResult(status="blocked", payload={"reason": "symbol_not_allowed", "symbol": symbol})

        source = data.get("source", "mt5")
        bars = data.get("bars", {})
        if not bars and source in {"mt5_http", "mt5_wine", "mt5linux"}:
            provider_result = (
                fetch_bars_http(symbol=symbol, timeframe="M5", count=120)
                if source == "mt5_http"
                else fetch_bars(symbol=symbol, timeframe="M5", count=120)
            )
            if provider_result.ok:
                bars = {"M5": provider_result.bars}
        snapshot = {
            "symbol": symbol,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "timeframes": {
                tf: self._normalize_bars(tf_bars)
                for tf, tf_bars in bars.items()
                if tf in {"H1", "M15", "M5"}
            },
            "spread": data.get("spread", 0.0),
            "session": data.get("session", "unknown"),
            "source": source,
        }
        return ServiceResult(status="ok", payload=snapshot)

    def _normalize_bars(self, bars: list[dict[str, Any]]) -> dict[str, Any]:
        if not bars:
            return {"count": 0, "last_close": None, "atr": 0.0}
        closes = [float(b["close"]) for b in bars]
        highs = [float(b["high"]) for b in bars]
        lows = [float(b["low"]) for b in bars]
        trs = [max(h - l, abs(h - c), abs(l - c)) for h, l, c in zip(highs, lows, closes, strict=False)]
        atr = fmean(trs[-14:]) if trs else 0.0
        return {
            "count": len(bars),
            "last_close": closes[-1],
            "high": max(highs),
            "low": min(lows),
            "atr": round(atr, 6),
            "closed_bar_time": bars[-1].get("time"),
        }

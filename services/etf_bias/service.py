from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class ServiceResult:
    status: str
    payload: dict[str, Any]


ETF_SYMBOLS = ("GLD", "IAU", "SGOL")


class Service:
    """Computes medium-term ETF bias from GLD/IAU/SGOL daily+4H snapshots."""

    def run(self, payload: dict[str, Any] | None = None) -> ServiceResult:
        data = payload or {}
        daily = data.get("daily", {})
        h4 = data.get("h4", {})

        votes: list[float] = []
        notes: list[str] = []
        for symbol in ETF_SYMBOLS:
            d = daily.get(symbol, 0.0)
            h = h4.get(symbol, 0.0)
            score = (d * 0.7) + (h * 0.3)
            votes.append(score)
            notes.append(f"{symbol}:{score:+.3f}")

        aggregate = sum(votes) / max(len(votes), 1)
        if aggregate > 0.1:
            bias = "bullish"
        elif aggregate < -0.1:
            bias = "bearish"
        else:
            bias = "neutral"

        return ServiceResult(
            status="ok",
            payload={
                "ETF_BIAS": bias,
                "strength_score": round(min(1.0, abs(aggregate)), 3),
                "notes": notes,
                "last_daily_update": datetime.now(timezone.utc).isoformat(),
                "last_h4_refresh": datetime.now(timezone.utc).isoformat(),
            },
        )

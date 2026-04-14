from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from shared.constants.domain import SYMBOL_XAUUSD
from shared.schemas.trading import Bar


@dataclass
class FeedSnapshot:
    symbol: str
    timeframe: str
    bars: list[Bar]
    source: str


class MarketFeedService:
    """Stage-2 deterministic feed adapter (MT5 bridge implementation can plug in later)."""

    def validate_symbol(self, symbol: str) -> None:
        if symbol != SYMBOL_XAUUSD:
            raise ValueError("only XAUUSD supported")

    def from_payload(self, symbol: str, timeframe: str, payload: list[dict]) -> FeedSnapshot:
        self.validate_symbol(symbol)
        bars = [Bar(**row) for row in payload]
        return FeedSnapshot(symbol=symbol, timeframe=timeframe, bars=bars, source="payload")

    def latest_closed_bar(self, snapshot: FeedSnapshot) -> Bar:
        if len(snapshot.bars) < 2:
            raise ValueError("at least 2 bars required to guarantee closed-bar logic")
        return snapshot.bars[-2]

    def resample_health(self, snapshot: FeedSnapshot) -> dict[str, str | int | datetime]:
        return {
            "symbol": snapshot.symbol,
            "timeframe": snapshot.timeframe,
            "bar_count": len(snapshot.bars),
            "last_ts": snapshot.bars[-1].ts if snapshot.bars else datetime.utcnow(),
        }

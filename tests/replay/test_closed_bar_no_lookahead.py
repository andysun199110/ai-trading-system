from datetime import datetime, timedelta

from services.market_feed.service import MarketFeedService


def test_latest_closed_bar_uses_penultimate() -> None:
    svc = MarketFeedService()
    t0 = datetime(2026, 1, 1)
    bars = [
        {"ts": t0, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "spread": 0.2},
        {"ts": t0 + timedelta(minutes=5), "open": 1.5, "high": 2.1, "low": 1.2, "close": 2.0, "spread": 0.2},
        {"ts": t0 + timedelta(minutes=10), "open": 2.0, "high": 2.3, "low": 1.9, "close": 2.2, "spread": 0.2},
    ]
    snap = svc.from_payload("XAUUSD", "M5", bars)
    assert svc.latest_closed_bar(snap).ts == t0 + timedelta(minutes=5)

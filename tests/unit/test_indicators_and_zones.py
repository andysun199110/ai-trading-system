from datetime import datetime, timedelta

from services.market_structure.service import MarketStructureService
from shared.schemas.trading import Bar
from shared.utils.indicators import atr


def _bars(n: int = 80, start: float = 2300.0) -> list[Bar]:
    t0 = datetime(2026, 1, 1)
    rows = []
    price = start
    for i in range(n):
        drift = 0.4 if i % 3 else -0.2
        price += drift
        rows.append(Bar(ts=t0 + timedelta(minutes=15 * i), open=price - 0.3, high=price + 0.8, low=price - 0.9, close=price, spread=0.2))
    return rows


def test_atr_positive() -> None:
    bars = _bars(30)
    a = atr([b.high for b in bars], [b.low for b in bars], [b.close for b in bars])
    assert a > 0


def test_zone_building_and_state() -> None:
    svc = MarketStructureService()
    z = svc.build_zones(_bars(), timeframe="M15")
    assert len(z) > 0
    assert z[0].lower < z[0].upper

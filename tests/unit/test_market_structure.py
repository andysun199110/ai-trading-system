import math

from services.market_structure.service import Service


def _bars(n: int, base: float = 2300.0) -> list[dict]:
    out = []
    for i in range(n):
        wave = math.sin(i / 3) * 1.5
        close = base + (i * 0.05) + wave
        out.append({"time": f"2026-01-01T{i:02d}:00:00+00:00", "open": close - 0.1, "high": close + 0.6, "low": close - 0.6, "close": close})
    return out


def test_market_structure_builds_zones_and_regime() -> None:
    svc = Service()
    out = svc.run({"H1": _bars(40), "M15": _bars(60, base=2290.0)})
    assert out.status == "ok"
    assert out.payload["h1_state"]["regime"] in {"bullish", "bearish", "range"}
    assert out.payload["zones"]

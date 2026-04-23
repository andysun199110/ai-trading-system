from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class MT5ConnectionResult:
    ok: bool
    detail: str
    bars: list[dict[str, Any]]


def _to_iso(ts: float | int) -> str:
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()


def fetch_bars(symbol: str = "XAUUSD", timeframe: str = "M5", count: int = 100) -> MT5ConnectionResult:
    """Best-effort MT5 bridge.

    1) Try local Wine Python package (MetaTrader5).
    2) Fall back to mt5linux client (RPyC bridge).
    """
    try:
        import MetaTrader5 as mt5  # type: ignore

        if not mt5.initialize(timeout=30_000):
            return MT5ConnectionResult(ok=False, detail="MetaTrader5 initialize failed", bars=[])

        tf_value = getattr(mt5, f"TIMEFRAME_{timeframe}", mt5.TIMEFRAME_M5)
        rates = mt5.copy_rates_from_pos(symbol, tf_value, 0, count)
        mt5.shutdown()

        bars = []
        for row in rates or []:
            bars.append(
                {
                    "time": _to_iso(row["time"]),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "tick_volume": int(row["tick_volume"]),
                }
            )
        return MT5ConnectionResult(ok=True, detail="MetaTrader5 via Wine", bars=bars)
    except Exception:
        pass

    try:
        from mt5linux import MetaTrader5 as LinuxMT5  # type: ignore

        mt5 = LinuxMT5(host="mt5", port=18812)
        tf_value = getattr(mt5, f"TIMEFRAME_{timeframe}", mt5.TIMEFRAME_M5)
        rates = mt5.copy_rates_from_pos(symbol, tf_value, 0, count)

        bars = []
        for row in rates or []:
            bars.append(
                {
                    "time": _to_iso(row["time"]),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "tick_volume": int(row.get("tick_volume", 0)),
                }
            )
        return MT5ConnectionResult(ok=True, detail="mt5linux bridge", bars=bars)
    except Exception as exc:
        return MT5ConnectionResult(ok=False, detail=f"MT5 bridge unavailable: {exc}", bars=[])


if __name__ == "__main__":
    result = fetch_bars()
    print({"ok": result.ok, "detail": result.detail, "count": len(result.bars)})

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx


@dataclass
class MT5HTTPResult:
    ok: bool
    detail: str
    bars: list[dict[str, Any]]


def _to_iso(value: Any) -> str:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()
    text = str(value)
    if text.endswith("Z"):
        return text.replace("Z", "+00:00")
    return text


def fetch_bars(symbol: str = "XAUUSD", timeframe: str = "M5", count: int = 100) -> MT5HTTPResult:
    base_url = os.getenv("MT5_HTTP_BASE_URL", "http://mt5:8001").rstrip("/")
    timeout_s = float(os.getenv("MT5_HTTP_TIMEOUT_SECONDS", "8"))
    endpoint = f"{base_url}/bars"
    params = {"symbol": symbol, "timeframe": timeframe, "count": count}

    try:
        with httpx.Client(timeout=timeout_s) as client:
            response = client.get(endpoint, params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception as exc:
        return MT5HTTPResult(ok=False, detail=f"mt5_http request failed: {exc}", bars=[])

    raw_bars = payload.get("bars", []) if isinstance(payload, dict) else []
    bars: list[dict[str, Any]] = []
    for row in raw_bars:
        try:
            bars.append(
                {
                    "time": _to_iso(row.get("time")),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "tick_volume": int(row.get("tick_volume", 0)),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue

    return MT5HTTPResult(ok=bool(bars), detail="mt5_http bars fetched" if bars else "mt5_http no bars", bars=bars)

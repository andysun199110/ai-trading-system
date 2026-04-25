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


def _auth_headers() -> dict[str, str]:
    token = (
        os.getenv("MT5_HTTPAPI_TOKEN")
        or os.getenv("MT5_HTTP_API_TOKEN")
        or os.getenv("MT5_HTTP_TOKEN")
        or ""
    ).strip()
    if not token:
        return {}

    mode = os.getenv("MT5_HTTP_AUTH_MODE", "bearer").strip().lower()
    if mode == "apikey":
        header_name = os.getenv("MT5_HTTP_API_KEY_HEADER", "X-API-Key").strip() or "X-API-Key"
        return {header_name: token}
    if mode == "token":
        return {"Authorization": token}
    if mode == "none":
        return {}
    return {"Authorization": f"Bearer {token}"}


def fetch_bars(symbol: str = "XAUUSD", timeframe: str = "M5", count: int = 100) -> MT5HTTPResult:
    base_url = os.getenv("MT5_HTTP_BASE_URL", "http://mt5:8001").rstrip("/")
    timeout_s = float(os.getenv("MT5_HTTP_TIMEOUT_SECONDS", "8").strip())
    bars_path = os.getenv("MT5_HTTP_BARS_PATH", "/bars").strip() or "/bars"
    endpoint = f"{base_url}{bars_path if bars_path.startswith('/') else '/' + bars_path}"
    params = {"symbol": symbol, "timeframe": timeframe, "count": count}
    headers = _auth_headers()

    try:
        with httpx.Client(timeout=timeout_s) as client:
            response = client.get(endpoint, params=params, headers=headers)
            if response.status_code == 401:
                return MT5HTTPResult(
                    ok=False,
                    detail=f"mt5_http unauthorized: 401 at {endpoint} (token_present={bool(headers)})",
                    bars=[],
                )
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

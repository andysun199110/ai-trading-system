"""
MT5 HTTP Provider - Remote Windows VPS MT5 API Client

Connects to remote MT5 HTTP API instead of local Wine/RPyC.
Compatible interface with mt5_wine_provider.py

Supports multiple authentication modes:
- bearer: Authorization: Bearer <token>
- key: X-API-Key: <key>
- none: No authentication
- auto: Try bearer > key > none
"""

import os
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

import httpx


class AuthMode(str, Enum):
    BEARER = "bearer"
    KEY = "key"
    NONE = "none"
    AUTO = "auto"


@dataclass
class Bar:
    """OHLCV bar structure compatible with Wine provider."""
    time: int  # Unix timestamp
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class FetchResult:
    """Result structure compatible with Wine provider."""
    ok: bool
    detail: str
    bars: List[Bar]


# Configuration from environment
# Support multiple env var naming conventions
MT5_HTTPAPI_URL = (
    os.getenv("MT5_HTTPAPI_URL") or
    os.getenv("MT5_HTTP_BASE_URL") or
    os.getenv("MT5_HTTP_URL") or
    "http://172.19.0.69:8000"
)
MT5_HTTPAPI_TIMEOUT = int(os.getenv("MT5_HTTPAPI_TIMEOUT") or os.getenv("MT5_HTTP_TIMEOUT") or "10")
MT5_HTTPAPI_AUTH_MODE = (
    os.getenv("MT5_HTTPAPI_AUTH_MODE") or
    os.getenv("MT5_HTTP_AUTH_MODE") or
    "auto"
).lower()
# Token: try multiple naming conventions
MT5_HTTPAPI_TOKEN = (
    os.getenv("MT5_HTTPAPI_TOKEN") or
    os.getenv("MT5_HTTP_API_TOKEN") or
    os.getenv("MT5_HTTP_TOKEN") or
    os.getenv("MT5_TOKEN") or
    ""
)
# API Key: try multiple naming conventions
MT5_HTTPAPI_KEY = (
    os.getenv("MT5_HTTPAPI_KEY") or
    os.getenv("MT5_HTTP_API_KEY") or
    os.getenv("MT5_API_KEY") or
    ""
)
# Custom bars path (if API uses non-standard endpoint)
MT5_HTTP_BARS_PATH = os.getenv("MT5_HTTP_BARS_PATH") or ""
# Custom header name for API key
MT5_HTTP_API_KEY_HEADER = os.getenv("MT5_HTTP_API_KEY_HEADER") or ""

MT5_HTTPAPI_RETRY = 3
MT5_HTTPAPI_BACKOFF = 0.5  # seconds


def _sanitize_token(token: str) -> str:
    """Sanitize token for logging - show first 2 and last 2 chars only."""
    if not token:
        return "***"
    if len(token) <= 4:
        return "****"
    return f"{token[:2]}***{token[-2:]}"


def _has_credentials() -> bool:
    """Check if any authentication credentials are configured."""
    return bool(MT5_HTTPAPI_TOKEN or MT5_HTTPAPI_KEY)


def _get_auth_headers() -> Dict[str, str]:
    """
    Get authentication headers based on configured auth mode.
    
    Returns:
        Dict of headers to include in requests
    
    Raises:
        ValueError: If auth mode requires credentials that are missing
    """
    headers = {}
    
    if MT5_HTTPAPI_AUTH_MODE == AuthMode.NONE:
        return headers
    
    if MT5_HTTPAPI_AUTH_MODE == AuthMode.BEARER:
        if not MT5_HTTPAPI_TOKEN:
            raise ValueError(
                f"CONFIG_ERROR: Token required when auth_mode=bearer. "
                f"Set MT5_HTTPAPI_TOKEN, MT5_HTTP_API_TOKEN, or MT5_HTTP_TOKEN. "
                f"Current URL: {MT5_HTTPAPI_URL}"
            )
        headers["Authorization"] = f"Bearer {MT5_HTTPAPI_TOKEN}"
        return headers
    
    if MT5_HTTPAPI_AUTH_MODE == AuthMode.KEY:
        if not MT5_HTTPAPI_KEY:
            raise ValueError(
                f"CONFIG_ERROR: API key required when auth_mode=key. "
                f"Set MT5_HTTPAPI_KEY, MT5_HTTP_API_KEY, or MT5_API_KEY. "
                f"Current URL: {MT5_HTTPAPI_URL}"
            )
        # Support custom header name
        header_name = MT5_HTTP_API_KEY_HEADER or "X-API-Key"
        headers[header_name] = MT5_HTTPAPI_KEY
        return headers
    
    if MT5_HTTPAPI_AUTH_MODE == AuthMode.AUTO:
        # Try bearer first, then key, then none
        if MT5_HTTPAPI_TOKEN:
            headers["Authorization"] = f"Bearer {MT5_HTTPAPI_TOKEN}"
        elif MT5_HTTPAPI_KEY:
            header_name = MT5_HTTP_API_KEY_HEADER or "X-API-Key"
            headers[header_name] = MT5_HTTPAPI_KEY
        # else: no headers
        return headers
    
    return headers


def _classify_error(status_code: int, endpoint: str, message: str = "") -> str:
    """
    Classify HTTP errors with proper categorization.
    
    Args:
        status_code: HTTP status code
        endpoint: API endpoint path
        message: Additional error message
    
    Returns:
        Formatted error string with category and details
    """
    base = f"Status {status_code} at {endpoint}"
    if message:
        base = f"{base} - {message}"
    
    if status_code == 401:
        return f"AUTH_FAIL: {base}"
    elif status_code == 403:
        return f"AUTH_FORBIDDEN: {base}"
    elif status_code == 429:
        return f"RATE_LIMIT: {base}"
    elif 500 <= status_code < 600:
        return f"UPSTREAM_ERROR: {base}"
    elif 400 <= status_code < 500:
        return f"CLIENT_ERROR: {base}"
    else:
        return f"HTTP_FAIL: {base}"


def _parse_bar(raw: Dict[str, Any]) -> Bar:
    """
    Parse raw API response into Bar object.
    
    Handles common field naming conventions:
    - time: time, datetime, timestamp, ctime, t, date
    - open: open, o, Open
    - high: high, h, High
    - low: low, l, Low
    - close: close, c, Close
    - volume: volume, vol, tick_volume, Volume
    """
    # Time field mapping
    time_val = None
    for key in ["time", "datetime", "timestamp", "ctime", "t", "date", "Time"]:
        if key in raw:
            time_val = raw[key]
            break
    
    if isinstance(time_val, str):
        # ISO format or datetime string - convert to timestamp
        from datetime import datetime
        try:
            if "T" in time_val:
                dt = datetime.fromisoformat(time_val.replace("Z", "+00:00"))
            elif "." in time_val and len(time_val) > 10:
                dt = datetime.strptime(time_val, "%Y.%m.%d %H:%M:%S")
            else:
                dt = datetime.fromtimestamp(int(time_val))
            time_val = int(dt.timestamp())
        except Exception:
            time_val = 0
    elif isinstance(time_val, (int, float)):
        # Already a timestamp
        time_val = int(time_val)
    else:
        time_val = 0
    
    # OHLCV field mapping
    open_val = raw.get("open") or raw.get("o") or raw.get("Open") or 0
    high_val = raw.get("high") or raw.get("h") or raw.get("High") or 0
    low_val = raw.get("low") or raw.get("l") or raw.get("Low") or 0
    close_val = raw.get("close") or raw.get("c") or raw.get("Close") or 0
    volume_val = raw.get("volume") or raw.get("vol") or raw.get("tick_volume") or raw.get("Volume") or 0
    
    return Bar(
        time=time_val,
        open=float(open_val),
        high=float(high_val),
        low=float(low_val),
        close=float(close_val),
        volume=int(volume_val)
    )


def _extract_bars_from_response(data: Any) -> List[Dict[str, Any]]:
    """
    Extract bars array from various API response structures.
    
    Priority:
    1. Direct list (top-level array) - PRIMARY FORMAT for /symbols/{symbol}/rates
    2. Wrapped in dict: {"bars": [...], "data": [...], "result": [...]}
    3. Nested structures
    """
    # PRIMARY: Top-level list (actual API response format)
    if isinstance(data, list):
        return data
    
    if isinstance(data, dict):
        # Fallback: Wrapped in dict
        for key in ["bars", "data", "klines", "candles", "result", "records", "items"]:
            if key in data and isinstance(data[key], list):
                return data[key]
        
        # Check nested structures
        for key in ["response", "body", "payload"]:
            if key in data and isinstance(data[key], dict):
                nested = _extract_bars_from_response(data[key])
                if nested:
                    return nested
        
        # Check if the dict itself looks like a bar (has OHLC fields)
        if any(k in data for k in ["open", "high", "low", "close", "time"]):
            return [data]
    
    return []


def _fetch_with_retry(
    client: httpx.Client,
    endpoint: str,
    params: Dict[str, Any],
    headers: Dict[str, str]
) -> httpx.Response:
    """
    Fetch with exponential backoff retry.
    
    Args:
        client: httpx client instance
        endpoint: API endpoint path
        params: Query parameters
        headers: Authentication headers
    
    Returns:
        httpx Response object
    
    Raises:
        Exception with classified error message
    """
    url = endpoint.lstrip("/")
    last_error = None
    
    for attempt in range(MT5_HTTPAPI_RETRY):
        try:
            response = client.get(url, params=params, headers=headers, timeout=MT5_HTTPAPI_TIMEOUT)
            
            # Check for auth errors - don't retry these
            if response.status_code in [401, 403]:
                error_msg = _classify_error(
                    response.status_code, 
                    endpoint,
                    response.json().get("error", "Invalid or missing credentials") if response.content else ""
                )
                raise Exception(error_msg)
            
            # Check for rate limiting
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                if retry_after and attempt < MT5_HTTPAPI_RETRY - 1:
                    wait_time = min(int(retry_after), 10)  # Cap at 10s
                    time.sleep(wait_time)
                    continue
                error_msg = _classify_error(
                    response.status_code,
                    endpoint,
                    "Too many requests"
                )
                raise Exception(error_msg)
            
            response.raise_for_status()
            return response
            
        except httpx.TimeoutException as e:
            last_error = f"TIMEOUT: Request timed out after {MT5_HTTPAPI_TIMEOUT}s at {endpoint}"
        except httpx.HTTPStatusError as e:
            error_msg = _classify_error(
                e.response.status_code,
                endpoint,
                str(e)
            )
            last_error = error_msg
            if e.response.status_code < 500 and e.response.status_code not in [429]:
                # Client error (not 429) - don't retry
                break
        except httpx.RequestError as e:
            last_error = f"HTTP_FAIL: {str(e)} at {endpoint}"
        except ValueError as e:
            # Config errors
            raise e
        except Exception as e:
            last_error = f"BAD_PAYLOAD: {str(e)}"
        
        if attempt < MT5_HTTPAPI_RETRY - 1:
            wait_time = MT5_HTTPAPI_BACKOFF * (2 ** attempt)
            time.sleep(wait_time)
    
    raise Exception(last_error)


def fetch_bars(
    symbol: str = "XAUUSD",
    timeframe: str = "M5",
    count: int = 100
) -> FetchResult:
    """
    Fetch historical bars from remote MT5 HTTP API.
    
    Args:
        symbol: Trading symbol (e.g., "XAUUSD", "EURUSD")
        timeframe: Timeframe (e.g., "M1", "M5", "M15", "H1", "H4", "D1")
        count: Number of bars to fetch
    
    Returns:
        FetchResult with ok/detail/bars structure
    
    Error Classification:
        - AUTH_FAIL: 401 Unauthorized
        - AUTH_FORBIDDEN: 403 Forbidden
        - RATE_LIMIT: 429 Too Many Requests
        - UPSTREAM_ERROR: 5xx Server errors
        - TIMEOUT: Request timeout
        - BAD_PAYLOAD: Invalid response format
        - EMPTY_DATA: No bars returned
        - CONFIG_ERROR: Missing required configuration
    """
    # Map timeframe to API format if needed
    timeframe_map = {
        "M1": "M1", "M5": "M5", "M15": "M15", "M30": "M30",
        "H1": "H1", "H4": "H4", "D1": "D1", "W1": "W1", "MN1": "MN1"
    }
    tf = timeframe_map.get(timeframe, timeframe)
    
    # Get auth headers
    try:
        headers = _get_auth_headers()
    except ValueError as e:
        return FetchResult(ok=False, detail=str(e), bars=[])
    
    # Prepare query parameters (symbol is in path, not query)
    params = {
        "timeframe": tf,
        "count": count
    }
    
    try:
        with httpx.Client(base_url=MT5_HTTPAPI_URL) as client:
            # Use correct endpoint pattern: /symbols/{symbol}/rates
            # This is the verified working endpoint for the Windows MT5 HTTP API
            endpoint = f"/symbols/{symbol}/rates"
            
            # Fetch from the correct endpoint
            response = _fetch_with_retry(client, endpoint, params, headers)
            
            # Parse response
            try:
                data = response.json()
            except Exception as e:
                return FetchResult(
                    ok=False,
                    detail=f"BAD_PAYLOAD: Failed to parse JSON response at {response.url}: {e}",
                    bars=[]
                )
            
            # Extract bars from response
            raw_bars = _extract_bars_from_response(data)
            
            if not raw_bars:
                # Check if API returned an error message
                if isinstance(data, dict) and "error" in data:
                    return FetchResult(
                        ok=False,
                        detail=f"API error: {data['error']}",
                        bars=[]
                    )
                return FetchResult(
                    ok=False,
                    detail=f"EMPTY_DATA: No bars returned from API (response: {str(data)[:200]})",
                    bars=[]
                )
            
            # Parse bars
            try:
                bars = [_parse_bar(b) for b in raw_bars]
            except Exception as e:
                return FetchResult(
                    ok=False,
                    detail=f"BAD_PAYLOAD: Failed to parse bars: {e}",
                    bars=[]
                )
            
            return FetchResult(
                ok=True,
                detail=f"Fetched {len(bars)} bars for {symbol} {timeframe}",
                bars=bars
            )
            
    except ValueError as e:
        # Config errors
        return FetchResult(ok=False, detail=str(e), bars=[])
    except Exception as e:
        error_str = str(e)
        # Return classified error
        if any(code in error_str for code in ["AUTH_FAIL", "AUTH_FORBIDDEN", "RATE_LIMIT", "UPSTREAM_ERROR"]):
            return FetchResult(ok=False, detail=error_str, bars=[])
        elif "TIMEOUT" in error_str:
            return FetchResult(ok=False, detail=error_str, bars=[])
        elif "HTTP_FAIL" in error_str:
            return FetchResult(ok=False, detail=error_str, bars=[])
        elif "BAD_PAYLOAD" in error_str:
            return FetchResult(ok=False, detail=error_str, bars=[])
        else:
            return FetchResult(ok=False, detail=f"UNKNOWN_ERROR: {error_str}", bars=[])


def get_rates(
    symbol: str,
    timeframe: str,
    count: int
) -> FetchResult:
    """Alias for fetch_bars - compatible with Wine provider interface."""
    return fetch_bars(symbol=symbol, timeframe=timeframe, count=count)


if __name__ == "__main__":
    # Quick test
    print(f"URL: {MT5_HTTPAPI_URL}")
    print(f"Auth mode: {MT5_HTTPAPI_AUTH_MODE}")
    print(f"Token: {_sanitize_token(MT5_HTTPAPI_TOKEN)}")
    print(f"Key: {_sanitize_token(MT5_HTTPAPI_KEY)}")
    print(f"Has credentials: {_has_credentials()}")
    print()
    result = fetch_bars(symbol="XAUUSD", timeframe="M5", count=5)
    print(f"ok={result.ok}")
    print(f"detail={result.detail}")
    print(f"count={len(result.bars)}")
    if result.bars:
        print(f"sample={result.bars[:2]}")

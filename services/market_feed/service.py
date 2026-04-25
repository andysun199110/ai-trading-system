"""
Market Feed Service - Main Entry Point

Supports multiple data sources:
- mt5_http: Remote Windows VPS HTTP API (production)
- mt5_wine: Local Wine/RPyC (legacy/backup)
"""

import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from .mt5_http_provider import fetch_bars as http_fetch_bars


@dataclass
class ServiceResult:
    """Service execution result."""
    status: str  # "success" | "error"
    payload: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class Service:
    """Market Feed Service."""
    
    def __init__(self):
        self.default_source = os.getenv("MT5_SOURCE", "mt5_http")
    
    def run(self, params: Dict[str, Any]) -> ServiceResult:
        """
        Execute market feed request.
        
        Args:
            params: Request parameters
                - source: Data source ("mt5_http" | "mt5_wine")
                - symbol: Trading symbol (default: "XAUUSD")
                - timeframes: List of timeframes (default: ["M5", "H1"])
                - count: Bars per timeframe (default: 100)
        
        Returns:
            ServiceResult with payload structure:
            {
                "symbol": str,
                "generated_at": str,
                "timeframes": {
                    "M5": {"count": int, "bars": [...], "source": str},
                    "H1": {...}
                },
                "spread": float,
                "session": str,
                "source": str
            }
        """
        source = params.get("source", self.default_source)
        symbol = params.get("symbol", "XAUUSD")
        timeframes = params.get("timeframes", ["M5", "H1"])
        count = params.get("count", 100)
        
        try:
            if source == "mt5_http":
                return self._fetch_http(symbol, timeframes, count)
            elif source == "mt5_wine":
                return self._fetch_wine(symbol, timeframes, count)
            else:
                return ServiceResult(
                    status="error",
                    error=f"Unknown source: {source}"
                )
        except Exception as e:
            return ServiceResult(
                status="error",
                error=str(e)
            )
    
    def _fetch_http(
        self,
        symbol: str,
        timeframes: list,
        count: int
    ) -> ServiceResult:
        """Fetch from HTTP provider."""
        result = {
            "symbol": symbol,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "timeframes": {},
            "spread": 0.0,
            "session": "auto",
            "source": "mt5_http"
        }
        
        for tf in timeframes:
            fetch_result = http_fetch_bars(
                symbol=symbol,
                timeframe=tf,
                count=count
            )
            
            if fetch_result.ok:
                result["timeframes"][tf] = {
                    "count": len(fetch_result.bars),
                    "bars": [
                        {
                            "time": b.time,
                            "open": b.open,
                            "high": b.high,
                            "low": b.low,
                            "close": b.close,
                            "volume": b.volume
                        }
                        for b in fetch_result.bars
                    ],
                    "source": "mt5_http"
                }
            else:
                # Return partial result with error detail
                result["timeframes"][tf] = {
                    "count": 0,
                    "bars": [],
                    "source": "mt5_http",
                    "error": fetch_result.detail
                }
        
        # Determine overall status
        successful_tfs = [
            tf for tf, data in result["timeframes"].items()
            if data.get("count", 0) > 0
        ]
        
        if successful_tfs:
            return ServiceResult(status="success", payload=result)
        else:
            errors = [
                data.get("error", "unknown")
                for data in result["timeframes"].values()
            ]
            return ServiceResult(
                status="error",
                payload=result,
                error=f"All timeframes failed: {'; '.join(errors)}"
            )
    
    def _fetch_wine(
        self,
        symbol: str,
        timeframes: list,
        count: int
    ) -> ServiceResult:
        """Fetch from Wine provider (legacy/backup)."""
        # Wine provider not available - HTTP is primary
        return ServiceResult(
            status="error",
            error="Wine provider not available - use mt5_http source"
        )


if __name__ == "__main__":
    # Quick test
    result = Service().run({
        "source": "mt5_http",
        "symbol": "XAUUSD",
        "timeframes": ["M5"],
        "count": 5
    })
    print(f"status={result.status}")
    print(f"payload={result.payload}")
    if result.error:
        print(f"error={result.error}")

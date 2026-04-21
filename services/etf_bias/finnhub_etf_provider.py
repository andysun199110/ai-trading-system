"""Finnhub ETF Provider for Stage 2."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

ETF_SYMBOLS = ["GLD", "IAU", "SGOL"]


class FinnhubETFProvider:
    """Finnhub ETF data provider with daily + 4H refresh strategy."""
    
    BASE_URL = "https://finnhub.io/api/v1/quote"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._daily_cache: dict[str, float] = {}
        self._h4_cache: dict[str, float] = {}
        self._daily_time: Optional[datetime] = None
        self._h4_time: Optional[datetime] = None
    
    def _needs_daily_refresh(self) -> bool:
        """Check if daily cache needs refresh (>24h old)."""
        if not self._daily_time:
            return True
        age = (datetime.now(timezone.utc) - self._daily_time).total_seconds()
        return age > 86400  # 24 hours
    
    def _needs_h4_refresh(self) -> bool:
        """Check if 4H cache needs refresh (>4h old)."""
        if not self._h4_time:
            return True
        age = (datetime.now(timezone.utc) - self._h4_time).total_seconds()
        return age > 14400  # 4 hours
    
    def get_etf_quotes(self, symbols: Optional[list[str]] = None) -> dict[str, float]:
        """Get current ETF quotes with smart caching."""
        symbols = symbols or ETF_SYMBOLS
        result = {}
        
        # Try to return cached data if valid
        if not self._needs_daily_refresh():
            for sym in symbols:
                if sym in self._daily_cache:
                    result[sym] = self._daily_cache[sym]
        
        # Fetch fresh data
        try:
            with httpx.Client(timeout=10.0) as client:
                for symbol in symbols:
                    params = {"symbol": symbol, "token": self.api_key}
                    response = client.get(self.BASE_URL, params=params)
                    if response.status_code == 200:
                        data = response.json()
                        price = data.get("c", 0.0)  # Current price
                        result[symbol] = price
                        
                        # Update cache
                        now = datetime.now(timezone.utc)
                        if self._needs_daily_refresh():
                            self._daily_cache[symbol] = price
                            self._daily_time = now
                        
                        if self._needs_h4_refresh():
                            self._h4_cache[symbol] = price
                            self._h4_time = now
            
            logger.info(f"Fetched ETF quotes: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Finnhub ETF fetch error: {e}")
            # Return cached data on error
            return result or {s: 0.0 for s in symbols}
    
    def compute_bias(self) -> dict[str, Any]:
        """Compute ETF bias score from GLD/IAU/SGOL."""
        quotes = self.get_etf_quotes()
        
        # Simple bias: compare current to 24h ago (simplified)
        votes = []
        notes = []
        
        for symbol, price in quotes.items():
            # Placeholder: in production, compare to historical
            # For now, use price momentum proxy
            vote = 0.0  # Neutral until we have historical data
            votes.append(vote)
            notes.append(f"{symbol}:{vote:+.3f}")
        
        aggregate = sum(votes) / max(len(votes), 1)
        
        if aggregate > 0.1:
            bias = "bullish"
        elif aggregate < -0.1:
            bias = "bearish"
        else:
            bias = "neutral"
        
        return {
            "ETF_BIAS": bias,
            "strength_score": round(min(1.0, abs(aggregate)), 3),
            "notes": notes,
            "last_daily_update": self._daily_time.isoformat() if self._daily_time else None,
            "last_h4_refresh": self._h4_time.isoformat() if self._h4_time else None,
        }

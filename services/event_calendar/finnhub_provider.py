"""Finnhub Event Calendar Provider for Stage 2."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class FinnhubEventProvider:
    """Finnhub economic calendar provider."""
    
    BASE_URL = "https://finnhub.io/api/v1/calendar/economic"
    
    def __init__(self, api_key: str, cache_ttl_seconds: int = 300):
        self.api_key = api_key
        self.cache_ttl = cache_ttl_seconds
        self._cache: Optional[dict] = None
        self._cache_time: Optional[datetime] = None
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._cache_time:
            return False
        age = (datetime.now(timezone.utc) - self._cache_time).total_seconds()
        return age < self.cache_ttl
    
    def get_events(self, from_date: Optional[str] = None, to_date: Optional[str] = None) -> list[dict[str, Any]]:
        """Fetch economic calendar events from Finnhub."""
        if self._is_cache_valid():
            logger.debug("Returning cached events")
            return self._cache.get("events", [])
        
        try:
            # Default to 7 days window
            if not from_date:
                from_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            if not to_date:
                to_date = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
            
            params = {
                "from": from_date,
                "to": to_date,
                "token": self.api_key,
            }
            
            with httpx.Client(timeout=10.0) as client:
                response = client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()
            
            events = self._normalize_events(data.get("economicCalendar", []))
            self._cache = {"events": events}
            self._cache_time = datetime.now(timezone.utc)
            
            logger.info(f"Fetched {len(events)} events from Finnhub")
            return events
            
        except httpx.TimeoutException:
            logger.warning("Finnhub timeout, returning stale cache")
            return self._cache.get("events", []) if self._cache else []
        except Exception as e:
            logger.error(f"Finnhub API error: {e}")
            return self._cache.get("events", []) if self._cache else []
    
    def _normalize_events(self, raw_events: list) -> list[dict[str, Any]]:
        """Normalize Finnhub events to internal format."""
        normalized = []
        for event in raw_events:
            try:
                event_time = datetime.fromisoformat(event.get("time", "").replace("Z", "+00:00"))
            except Exception:
                event_time = datetime.now(timezone.utc)
            
            impact = event.get("impact", "").lower()
            if impact not in ("high", "medium", "low"):
                impact = "medium"
            
            normalized.append({
                "name": event.get("event", "unknown"),
                "time": event_time.isoformat(),
                "impact": impact,
                "country": event.get("country", "US"),
                "actual": event.get("actual"),
                "estimate": event.get("estimate"),
                "previous": event.get("prev"),
            })
        
        return normalized

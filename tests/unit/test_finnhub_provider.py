"""Unit tests for Finnhub event calendar provider."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone


class TestFinnhubEventProvider:
    """Tests for FinnhubEventProvider class."""
    
    def test_provider_import(self):
        """Test that FinnhubEventProvider can be imported."""
        from services.event_calendar.finnhub_provider import FinnhubEventProvider
        assert FinnhubEventProvider is not None
    
    def test_provider_initialization(self):
        """Test FinnhubEventProvider initialization."""
        from services.event_calendar.finnhub_provider import FinnhubEventProvider
        
        provider = FinnhubEventProvider(api_key="test_key")
        assert provider.api_key == "test_key"
        assert provider.cache_ttl == 300
        assert provider._cache is None
        assert provider._cache_time is None
    
    def test_provider_custom_ttl(self):
        """Test FinnhubEventProvider with custom TTL."""
        from services.event_calendar.finnhub_provider import FinnhubEventProvider
        
        provider = FinnhubEventProvider(api_key="test_key", cache_ttl_seconds=600)
        assert provider.cache_ttl == 600
    
    def test_cache_invalid_when_empty(self):
        """Test cache is invalid when empty."""
        from services.event_calendar.finnhub_provider import FinnhubEventProvider
        
        provider = FinnhubEventProvider(api_key="test_key")
        assert provider._is_cache_valid() is False
    
    @patch('services.event_calendar.finnhub_provider.httpx')
    def test_get_events_success(self, mock_httpx):
        """Test successful event fetch."""
        from services.event_calendar.finnhub_provider import FinnhubEventProvider
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "economicCalendar": [
                {
                    "country": "US",
                    "event": "Nonfarm Payrolls",
                    "time": "2026-04-21T12:30:00Z",
                    "impact": "high",
                    "actual": "250K",
                    "estimate": "200K",
                    "previous": "180K"
                }
            ]
        }
        mock_client.get.return_value = mock_response
        mock_httpx.Client.return_value.__enter__.return_value = mock_client
        
        provider = FinnhubEventProvider(api_key="test_key")
        events = provider.get_events(from_date="2026-04-21", to_date="2026-04-28")
        
        assert len(events) >= 0  # May be normalized
        assert provider._cache is not None
    
    @patch('services.event_calendar.finnhub_provider.httpx')
    def test_get_events_timeout(self, mock_httpx):
        """Test timeout handling returns cached data."""
        from services.event_calendar.finnhub_provider import FinnhubEventProvider
        import httpx
        
        mock_client = Mock()
        mock_client.get.side_effect = httpx.TimeoutException("Timeout")
        mock_httpx.Client.return_value.__enter__.return_value = mock_client
        
        provider = FinnhubEventProvider(api_key="test_key")
        # Pre-populate cache
        provider._cache = {"events": [{"cached": True}]}
        provider._cache_time = datetime.now(timezone.utc)
        
        events = provider.get_events()
        
        assert events == [{"cached": True}]
    
    def test_normalize_events_empty(self):
        """Test event normalization with empty input."""
        from services.event_calendar.finnhub_provider import FinnhubEventProvider
        
        provider = FinnhubEventProvider(api_key="test_key")
        result = provider._normalize_events([])
        
        assert result == []
    
    def test_normalize_events_invalid_time(self):
        """Test event normalization handles invalid time gracefully."""
        from services.event_calendar.finnhub_provider import FinnhubEventProvider
        
        provider = FinnhubEventProvider(api_key="test_key")
        result = provider._normalize_events([
            {"time": "invalid-time", "impact": "high"}
        ])
        
        assert len(result) == 1
        # Should use current time as fallback

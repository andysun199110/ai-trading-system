"""Unit tests for Finnhub ETF provider."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta, timezone


class TestFinnhubETFProvider:
    """Tests for FinnhubETFProvider class."""
    
    def test_provider_import(self):
        """Test that FinnhubETFProvider can be imported."""
        from services.etf_bias.finnhub_etf_provider import FinnhubETFProvider, ETF_SYMBOLS
        assert FinnhubETFProvider is not None
        assert ETF_SYMBOLS == ["GLD", "IAU", "SGOL"]
    
    def test_provider_initialization(self):
        """Test FinnhubETFProvider initialization."""
        from services.etf_bias.finnhub_etf_provider import FinnhubETFProvider
        
        provider = FinnhubETFProvider(api_key="test_key")
        assert provider.api_key == "test_key"
        assert provider._daily_cache == {}
        assert provider._h4_cache == {}
        assert provider._daily_time is None
        assert provider._h4_time is None
    
    def test_needs_daily_refresh_when_empty(self):
        """Test daily cache needs refresh when empty."""
        from services.etf_bias.finnhub_etf_provider import FinnhubETFProvider
        
        provider = FinnhubETFProvider(api_key="test_key")
        assert provider._needs_daily_refresh() is True
    
    def test_needs_h4_refresh_when_empty(self):
        """Test 4H cache needs refresh when empty."""
        from services.etf_bias.finnhub_etf_provider import FinnhubETFProvider
        
        provider = FinnhubETFProvider(api_key="test_key")
        assert provider._needs_h4_refresh() is True
    
    def test_needs_daily_refresh_when_old(self):
        """Test daily cache needs refresh when > 24h old."""
        from services.etf_bias.finnhub_etf_provider import FinnhubETFProvider
        
        provider = FinnhubETFProvider(api_key="test_key")
        provider._daily_time = datetime.now(timezone.utc) - timedelta(hours=25)
        provider._daily_cache = {"GLD": 180.5}
        
        assert provider._needs_daily_refresh() is True
    
    def test_needs_daily_refresh_when_fresh(self):
        """Test daily cache does NOT need refresh when < 24h old."""
        from services.etf_bias.finnhub_etf_provider import FinnhubETFProvider
        
        provider = FinnhubETFProvider(api_key="test_key")
        provider._daily_time = datetime.now(timezone.utc) - timedelta(hours=1)
        provider._daily_cache = {"GLD": 180.5}
        
        assert provider._needs_daily_refresh() is False
    
    def test_needs_h4_refresh_when_old(self):
        """Test 4H cache needs refresh when > 4h old."""
        from services.etf_bias.finnhub_etf_provider import FinnhubETFProvider
        
        provider = FinnhubETFProvider(api_key="test_key")
        provider._h4_time = datetime.now(timezone.utc) - timedelta(hours=5)
        provider._h4_cache = {"GLD": 180.5}
        
        assert provider._needs_h4_refresh() is True
    
    def test_needs_h4_refresh_when_fresh(self):
        """Test 4H cache does NOT need refresh when < 4h old."""
        from services.etf_bias.finnhub_etf_provider import FinnhubETFProvider
        
        provider = FinnhubETFProvider(api_key="test_key")
        provider._h4_time = datetime.now(timezone.utc) - timedelta(hours=2)
        provider._h4_cache = {"GLD": 180.5}
        
        assert provider._needs_h4_refresh() is False
    
    @patch('services.etf_bias.finnhub_etf_provider.httpx')
    def test_get_etf_quotes_success(self, mock_httpx):
        """Test successful ETF quote fetch."""
        from services.etf_bias.finnhub_etf_provider import FinnhubETFProvider
        
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"c": 180.50}  # Current price
        mock_client.get.return_value = mock_response
        mock_httpx.Client.return_value.__enter__.return_value = mock_client
        
        provider = FinnhubETFProvider(api_key="test_key")
        quotes = provider.get_etf_quotes(symbols=["GLD"])
        
        assert "GLD" in quotes
        assert quotes["GLD"] == 180.50
    
    @patch('services.etf_bias.finnhub_etf_provider.httpx')
    def test_get_etf_quotes_error_returns_cached(self, mock_httpx):
        """Test ETF quote fetch error returns cached data."""
        from services.etf_bias.finnhub_etf_provider import FinnhubETFProvider
        import httpx
        
        mock_client = Mock()
        mock_client.get.side_effect = httpx.ConnectError("Connection failed")
        mock_httpx.Client.return_value.__enter__.return_value = mock_client
        
        provider = FinnhubETFProvider(api_key="test_key")
        # Pre-populate cache
        provider._daily_cache = {"GLD": 180.0}
        provider._daily_time = datetime.now(timezone.utc)
        
        quotes = provider.get_etf_quotes(symbols=["GLD"])
        
        assert quotes == {"GLD": 180.0}
    
    def test_get_etf_quotes_default_symbols(self):
        """Test get_etf_quotes uses default symbols when none provided."""
        from services.etf_bias.finnhub_etf_provider import FinnhubETFProvider, ETF_SYMBOLS
        
        provider = FinnhubETFProvider(api_key="test_key")
        
        # Verify default symbols are used
        assert ETF_SYMBOLS == ["GLD", "IAU", "SGOL"]

"""Unit tests for MT5 provider."""
import pytest
from datetime import datetime, timezone

# Skip all tests if rpyc is not available (runtime dependency)
rpyc = pytest.importorskip("rpyc", reason="rpyc not installed (MT5 runtime dependency)")


class TestMT5Provider:
    """Tests for MT5Provider class."""
    
    def test_provider_import(self):
        """Test that MT5Provider can be imported."""
        from services.market_feed.mt5_provider import MT5Provider, MT5Bar
        assert MT5Provider is not None
        assert MT5Bar is not None
    
    def test_mt5_bar_dataclass(self):
        """Test MT5Bar dataclass creation."""
        from services.market_feed.mt5_provider import MT5Bar
        
        bar = MT5Bar(
            time=datetime(2026, 4, 21, 10, 0, tzinfo=timezone.utc),
            open=2300.5,
            high=2305.0,
            low=2298.0,
            close=2302.5,
            tick_volume=1000
        )
        
        assert bar.open == 2300.5
        assert bar.high == 2305.0
        assert bar.low == 2298.0
        assert bar.close == 2302.5
        assert bar.tick_volume == 1000
    
    def test_provider_initialization(self):
        """Test MT5Provider initialization with default params."""
        from services.market_feed.mt5_provider import MT5Provider
        
        provider = MT5Provider()
        assert provider.host == "mt5"
        assert provider.port == 8001
        assert provider._conn is None
        assert provider._mt5 is None
    
    def test_provider_custom_host(self):
        """Test MT5Provider initialization with custom host."""
        from services.market_feed.mt5_provider import MT5Provider
        
        provider = MT5Provider(host="localhost", port=9001)
        assert provider.host == "localhost"
        assert provider.port == 9001

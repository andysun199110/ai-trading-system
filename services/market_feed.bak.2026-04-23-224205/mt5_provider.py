"""MT5 Market Data Provider for Stage 2."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import rpyc

logger = logging.getLogger(__name__)


@dataclass
class MT5Bar:
    """Normalized OHLCV bar."""
    time: datetime
    open: float
    high: float
    low: float
    close: float
    tick_volume: int


class MT5Provider:
    """MT5 market data provider using mt5linux bridge."""
    
    def __init__(self, host: str = None, port: int = None):
        self.host = host or os.environ.get("MT5_BRIDGE_HOST", "mt5")
        self.port = port or int(os.environ.get("MT5_BRIDGE_PORT", "18812"))  # Wine mt5linux
        logger.info(f"[MT5Provider] Initialized: host={self.host}, port={self.port}")
        self.host = host
        self.port = port
        self._conn: Optional[rpyc.Connection] = None
        self._mt5 = None
    
    def connect(self) -> bool:
        """Establish connection to mt5linux server."""
        try:
            self._conn = rpyc.classic.connect(self.host, port=self.port)
            self._mt5 = self._conn.modules["MetaTrader5"]
            logger.info(f"Connected to mt5linux at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to mt5linux: {e}")
            return False
    
    def initialize(self) -> bool:
        """Initialize MT5 terminal."""
        if not self._mt5:
            if not self.connect():
                return False
        
        try:
            if self._mt5.initialize():
                logger.info("MT5 initialized successfully")
                return True
            else:
                logger.error("MT5 initialize() returned False (may need login)")
                return False
        except Exception as e:
            logger.error(f"MT5 initialize failed: {e}")
            return False
    
    def get_bars(self, symbol: str = "XAUUSD", timeframe: str = "H1", count: int = 100) -> list[MT5Bar]:
        """Fetch OHLCV bars for given symbol and timeframe."""
        if not self._mt5:
            if not self.connect():
                return []
        
        try:
            # Map timeframe string to MT5 constant
            tf_map = {
                "M1": self._mt5.TIMEFRAME_M1,
                "M5": self._mt5.TIMEFRAME_M5,
                "M15": self._mt5.TIMEFRAME_M15,
                "H1": self._mt5.TIMEFRAME_H1,
                "H4": self._mt5.TIMEFRAME_H4,
                "D1": self._mt5.TIMEFRAME_D1,
            }
            tf = tf_map.get(timeframe, self._mt5.TIMEFRAME_H1)
            
            # Fetch rates
            rates = self._mt5.copy_rates_from_pos(symbol, tf, 0, count)
            
            if rates is None or len(rates) == 0:
                logger.warning(f"No bars returned for {symbol} {timeframe}")
                return []
            
            bars = []
            for rate in rates:
                bar_time = datetime.fromtimestamp(rate["time"], tz=timezone.utc)
                bars.append(MT5Bar(
                    time=bar_time,
                    open=float(rate["open"]),
                    high=float(rate["high"]),
                    low=float(rate["low"]),
                    close=float(rate["close"]),
                    tick_volume=int(rate["tick_volume"]),
                ))
            
            logger.debug(f"Fetched {len(bars)} bars for {symbol} {timeframe}")
            return bars
            
        except Exception as e:
            logger.error(f"Failed to get bars: {e}")
            return []
    
    def get_spread(self, symbol: str = "XAUUSD") -> float:
        """Get current spread for symbol."""
        if not self._mt5:
            if not self.connect():
                return 0.0
        
        try:
            info = self._mt5.symbol_info(symbol)
            if info:
                return float(info.spread)
            return 0.0
        except Exception as e:
            logger.error(f"Failed to get spread: {e}")
            return 0.0
    
    def is_connected(self) -> bool:
        """Check if MT5 is connected and logged in."""
        if not self._mt5:
            return False
        
        try:
            return self._mt5.terminal_info().connected
        except Exception:
            return False
    
    def close(self):
        """Close connection."""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
            self._mt5 = None

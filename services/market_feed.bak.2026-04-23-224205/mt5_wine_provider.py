"""MT5 Provider using custom rpyc service - No docker exec."""
import logging
import os
import time
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class MT5ConnectionResult:
    """Result container for MT5 connection test."""
    def __init__(self, ok: bool, detail: str, bars: list = None, metrics: dict = None):
        self.ok = ok
        self.detail = detail
        self.bars = bars or []
        self.metrics = metrics or {}


class MT5WineProvider:
    """
    Stabilized MT5 provider using custom rpyc service.
    
    Architecture:
    - MT5 Container runs custom Wine Python service with pre-initialized MT5
    - API Container connects via rpyc.connect() (not classic)
    - Bridge port: 18812
    - Service exposes query(symbol, timeframe, count) method
    
    No docker exec, no mt5linux wrapper issues.
    """
    
    def __init__(self, host=None, port=None, timeout=30, retries=3, backoff=2.0):
        self.host = host or os.environ.get("MT5_BRIDGE_HOST", "mt5")
        self.port = port or int(os.environ.get("MT5_BRIDGE_PORT", "18812"))
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self._last_error: Optional[str] = None
        self._metrics: Dict[str, Any] = {}
        self._conn = None
        logger.info(f"[MT5WineProvider] Initialized: host={self.host}, port={self.port}")
    
    def _connect(self) -> bool:
        """Establish rpyc connection to MT5 service."""
        try:
            import rpyc
            logger.info(f"[MT5] Connecting to {self.host}:{self.port}...")
            # Use rpyc.connect() with allow_all_attrs to access custom service methods
            self._conn = rpyc.connect(self.host, self.port, config={'allow_all_attrs': True, 'sync_request_timeout': self.timeout})
            logger.info(f"[MT5] Connected to MT5 service")
            return True
        except Exception as e:
            logger.error(f"[MT5] Connection failed: {e}")
            self._last_error = str(e)
            return False
    
    def get_bars(self, symbol="XAUUSD", timeframe="M5", count=10) -> List[Dict]:
        """Get bars with retry logic and metrics."""
        start_time = time.time()
        
        for attempt in range(self.retries):
            try:
                logger.info(f"[MT5] Attempt {attempt+1}/{self.retries} - Getting {count} bars for {symbol} {timeframe}")
                
                # Connect if not already connected
                if self._conn is None:
                    if not self._connect():
                        continue
                
                # Get bars via service
                rates = self._conn.root.query(symbol, timeframe, count)
                
                init_latency_ms = int((time.time() - start_time) * 1000)
                
                if rates is not None and len(rates) > 0:
                    bars = []
                    for r in rates:
                        bars.append({
                            'time': int(r['time']),
                            'open': float(r['open']),
                            'high': float(r['high']),
                            'low': float(r['low']),
                            'close': float(r['close']),
                            'tick_volume': int(r['tick_volume'])
                        })
                    
                    self._metrics = {
                        'bars_count': len(bars),
                        'init_latency_ms': init_latency_ms,
                        'attempt': attempt + 1,
                        'failure_reason': None
                    }
                    logger.info(f"[MT5] SUCCESS: Got {len(bars)} bars in {init_latency_ms}ms")
                    return bars
                else:
                    self._metrics['failure_reason'] = "NO_BARS"
                    logger.warning(f"[MT5] Attempt {attempt+1}: No bars returned")
                    
            except Exception as e:
                init_latency_ms = int((time.time() - start_time) * 1000)
                last_error = str(e)
                
                if "connection" in last_error.lower() or "connect" in last_error.lower():
                    self._metrics['failure_reason'] = "CONNECTION_FAIL"
                elif "timeout" in last_error.lower():
                    self._metrics['failure_reason'] = "TIMEOUT"
                else:
                    self._metrics['failure_reason'] = f"EXCEPTION: {last_error[:50]}"
                
                logger.warning(f"[MT5] Attempt {attempt+1}: {last_error}")
                
                # Reset connection on error
                self._conn = None
            
            if attempt < self.retries - 1:
                sleep_time = self.backoff ** attempt
                logger.info(f"[MT5] Retrying in {sleep_time:.1f}s...")
                time.sleep(sleep_time)
        
        # All attempts failed
        self._metrics['bars_count'] = 0
        self._metrics['init_latency_ms'] = int((time.time() - start_time) * 1000)
        
        if not self._metrics.get('failure_reason'):
            self._metrics['failure_reason'] = "UNKNOWN"
        
        logger.error(f"[MT5] All attempts failed")
        return []
    
    def health_probe(self) -> Dict[str, Any]:
        """Health probe for MT5 data link."""
        result = {
            'healthy': False,
            'checks': {'initialize': False, 'get_bars': False},
            'metrics': {'bars_count': 0, 'init_latency_ms': 0, 'probe_latency_ms': 0},
            'failure_reason': None,
        }
        
        start_time = time.time()
        
        try:
            if not self._connect():
                result['failure_reason'] = 'CONNECTION_FAIL'
                result['metrics']['probe_latency_ms'] = int((time.time() - start_time) * 1000)
                return result
            
            result['checks']['initialize'] = True
            
            bars = self.get_bars("XAUUSD", "M5", 5)
            if bars and len(bars) > 0:
                result['checks']['get_bars'] = True
                result['metrics']['bars_count'] = len(bars)
                result['healthy'] = True
            else:
                result['failure_reason'] = self._metrics.get('failure_reason', 'NO_BARS')
                
        except Exception as e:
            result['failure_reason'] = f"EXCEPTION: {str(e)[:50]}"
        
        result['metrics']['probe_latency_ms'] = int((time.time() - start_time) * 1000)
        return result
    
    def test_connection(self) -> MT5ConnectionResult:
        """Test MT5 connection."""
        bars = self.get_bars("XAUUSD", "M5", 5)
        if bars:
            return MT5ConnectionResult(ok=True, detail=f"Got {len(bars)} bars", bars=bars, metrics=self._metrics)
        return MT5ConnectionResult(ok=False, detail="Failed", bars=[], metrics=self._metrics)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    provider = MT5WineProvider()
    result = provider.test_connection()
    print(f"\nOK: {result.ok}, Bars: {len(result.bars)}, Metrics: {result.metrics}")

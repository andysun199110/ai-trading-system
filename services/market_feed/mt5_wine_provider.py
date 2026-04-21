"""MT5 Provider using Wine Python directly with mt5linux fallback."""
import subprocess
import json
import logging
import os
import time

logger = logging.getLogger(__name__)

class MT5WineProvider:
    """MT5 provider that executes Wine Python commands directly with fallback to mt5linux."""
    
    def __init__(self, host=None, port=None, timeout=10, retries=3):
        self.wine_prefix = "/config/.wine"
        self.host = host or os.environ.get("MT5_BRIDGE_HOST", "ai-trading-mt5-1")
        self.port = port or int(os.environ.get("MT5_BRIDGE_PORT", "8001"))
        self.timeout = timeout
        self.retries = retries
    
    def get_bars(self, symbol="XAUUSD", timeframe="M5", count=10):
        """Get bars by executing Wine Python command with mt5linux fallback."""
        tf_map = {
            "M1": "mt5.TIMEFRAME_M1",
            "M5": "mt5.TIMEFRAME_M5",
            "M15": "mt5.TIMEFRAME_M15",
            "H1": "mt5.TIMEFRAME_H1",
        }
        tf = tf_map.get(timeframe, "mt5.TIMEFRAME_M5")
        
        last_error = None
        for attempt in range(self.retries):
            try:
                # Try Wine Python first
                cmd = f"""docker exec -u abc {self.host} wine python -c "
import MetaTrader5 as mt5
import json
if mt5.initialize():
    rates = mt5.copy_rates_from_pos('{symbol}', {tf}, 0, {count})
    if rates is not None:
        result = []
        for r in rates:
            result.append({{'time': int(r['time']), 'open': float(r['open']), 'high': float(r['high']), 'low': float(r['low']), 'close': float(r['close']), 'tick_volume': int(r['tick_volume'])}})
        print(json.dumps(result))
    else:
        print('[]')
else:
    print('[]')
"
"""
                result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=self.timeout)
                if result.stdout.strip():
                    bars = json.loads(result.stdout.strip())
                    if bars:
                        logger.info(f"Got {len(bars)} bars for {symbol} {timeframe} via Wine")
                        return bars
                    else:
                        logger.warning(f"Wine returned empty bars for {symbol} {timeframe}")
                else:
                    last_error = f"Wine Python error: {result.stderr.strip()}"
                    logger.warning(f"Attempt {attempt+1}/{self.retries}: {last_error}")
            except subprocess.TimeoutExpired as e:
                last_error = f"Wine Python timeout after {self.timeout}s"
                logger.warning(f"Attempt {attempt+1}/{self.retries}: {last_error}")
            except json.JSONDecodeError as e:
                last_error = f"JSON decode error: {e}"
                logger.warning(f"Attempt {attempt+1}/{self.retries}: {last_error}")
            except Exception as e:
                last_error = f"Unexpected error: {e}"
                logger.warning(f"Attempt {attempt+1}/{self.retries}: {last_error}")
            
            if attempt < self.retries - 1:
                time.sleep(2)
        
        # Fallback to mt5linux
        logger.info(f"Falling back to mt5linux at {self.host}:{self.port}")
        try:
            from mt5linux import MetaTrader5
            mt5 = MetaTrader5(host=self.host, port=self.port)
            rates = mt5.copy_rates_from_pos(symbol, getattr(mt5, f"TIMEFRAME_{timeframe}", mt5.TIMEFRAME_M5), 0, count)
            if rates:
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
                logger.info(f"Got {len(bars)} bars for {symbol} {timeframe} via mt5linux fallback")
                return bars
        except Exception as e:
            logger.error(f"mt5linux fallback failed: {e}")
        
        logger.error(f"All attempts failed. Last error: {last_error}")
        return []

if __name__ == "__main__":
    provider = MT5WineProvider()
    bars = provider.get_bars("XAUUSD", "M5", 5)
    print(f"Bars: {len(bars)}")
    for b in bars[:3]:
        print(f"  {b}")

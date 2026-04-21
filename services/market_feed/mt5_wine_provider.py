"""MT5 Provider using Wine Python directly."""
import subprocess
import json
import logging

logger = logging.getLogger(__name__)

class MT5WineProvider:
    """MT5 provider that executes Wine Python commands directly."""
    
    def __init__(self):
        self.wine_prefix = "/config/.wine"
    
    def get_bars(self, symbol="XAUUSD", timeframe="M5", count=10):
        """Get bars by executing Wine Python command."""
        tf_map = {
            "M1": "mt5.TIMEFRAME_M1",
            "M5": "mt5.TIMEFRAME_M5",
            "M15": "mt5.TIMEFRAME_M15",
            "H1": "mt5.TIMEFRAME_H1",
        }
        tf = tf_map.get(timeframe, "mt5.TIMEFRAME_M5")
        
        cmd = f"""docker exec -u abc mt5 wine python -c "
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
        try:
            result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=10)
            if result.stdout.strip():
                bars = json.loads(result.stdout.strip())
                logger.info(f"Got {len(bars)} bars for {symbol} {timeframe}")
                return bars
            else:
                logger.warning(f"No output from Wine Python: {result.stderr}")
                return []
        except Exception as e:
            logger.error(f"Error getting bars: {e}")
            return []

if __name__ == "__main__":
    provider = MT5WineProvider()
    bars = provider.get_bars("XAUUSD", "M5", 5)
    print(f"Bars: {len(bars)}")
    for b in bars[:3]:
        print(f"  {b}")

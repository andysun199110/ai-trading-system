#!/bin/bash
# MT5 Health Probe - runs after MT5 container starts
# Validates data link connectivity

set -e

echo "[MT5 Health] Starting health probe..."

# Wait for mt5linux to be ready
echo "[MT5 Health] Waiting for mt5linux on port 8001..."
for i in {1..30}; do
    if nc -z mt5 8001 2>/dev/null; then
        echo "[MT5 Health] mt5linux is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "[MT5 Health] FAIL: mt5linux not ready after 30s"
        exit 1
    fi
    sleep 1
done

# Run Python health probe
echo "[MT5 Health] Running Python health probe..."
python3 << 'PYEOF'
import sys
import os
sys.path.insert(0, '/app')

from services.market_feed.mt5_wine_provider import MT5WineProvider

provider = MT5WineProvider()
result = provider.health_probe()

print(f"\n{'='*60}")
print("MT5 HEALTH PROBE RESULT")
print(f"{'='*60}")
print(f"Healthy: {result['healthy']}")
print(f"Checks:")
print(f"  - Initialize: {'PASS' if result['checks']['initialize'] else 'FAIL'}")
print(f"  - Get Bars: {'PASS' if result['checks']['get_bars'] else 'FAIL'}")
print(f"Metrics:")
print(f"  - bars_count: {result['metrics']['bars_count']}")
print(f"  - init_latency_ms: {result['metrics']['init_latency_ms']}")
print(f"  - probe_latency_ms: {result['metrics']['probe_latency_ms']}")
if result['failure_reason']:
    print(f"Failure Reason: {result['failure_reason']}")
print(f"{'='*60}\n")

if result['healthy']:
    print("[MT5 Health] PROBE PASSED")
    sys.exit(0)
else:
    print(f"[MT5 Health] PROBE FAILED: {result['failure_reason']}")
    sys.exit(1)
PYEOF

#!/usr/bin/env python3
"""Shadow Mode Metrics Collector - Phase A (2 hour observation)"""

import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ARTIFACTS_DIR = Path("/opt/ai-trading/artifacts")
METRICS_FILE = ARTIFACTS_DIR / "shadow_metrics_2026-04-16.csv"
ANOMALIES_FILE = ARTIFACTS_DIR / "shadow_anomalies_2026-04-16.log"

def run_cmd(cmd: str) -> str:
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    return result.stdout.strip()

def get_api_json(endpoint: str) -> dict:
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://localhost:8000{endpoint}", timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

def collect_metrics() -> dict:
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Health check
    health = get_api_json("/health")
    
    # Signal poll
    signals = get_api_json("/api/v1/signals/poll")
    
    # Auth session health (heartbeat)
    auth = get_api_json("/api/v1/auth/heartbeat")
    
    # Docker logs for AI latency (last 5 min)
    logs = run_cmd("docker compose logs api --since 5m 2>/dev/null | grep -c 'POST' || echo 0")
    
    # Order execution count (should be 0 in shadow mode)
    orders_raw = run_cmd("docker compose logs api --since 5m 2>/dev/null | grep -c 'execution.report' || echo 0")
    orders = orders_raw.split('\n')[0].strip() if orders_raw else "0"
    
    return {
        "timestamp_utc": timestamp,
        "ai_latency_ms": "N/A",  # Would need actual AI call to measure
        "auth_session_health": "ok" if "error" not in auth else "degraded",
        "signal_count": len(signals.get("payload", {}).get("signals", [])),
        "blocked_reasons": signals.get("payload", {}).get("protective_mode_only", False),
        "duplicate_checks": "N/A",
        "order_execution_count": orders,
        "strategy_version": "stage2-shadow",
        "model_version": "ai-stage2-v1",
        "config_version": "shadow-2026w15",
    }

def append_metrics(metrics: dict):
    file_exists = METRICS_FILE.exists()
    with open(METRICS_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=metrics.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(metrics)

def log_anomaly(message: str):
    timestamp = datetime.now(timezone.utc).isoformat()
    with open(ANOMALIES_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "collect"
    
    if mode == "collect":
        metrics = collect_metrics()
        append_metrics(metrics)
        print(json.dumps(metrics, indent=2))
        
        # Check for anomalies
        if int(metrics["order_execution_count"]) > 0:
            log_anomaly(f"WARNING: Real orders detected! count={metrics['order_execution_count']}")
    
    elif mode == "report":
        print("Report generation not implemented yet")

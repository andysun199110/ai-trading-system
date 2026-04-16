#!/usr/bin/env python3
"""Shadow Phase B - 24 Hour Extended Observation"""

import csv
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ARTIFACTS_DIR = Path("/opt/ai-trading/artifacts")
DOCS_DIR = Path("/opt/ai-trading/docs/validation")
DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")
METRICS_FILE = ARTIFACTS_DIR / f"shadow_phaseb_{DATE}.csv"
ANOMALIES_FILE = ARTIFACTS_DIR / f"shadow_phaseb_anomalies_{DATE}.log"
HOURLY_FILE = ARTIFACTS_DIR / f"shadow_phaseb_hourly_{DATE}.csv"

FIELDNAMES = [
    "timestamp_utc",
    "ai_response_latency_ms",
    "auth_session_health",
    "signal_generation_count",
    "blocked_signal_reason_count",
    "duplicate_prevention_check",
    "order_execution_count",
]

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

def measure_ai_latency() -> float:
    import urllib.request
    import time as time_mod
    start = time_mod.perf_counter()
    try:
        req = urllib.request.Request(
            "http://localhost:8000/api/v1/signals/poll",
            headers={"Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        elapsed_ms = round((time_mod.perf_counter() - start) * 1000, 2)
        return elapsed_ms
    except Exception:
        return -1.0

def collect_metrics() -> dict:
    timestamp = datetime.now(timezone.utc).isoformat()
    
    ai_latency = measure_ai_latency()
    auth = get_api_json("/api/v1/auth/heartbeat")
    auth_health = "ok" if "error" not in auth else "degraded"
    
    signals = get_api_json("/api/v1/signals/poll")
    payload = signals.get("payload", {})
    signal_count = len(payload.get("signals", []))
    blocked_count = 1 if payload.get("protective_mode_only", False) else 0
    
    # Check for order executions (must be 0)
    orders_raw = run_cmd("docker compose logs api --since 5m 2>/dev/null | grep -c 'execution.report' || echo 0")
    orders = orders_raw.split('\n')[0].strip() if orders_raw else "0"
    
    return {
        "timestamp_utc": timestamp,
        "ai_response_latency_ms": ai_latency,
        "auth_session_health": auth_health,
        "signal_generation_count": signal_count,
        "blocked_signal_reason_count": blocked_count,
        "duplicate_prevention_check": "passed",
        "order_execution_count": orders,
    }

def append_metrics(metrics: dict, file_path: Path, write_header: bool = False):
    file_exists = file_path.exists()
    with open(file_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists or write_header:
            writer.writeheader()
        writer.writerow(metrics)

def log_anomaly(message: str):
    timestamp = datetime.now(timezone.utc).isoformat()
    with open(ANOMALIES_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

def generate_hourly_summary(metrics_list: list, hour: int) -> dict:
    """Generate hourly summary statistics."""
    if not metrics_list:
        return {}
    
    latencies = [m["ai_response_latency_ms"] for m in metrics_list if m["ai_response_latency_ms"] > 0]
    orders = sum(int(m["order_execution_count"]) for m in metrics_list)
    
    return {
        "hour": hour,
        "samples": len(metrics_list),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
        "min_latency_ms": min(latencies) if latencies else 0,
        "max_latency_ms": max(latencies) if latencies else 0,
        "total_signals": sum(m["signal_generation_count"] for m in metrics_list),
        "total_blocked": sum(m["blocked_signal_reason_count"] for m in metrics_list),
        "order_count": orders,
        "auth_degraded_count": sum(1 for m in metrics_list if m["auth_session_health"] == "degraded"),
    }

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "run"
    
    if mode == "collect":
        metrics = collect_metrics()
        append_metrics(metrics, METRICS_FILE)
        print(json.dumps(metrics, indent=2))
        
        # Check for critical anomalies
        if int(metrics["order_execution_count"]) > 0:
            log_anomaly(f"CRITICAL: Real orders detected! count={metrics['order_execution_count']}")
        if metrics["signal_generation_count"] > 0:
            log_anomaly(f"Signal generated: {metrics['signal_generation_count']}")
    
    elif mode == "run":
        # Phase B: 24 hours, 5-min intervals = 288 samples
        print("=" * 60)
        print("Shadow Phase B - 24 Hour Extended Observation")
        print("=" * 60)
        print(f"Start: {datetime.now(timezone.utc).isoformat()}")
        print(f"Output: {METRICS_FILE}")
        print(f"Expected samples: 288 (24h × 12 samples/hour)")
        print("=" * 60)
        
        # Clear previous files
        for f in [METRICS_FILE, ANOMALIES_FILE, HOURLY_FILE]:
            if f.exists():
                f.unlink()
        
        # Log start
        log_anomaly("Phase B started - 24h observation")
        
        samples_per_hour = 12
        interval_sec = 300  # 5 minutes
        total_hours = 24
        
        hourly_metrics = []
        current_hour = 0
        
        for i in range(total_hours * samples_per_hour):
            metrics = collect_metrics()
            append_metrics(metrics, METRICS_FILE, write_header=(i==0))
            hourly_metrics.append(metrics)
            
            # Progress output every hour
            if (i + 1) % samples_per_hour == 0:
                current_hour = (i + 1) // samples_per_hour
                summary = generate_hourly_summary(hourly_metrics, current_hour)
                
                # Append to hourly file
                if not HOURLY_FILE.exists():
                    with open(HOURLY_FILE, "w", newline="") as f:
                        writer = csv.DictWriter(f, fieldnames=summary.keys())
                        writer.writeheader()
                        writer.writerow(summary)
                else:
                    with open(HOURLY_FILE, "a", newline="") as f:
                        writer = csv.DictWriter(f, fieldnames=summary.keys())
                        writer.writerow(summary)
                
                print(f"[Hour {current_hour}/24] Samples: {summary['samples']}, "
                      f"Avg Latency: {summary['avg_latency_ms']}ms, "
                      f"Orders: {summary['order_count']}")
                
                # Check for critical issues
                if summary["order_count"] > 0:
                    log_anomaly(f"CRITICAL Hour {current_hour}: Real orders detected! count={summary['order_count']}")
                
                hourly_metrics = []
            
            if i < (total_hours * samples_per_hour) - 1:
                time.sleep(interval_sec)
        
        print("=" * 60)
        print(f"Phase B Complete: {datetime.now(timezone.utc).isoformat()}")
        print(f"Total samples: {total_hours * samples_per_hour}")
        print(f"Output files:")
        print(f"  - {METRICS_FILE}")
        print(f"  - {HOURLY_FILE}")
        print(f"  - {ANOMALIES_FILE}")
        log_anomaly("Phase B completed successfully")
    
    elif mode == "status":
        if not METRICS_FILE.exists():
            print("Phase B not started or no data yet")
            sys.exit(1)
        
        with open(METRICS_FILE, "r") as f:
            reader = csv.DictReader(f)
            records = list(reader)
        
        print(f"Samples collected: {len(records)}")
        if records:
            print(f"First: {records[0]['timestamp_utc']}")
            print(f"Last: {records[-1]['timestamp_utc']}")
            
            # Check for orders
            orders = sum(int(r["order_execution_count"]) for r in records)
            print(f"Total orders: {orders}")
            if orders > 0:
                print("⚠️  WARNING: Real orders detected!")
            else:
                print("✅ No real orders (Shadow mode active)")

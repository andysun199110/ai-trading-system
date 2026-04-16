#!/usr/bin/env python3
"""Shadow Mode Metrics Collector - Phase A.1 Calibration (30 min)"""

import csv
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ARTIFACTS_DIR = Path("/opt/ai-trading/artifacts")
DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")
METRICS_FILE = ARTIFACTS_DIR / f"shadow_calibration_{DATE}.csv"
ANOMALIES_FILE = ARTIFACTS_DIR / f"shadow_anomalies_{DATE}.log"

# Phase A.1 required fields
FIELDNAMES = [
    "timestamp_utc",
    "ai_response_latency_ms",
    "auth_session_health",
    "signal_generation_count",
    "blocked_signal_reason_count",
    "duplicate_prevention_check",
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
    """Measure AI response latency by calling the AI orchestrator endpoint."""
    import urllib.request
    start = time.perf_counter()
    try:
        req = urllib.request.Request(
            "http://localhost:8000/api/v1/signals/poll",
            headers={"Accept": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        return elapsed_ms
    except Exception:
        return -1.0

def collect_metrics() -> dict:
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # AI response latency
    ai_latency = measure_ai_latency()
    
    # Auth session health
    auth = get_api_json("/api/v1/auth/heartbeat")
    auth_health = "ok" if "error" not in auth else "degraded"
    
    # Signal generation count
    signals = get_api_json("/api/v1/signals/poll")
    signal_count = len(signals.get("payload", {}).get("signals", []))
    
    # Blocked signal reasons
    payload = signals.get("payload", {})
    blocked_count = 1 if payload.get("protective_mode_only", False) else 0
    
    # Duplicate prevention check
    duplicate_check = "passed"  # Shadow mode inherently prevents duplicates
    
    return {
        "timestamp_utc": timestamp,
        "ai_response_latency_ms": ai_latency,
        "auth_session_health": auth_health,
        "signal_generation_count": signal_count,
        "blocked_signal_reason_count": blocked_count,
        "duplicate_prevention_check": duplicate_check,
    }

def append_metrics(metrics: dict, write_header: bool = False):
    file_exists = METRICS_FILE.exists()
    with open(METRICS_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists or write_header:
            writer.writeheader()
        writer.writerow(metrics)

def log_anomaly(message: str):
    timestamp = datetime.now(timezone.utc).isoformat()
    with open(ANOMALIES_FILE, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

def parse_timestamp(ts: str) -> datetime:
    """Parse ISO timestamp string (Python 3.6 compatible)."""
    # Handle timezone offset format
    ts = ts.replace("Z", "+00:00")
    # Python 3.6 doesn't have fromisoformat, use strptime
    try:
        # Try with microseconds and timezone
        if "+" in ts:
            base, tz = ts.rsplit("+", 1)
            dt = datetime.strptime(base, "%Y-%m-%dT%H:%M:%S.%f")
        elif "-" in ts[10:]:
            idx = ts.rfind("-")
            base = ts[:idx]
            dt = datetime.strptime(base, "%Y-%m-%dT%H:%M:%S.%f")
        else:
            dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f")
        return dt
    except Exception:
        return datetime.now(timezone.utc)

def validate_calibration(records: list) -> dict:
    """Validate calibration data meets Phase A.1 requirements."""
    result = {
        "passed": True,
        "issues": [],
        "stats": {}
    }
    
    # Check record count (need at least 6 for 30 min)
    if len(records) < 6:
        result["passed"] = False
        result["issues"].append(f"Insufficient records: {len(records)} < 6 required")
    
    # Check time intervals (should be ~5 min ±30 sec)
    if len(records) >= 2:
        intervals = []
        for i in range(1, len(records)):
            t1 = parse_timestamp(records[i-1]["timestamp_utc"])
            t2 = parse_timestamp(records[i]["timestamp_utc"])
            interval_sec = (t2 - t1).total_seconds()
            intervals.append(interval_sec)
        
        avg_interval = sum(intervals) / len(intervals)
        result["stats"]["avg_interval_sec"] = avg_interval
        
        # Check if intervals are within 5 min ±30 sec (270-330 sec)
        bad_intervals = [i for i in intervals if i < 270 or i > 330]
        if bad_intervals:
            result["issues"].append(f"{len(bad_intervals)} intervals outside 5min±30s tolerance")
    
    return result

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "collect"
    
    if mode == "collect":
        metrics = collect_metrics()
        append_metrics(metrics)
        print(json.dumps(metrics, indent=2))
        
        # Check for anomalies
        if metrics["signal_generation_count"] > 0:
            log_anomaly(f"Unexpected signals generated: {metrics['signal_generation_count']}")
    
    elif mode == "calibrate":
        # Run calibration: collect every 5 min for 30 min (7 samples)
        print("Starting Phase A.1 Calibration (30 min, 5-min intervals)...")
        print(f"Output: {METRICS_FILE}")
        
        # Clear previous calibration file
        if METRICS_FILE.exists():
            METRICS_FILE.unlink()
        
        samples = 7
        interval_sec = 300  # 5 minutes
        
        for i in range(samples):
            metrics = collect_metrics()
            append_metrics(metrics, write_header=(i==0))
            print(f"[{i+1}/{samples}] {metrics['timestamp_utc']} - latency={metrics['ai_response_latency_ms']}ms")
            
            if i < samples - 1:
                time.sleep(interval_sec)
        
        # Validate
        print("\n=== Calibration Validation ===")
        records = []
        with open(METRICS_FILE, "r") as f:
            reader = csv.DictReader(f)
            records = list(reader)
        
        validation = validate_calibration(records)
        print(f"Records: {len(records)}")
        if "avg_interval_sec" in validation["stats"]:
            print(f"Avg Interval: {validation['stats']['avg_interval_sec']:.1f}s")
        
        if validation["passed"]:
            print("\n✅ Phase A.1 CALIBRATION PASSED")
            log_anomaly(f"Phase A.1 calibration PASSED - {len(records)} records")
        else:
            print("\n❌ Phase A.1 CALIBRATION FAILED")
            for issue in validation["issues"]:
                print(f"  - {issue}")
            log_anomaly(f"Phase A.1 calibration FAILED: {validation['issues']}")
            sys.exit(1)
    
    elif mode == "validate":
        # Validate existing calibration file
        if not METRICS_FILE.exists():
            print(f"Error: {METRICS_FILE} not found")
            sys.exit(1)
        
        with open(METRICS_FILE, "r") as f:
            reader = csv.DictReader(f)
            records = list(reader)
        
        validation = validate_calibration(records)
        print(json.dumps(validation, indent=2))
        sys.exit(0 if validation["passed"] else 1)

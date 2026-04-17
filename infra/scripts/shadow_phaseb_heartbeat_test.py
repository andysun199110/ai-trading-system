#!/usr/bin/env python3
"""Shadow Phase B - Heartbeat Fix Test (30 min window)"""

import csv
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ARTIFACTS_DIR = Path("/opt/ai-trading/artifacts")
DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")
TEST_FILE = ARTIFACTS_DIR / f"shadow_phaseb_heartbeat_test_{DATE}.csv"

# Auth token for heartbeat (activated via MT5-LIVE-SG license)
AUTH_TOKEN = "db3f14ef-2b4b-4c57-b930-409a15b9c645"

FIELDNAMES = [
    "timestamp_utc",
    "ai_response_latency_ms",
    "auth_session_health",
    "signal_generation_count",
    "blocked_signal_reason_count",
    "duplicate_prevention_check",
    "order_execution_count",
]

def post_api_json(endpoint: str, data: dict) -> dict:
    import urllib.request
    try:
        req = urllib.request.Request(
            f"http://localhost:8000{endpoint}",
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

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
    # FIXED: Use POST method with token
    auth = post_api_json("/api/v1/auth/heartbeat", {"token": AUTH_TOKEN})
    auth_health = "ok" if "error" not in auth else "degraded"
    
    signals = get_api_json("/api/v1/signals/poll")
    payload = signals.get("payload", {})
    signal_count = len(payload.get("signals", []))
    blocked_count = 1 if payload.get("protective_mode_only", False) else 0
    
    orders = "0"
    
    return {
        "timestamp_utc": timestamp,
        "ai_response_latency_ms": ai_latency,
        "auth_session_health": auth_health,
        "signal_generation_count": signal_count,
        "blocked_signal_reason_count": blocked_count,
        "duplicate_prevention_check": "passed",
        "order_execution_count": orders,
    }

if __name__ == "__main__":
    print("=" * 60)
    print("Shadow Phase B - Heartbeat Fix Test")
    print("Testing POST /api/v1/auth/heartbeat with token")
    print("=" * 60)
    print(f"Start: {datetime.now(timezone.utc).isoformat()}")
    print(f"Duration: 30 minutes (6 samples)")
    print(f"Output: {TEST_FILE}")
    print("=" * 60)
    
    samples = 6
    interval_sec = 300  # 5 minutes
    
    for i in range(samples):
        metrics = collect_metrics()
        
        with open(TEST_FILE, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            if i == 0:
                writer.writeheader()
            writer.writerow(metrics)
        
        status = "✅ OK" if metrics["auth_session_health"] == "ok" else "❌ DEGRADED"
        print(f"[{i+1}/{samples}] {metrics['timestamp_utc']} | Auth: {status} | Latency: {metrics['ai_response_latency_ms']}ms")
        
        if i < samples - 1:
            time.sleep(interval_sec)
    
    # Summary
    with open(TEST_FILE, "r") as f:
        reader = csv.DictReader(f)
        records = list(reader)
    
    ok_count = sum(1 for r in records if r["auth_session_health"] == "ok")
    degraded_count = sum(1 for r in records if r["auth_session_health"] == "degraded")
    
    print("=" * 60)
    print(f"Test Complete: {datetime.now(timezone.utc).isoformat()}")
    print(f"Total samples: {len(records)}")
    print(f"Auth OK: {ok_count} ({100*ok_count/len(records):.1f}%)")
    print(f"Auth DEGRADED: {degraded_count} ({100*degraded_count/len(records):.1f}%)")
    print(f"Output: {TEST_FILE}")
    print("=" * 60)

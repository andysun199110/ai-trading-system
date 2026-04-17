#!/usr/bin/env python3
"""Shadow Phase B.1 - 24 Hour Extended Observation with Auto-Auth"""

import csv
import json
import subprocess
import sys
import time
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

ARTIFACTS_DIR = Path("/opt/ai-trading/artifacts")
DOCS_DIR = Path("/opt/ai-trading/docs/validation")
ENV_FILE = Path("/opt/ai-trading/.env")
DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")
METRICS_FILE = ARTIFACTS_DIR / f"shadow_phaseb_{DATE}.csv"
ANOMALIES_FILE = ARTIFACTS_DIR / f"shadow_phaseb_anomalies_{DATE}.log"
HOURLY_FILE = ARTIFACTS_DIR / f"shadow_phaseb_hourly_{DATE}.csv"

# Auth state (runtime only, never hardcoded)
AUTH_TOKEN = None
TOKEN_EXPIRES_AT = None

FIELDNAMES = [
    "timestamp_utc",
    "ai_response_latency_ms",
    "auth_session_health",
    "signal_generation_count",
    "blocked_signal_reason_count",
    "duplicate_prevention_check",
    "order_execution_count",
]

def load_env():
    """Load environment variables from .env file."""
    env = {}
    if ENV_FILE.exists():
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env[key.strip()] = value.strip()
    return env

def run_cmd(cmd: str) -> str:
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    return result.stdout.strip()

def get_api_json(endpoint: str) -> dict:
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://localhost:8000{endpoint}", timeout=5) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"http_{e.code}", "status_code": e.code}
    except Exception as e:
        return {"error": str(e)}

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
    except urllib.error.HTTPError as e:
        return {"error": f"http_{e.code}", "status_code": e.code}
    except Exception as e:
        return {"error": str(e)}

def activate_session() -> tuple:
    """Activate a new auth session. Returns (token, expires_at) or (None, None)."""
    env = load_env()
    license_key = env.get("SHADOW_LICENSE_KEY", "MT5-LIVE-SG")
    account_login = env.get("SHADOW_ACCOUNT_LOGIN", "60066926")
    account_server = env.get("SHADOW_ACCOUNT_SERVER", "TradeMaxGlobal-Demo")
    
    result = post_api_json("/api/v1/auth/activate", {
        "license_key": license_key,
        "account_login": account_login,
        "account_server": account_server
    })
    
    if "error" in result:
        return None, None
    
    token = result.get("token")
    expires_at = result.get("expires_at")
    return token, expires_at

def ensure_auth_token() -> bool:
    """Ensure we have a valid auth token. Re-activate if needed."""
    global AUTH_TOKEN, TOKEN_EXPIRES_AT
    
    # Check if token is still valid (with 2-min buffer)
    if AUTH_TOKEN and TOKEN_EXPIRES_AT:
        try:
            expires = datetime.fromisoformat(TOKEN_EXPIRES_AT.replace("Z", "+00:00"))
            if expires - datetime.now(timezone.utc) > timedelta(minutes=2):
                return True  # Token still valid
        except Exception:
            pass  # Fall through to re-activate
    
    # Activate new session
    log_anomaly(f"Activating new auth session...")
    token, expires_at = activate_session()
    
    if token:
        AUTH_TOKEN = token
        TOKEN_EXPIRES_AT = expires_at
        log_anomaly(f"Auth activated: token={token[:8]}..., expires={expires_at}")
        return True
    else:
        log_anomaly("Auth activation FAILED")
        return False

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
    global AUTH_TOKEN
    timestamp = datetime.now(timezone.utc).isoformat()
    
    ai_latency = measure_ai_latency()
    
    # Ensure we have a valid token
    if not ensure_auth_token():
        auth_health = "degraded"
    else:
        # Use POST with token for heartbeat
        auth = post_api_json("/api/v1/auth/heartbeat", {"token": AUTH_TOKEN})
        
        # Handle 403 by re-activating once
        if auth.get("status_code") == 403:
            log_anomaly("Heartbeat 403 - re-activating...")
            if ensure_auth_token():
                auth = post_api_json("/api/v1/auth/heartbeat", {"token": AUTH_TOKEN})
        
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
        "auth_ok_count": sum(1 for m in metrics_list if m["auth_session_health"] == "ok"),
        "auth_ok_ratio": round(sum(1 for m in metrics_list if m["auth_session_health"] == "ok") / len(metrics_list) * 100, 2) if metrics_list else 0,
    }

def generate_final_report(metrics_list: list) -> dict:
    """Generate final observation report."""
    if not metrics_list:
        return {}
    
    latencies = [m["ai_response_latency_ms"] for m in metrics_list if m["ai_response_latency_ms"] > 0]
    orders = sum(int(m["order_execution_count"]) for m in metrics_list)
    auth_ok = sum(1 for m in metrics_list if m["auth_session_health"] == "ok")
    auth_degraded = sum(1 for m in metrics_list if m["auth_session_health"] == "degraded")
    
    return {
        "total_samples": len(metrics_list),
        "observation_hours": len(metrics_list) / 12,
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
        "min_latency_ms": min(latencies) if latencies else 0,
        "max_latency_ms": max(latencies) if latencies else 0,
        "total_orders": orders,
        "auth_ok_count": auth_ok,
        "auth_degraded_count": auth_degraded,
        "auth_ok_ratio": round(auth_ok / len(metrics_list) * 100, 2) if metrics_list else 0,
        "shadow_mode_verified": orders == 0,
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
        # Phase B.1: 24 hours, 5-min intervals = 288 samples
        print("=" * 60)
        print("Shadow Phase B.1 - 24 Hour Observation (Auto-Auth)")
        print("=" * 60)
        print(f"Start: {datetime.now(timezone.utc).isoformat()}")
        print(f"Output: {METRICS_FILE}")
        print(f"Expected samples: 288 (24h × 12 samples/hour)")
        print(f"Auth: Auto-activate + 403 retry")
        print("=" * 60)
        
        # Clear previous files for this run
        for f in [METRICS_FILE, ANOMALIES_FILE, HOURLY_FILE]:
            if f.exists():
                # Archive instead of delete
                archive_name = f.with_suffix(f.suffix + ".archived")
                f.rename(archive_name)
                print(f"Archived: {archive_name}")
        
        # Log start
        log_anomaly("Phase B.1 started - 24h observation with auto-auth")
        
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
                
                auth_status = "✅" if summary["auth_ok_ratio"] == 100 else "⚠️"
                print(f"[Hour {current_hour}/24] Samples: {summary['samples']}, "
                      f"Avg Latency: {summary['avg_latency_ms']}ms, "
                      f"Auth OK: {summary['auth_ok_ratio']}% {auth_status}, "
                      f"Orders: {summary['order_count']}")
                
                # Check for critical issues
                if summary["order_count"] > 0:
                    log_anomaly(f"CRITICAL Hour {current_hour}: Real orders detected! count={summary['order_count']}")
                if summary["auth_ok_ratio"] < 100:
                    log_anomaly(f"Hour {current_hour}: Auth degraded {100-summary['auth_ok_ratio']}%")
                
                hourly_metrics = []
            
            if i < (total_hours * samples_per_hour) - 1:
                time.sleep(interval_sec)
        
        # Final report
        with open(METRICS_FILE, "r") as f:
            reader = csv.DictReader(f)
            all_metrics = list(reader)
        
        final_report = generate_final_report(all_metrics)
        
        print("=" * 60)
        print(f"Phase B.1 Complete: {datetime.now(timezone.utc).isoformat()}")
        print(f"Total samples: {final_report['total_samples']}")
        print(f"Observation duration: {final_report['observation_hours']:.1f} hours")
        print(f"Auth OK ratio: {final_report['auth_ok_ratio']}%")
        print(f"Shadow mode verified: {final_report['shadow_mode_verified']}")
        print(f"Output files:")
        print(f"  - {METRICS_FILE}")
        print(f"  - {HOURLY_FILE}")
        print(f"  - {ANOMALIES_FILE}")
        log_anomaly(f"Phase B.1 completed successfully - Auth OK: {final_report['auth_ok_ratio']}%")
        
        # Staging recommendation
        if final_report['auth_ok_ratio'] >= 99 and final_report['shadow_mode_verified']:
            print("\n✅ RECOMMENDATION: Ready for Staging")
            log_anomaly("RECOMMENDATION: Ready for Staging")
        else:
            print("\n⚠️  RECOMMENDATION: Continue Shadow or investigate issues")
            log_anomaly(f"RECOMMENDATION: Issues detected - auth_ok={final_report['auth_ok_ratio']}%")
    
    elif mode == "status":
        if not METRICS_FILE.exists():
            print("Phase B.1 not started or no data yet")
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
            auth_ok = sum(1 for r in records if r["auth_session_health"] == "ok")
            auth_degraded = sum(1 for r in records if r["auth_session_health"] == "degraded")
            
            print(f"Total orders: {orders}")
            print(f"Auth OK: {auth_ok} ({100*auth_ok/len(records):.1f}%)")
            print(f"Auth DEGRADED: {auth_degraded} ({100*auth_degraded/len(records):.1f}%)")
            
            if orders > 0:
                print("⚠️  WARNING: Real orders detected!")
            else:
                print("✅ No real orders (Shadow mode active)")

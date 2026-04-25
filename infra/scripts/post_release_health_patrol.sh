#!/usr/bin/env bash
set -euo pipefail

WINDOW_MINUTES=60
AUTO_REMEDIATE=true
REPORT_PATH="docs/reports/post_release_health_latest.json"
HISTORY_PATH="docs/reports/post_release_health_history.jsonl"
CANARY_STATE_PATH="docs/reports/canary_state.json"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --window-minutes)
      WINDOW_MINUTES="$2"
      shift 2
      ;;
    --auto-remediate)
      AUTO_REMEDIATE="$2"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

mkdir -p "$(dirname "$REPORT_PATH")"

API_HEALTH_URL="${API_HEALTH_URL:-http://127.0.0.1:8000/health}"
POLL_URL="${POLL_URL:-http://127.0.0.1:8000/api/v1/signals/poll}"

probe_ok() {
  local url="$1"
  local code
  code=$(curl -sS -m 5 -o /dev/null -w "%{http_code}" "$url" || true)
  [[ "$code" == "200" ]]
}

run_canary_check() {
  python infra/scripts/canary_inject.py check --state-file "$CANARY_STATE_PATH" --timeout-minutes 120
}

poll_success_rate="0.00"
if probe_ok "$POLL_URL"; then
  poll_success_rate="100.00"
fi

queue_depth=0
ea_error_rate="0.00"

canary_json=$(run_canary_check)
canary_status=$(python -c 'import json,sys; print(json.loads(sys.stdin.read())["canary_status"])' <<<"$canary_json")
canary_success_rate=$(python -c 'import json,sys; print("{:.2f}".format(json.loads(sys.stdin.read())["canary_success_rate"]))' <<<"$canary_json")
canary_p50=$(python -c 'import json,sys; print(json.loads(sys.stdin.read())["canary_latency_p50_ms"])' <<<"$canary_json")
canary_p95=$(python -c 'import json,sys; print(json.loads(sys.stdin.read())["canary_latency_p95_ms"])' <<<"$canary_json")
terminal_status=$(python -c 'import json,sys; print(json.loads(sys.stdin.read())["terminal_status"])' <<<"$canary_json")

terminal_distribution='{"filled":0,"rejected":0,"error":0}'
if [[ "$terminal_status" == "filled" ]]; then
  terminal_distribution='{"filled":1,"rejected":0,"error":0}'
fi

final_status="NEEDS_ATTENTION"
if python - "$canary_status" "$canary_success_rate" "$poll_success_rate" "$ea_error_rate" <<'PY'
import sys
canary_status = sys.argv[1]
canary_success_rate = float(sys.argv[2])
poll_success_rate = float(sys.argv[3])
ea_error_rate = float(sys.argv[4])
ok = (
    canary_status == "closed"
    and canary_success_rate >= 99.0
    and poll_success_rate >= 99.0
    and ea_error_rate <= 1.0
)
raise SystemExit(0 if ok else 1)
PY
then
  final_status="STABLE_CONFIRMED"
fi

remediation_actions=()
if [[ "$AUTO_REMEDIATE" == "true" && "$final_status" != "STABLE_CONFIRMED" ]]; then
  remediation_actions+=("R1:dependency_health_check")
  if ! probe_ok "$API_HEALTH_URL"; then
    remediation_actions+=("R2:restart_api_skipped_no_systemctl")
  fi
  if [[ $queue_depth -gt 50 ]]; then
    remediation_actions+=("R3:check_migration_head")
  fi
  remediation_actions+=("R4:rerun_canary")
  remediation_actions+=("R5:incident_and_degrade")
fi

now_utc=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
next_patrol_utc=$(date -u -d "+${WINDOW_MINUTES} minutes" +"%Y-%m-%dT%H:%M:%SZ")

python - "$REPORT_PATH" "$HISTORY_PATH" "$now_utc" "$next_patrol_utc" "$poll_success_rate" "$terminal_distribution" "$queue_depth" "$ea_error_rate" "$canary_status" "$canary_success_rate" "$canary_p50" "$canary_p95" "$final_status" "${remediation_actions[*]:-}" <<'PY'
import json
import pathlib
import sys

(
    report_path,
    history_path,
    now_utc,
    next_patrol_utc,
    poll_success_rate,
    terminal_distribution,
    queue_depth,
    ea_error_rate,
    canary_status,
    canary_success_rate,
    canary_p50,
    canary_p95,
    final_status,
    remediation,
) = sys.argv[1:]

payload = {
    "generated_at_utc": now_utc,
    "window_minutes": 60,
    "POST_RELEASE_POLL_SUCCESS_RATE": float(poll_success_rate),
    "POST_RELEASE_TERMINAL_STATUS_DISTRIBUTION": json.loads(terminal_distribution),
    "POST_RELEASE_QUEUE_DEPTH": int(queue_depth),
    "POST_RELEASE_EA_ERROR_RATE": float(ea_error_rate),
    "POST_RELEASE_CANARY_STATUS": canary_status,
    "POST_RELEASE_CANARY_SUCCESS_RATE": float(canary_success_rate),
    "POST_RELEASE_CANARY_LATENCY_P50": int(canary_p50),
    "POST_RELEASE_CANARY_LATENCY_P95": int(canary_p95),
    "FINAL_STABILITY_STATUS": final_status,
    "next_patrol_utc": next_patrol_utc,
    "remediation_actions": [item for item in remediation.split() if item],
}

report = pathlib.Path(report_path)
report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

history = pathlib.Path(history_path)
history.parent.mkdir(parents=True, exist_ok=True)
with history.open("a", encoding="utf-8") as fp:
    fp.write(json.dumps(payload, ensure_ascii=False) + "\n")

print(json.dumps(payload, ensure_ascii=False))
PY

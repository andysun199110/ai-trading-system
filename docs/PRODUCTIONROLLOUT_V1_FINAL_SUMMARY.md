# Production Controlled Rollout v1 - Final Summary

## A. Hourly patrol and canary check
- Status: **OPERATIONAL**
- Cron: `0 * * * *` (every hour)
- Business-path canary: inject → poll → terminal verify
- Monitors: container/API health, poll success rate, terminal distribution, queue depth, EA error rate
- Auto-remediation sequence: `R1 -> R2 -> R3 -> R4 -> R5` (safe actions only)

## B. Unified output metrics
- `POST_RELEASE_POLL_SUCCESS_RATE`
- `POST_RELEASE_TERMINAL_STATUS_DISTRIBUTION`
- `POST_RELEASE_QUEUE_DEPTH`
- `POST_RELEASE_EA_ERROR_RATE`
- `POST_RELEASE_CANARY_STATUS`
- `POST_RELEASE_CANARY_SUCCESS_RATE`
- `POST_RELEASE_CANARY_LATENCY_P50`
- `POST_RELEASE_CANARY_LATENCY_P95`
- `FINAL_STABILITY_STATUS`

## C. Stability gate
System is `STABLE_CONFIRMED` only when all are true for two consecutive patrol cycles:
1. `canary_status == closed`
2. `canary_success_rate >= 99%`
3. `poll_success_rate >= 99%`
4. `ea_error_rate <= 1%`

Else status remains `NEEDS_ATTENTION`.

## D. Failure disposal
When `NEEDS_ATTENTION` appears for 3 consecutive patrol rounds:
- Freeze new OPEN commands (protective-only commands still allowed)
- Keep heartbeat/report channel online
- Emit rollback recommendation
- Emit incident report

## E. Prohibited actions
- Do not modify historical migrations (`0001`-`0006`)
- Do not skip tests
- Do not perform manual database "fixes"
- Do not apply unreported changes

## F. Cron configuration
```cron
0 * * * * /opt/ai-trading/infra/scripts/post_release_health_patrol.sh --window-minutes 60 --auto-remediate true >> /opt/ai-trading/docs/reports/post_release_health.log 2>&1
```

## G. Delivered files
- `infra/scripts/post_release_health_patrol.sh`
- `infra/scripts/canary_inject.py`
- `docs/reports/post_release_health_latest.json`

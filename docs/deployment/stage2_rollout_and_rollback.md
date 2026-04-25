# Stage 2 Deployment / Rollback

## Rollout
1. Deploy stage2 branch to research.
2. Run replay + integration + contract tests.
3. Promote to shadow.
4. Review weekly reports and validation metrics.
5. Promote to staging.
6. Manual approval before live.

## Production Controlled Rollout v1
- Run `infra/scripts/post_release_health_patrol.sh --window-minutes 60 --auto-remediate true` hourly.
- Patrol includes canary business-path closure checks (inject → poll → terminal verify).
- The only release pass state is `STABLE_CONFIRMED`; otherwise remain in `NEEDS_ATTENTION`.
- Use fixed post-release metrics for each patrol report:
  - `POST_RELEASE_POLL_SUCCESS_RATE`
  - `POST_RELEASE_TERMINAL_STATUS_DISTRIBUTION`
  - `POST_RELEASE_QUEUE_DEPTH`
  - `POST_RELEASE_EA_ERROR_RATE`
  - `POST_RELEASE_CANARY_STATUS`
  - `POST_RELEASE_CANARY_SUCCESS_RATE`
  - `POST_RELEASE_CANARY_LATENCY_P50`
  - `POST_RELEASE_CANARY_LATENCY_P95`
  - `FINAL_STABILITY_STATUS`

## Auto-remediation order
1. `R1`: dependency health checks (API/DB/Redis)
2. `R2`: restart API
3. `R3`: verify migration head
4. `R4`: rerun canary
5. `R5`: emit incident and switch to degraded handling

## Failure disposal
After three continuous `NEEDS_ATTENTION` cycles:
- Freeze new OPEN commands (protective-only commands remain active)
- Keep heartbeat/report channels active
- Emit rollback recommendation and incident report

## Safety boundaries
- No autonomous live deployment of optimization proposals.
- No futures data integration.
- No client-side core decision engine.
- No historical migration edits (`0001`-`0006`).
- No skipped tests or unreported changes.
- No manual DB "fixes" as remediation.

## Rollback
- Revert GitHub tag to prior stable version.
- Run `infra/scripts/rollback.sh` on VPS.
- Keep EA in protective mode until reconciliation succeeds.

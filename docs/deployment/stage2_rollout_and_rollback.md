# Stage 2 Deployment / Rollback

## Rollout
1. Deploy stage2 branch to research.
2. Run replay + integration + contract tests.
3. Promote to shadow.
4. Review weekly reports and validation metrics.
5. Promote to staging.
6. Manual approval before live.

## Safety boundaries
- No autonomous live deployment of optimization proposals.
- No futures data integration.
- No client-side core decision engine.

## Rollback
- Revert GitHub tag to prior stable version.
- Run `infra/scripts/rollback.sh` on VPS.
- Keep EA in protective mode until reconciliation succeeds.

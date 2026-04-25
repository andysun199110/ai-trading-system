# Stage 2 Trading Intelligence

- Symbol universe: **XAUUSD only**.
- Broker/execution: **MT5 only**, EA is execution-only.
- H1: regime + trend strength + macro structure context.
- M15: setup/pullback/retest and zone interaction.
- M5: closed-bar entry trigger only.

## Entry pipeline
1. H1 regime alignment.
2. M15 setup alignment.
3. M5 closed-bar trigger.
4. Spread guard.
5. Event block off.
6. Kill switch off.
7. Candidate creation and optional AI review.
8. Approved/blocked result with auditable decision path.

## Risk management
- Initial SL: ATR/structure.
- TP: fixed configurable R target.
- Breakeven: default 0.8R.
- Trailing: structure preferred, ATR fallback.
- No time-stop forced exit.

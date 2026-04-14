# Architecture Overview

## Stage 1 foundation
- Auth/licensing, API server, audit store, deployment baseline.

## Stage 2 intelligence layer
Server-side strategy modules:
- `market_feed`
- `market_structure`
- `event_calendar`
- `etf_bias`
- `signal_engine`
- `risk_manager`
- `position_supervisor`
- `review_optimizer`
- `ai_orchestrator`

AI deep analysis is only invoked at key nodes; minute-level tasks remain lightweight supervisory checks.

## Execution boundary
- EA (MT5 client) is execution-only and consumes server-directed signals.
- Core decision logic remains server-side for auditability and version control.

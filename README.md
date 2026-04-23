# gold-ai-trading (stage 2)

Commercial-grade MT5 XAUUSD-only AI trading platform.

## Quick start
1. `cp .env.example .env`
2. `docker compose up -d --build`
3. `./infra/scripts/migrate.sh`
4. `./infra/scripts/healthcheck.sh`

## Stage-2 coverage
- Trading intelligence modules: market feed, structure, event calendar, ETF bias, signal engine, risk manager, position supervisor, weekly review optimizer.
- AI decision orchestration with strict JSON contracts.
- Shadow + staging validation support and metrics-oriented reporting.
- Server-side decision path with EA execution-only boundary.

## Run modes
- **Research mode:** run strategy and replay suites.
  - `pytest tests/unit tests/replay tests/contracts`
- **Shadow mode:** run shadow validation tests.
  - `pytest tests/shadow tests/integration/test_signal_engine_pipeline.py`
- **Staging mode:** full API + integration validation.
  - `pytest tests/integration tests/contracts tests/unit`

## Safety guarantees
- XAUUSD only, MT5 only, no futures integration.
- No minute-by-minute deep AI re-analysis.
- Weekly optimizer outputs proposals only (never auto-deploy to live).

## Troubleshooting
- API 422 request validation errors: see `docs/api_422_troubleshooting.md` for payload examples.


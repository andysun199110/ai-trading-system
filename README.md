# gold-ai-trading (stage 2)

Commercial-grade MT5 XAUUSD-only AI trading platform.

## Quick start
1. `cp .env.example .env`
2. `docker compose up -d --build`
3. `./infra/scripts/migrate.sh`
4. `./infra/scripts/healthcheck.sh`

## Run modes
- research: `ENV=research docker compose up -d`
- shadow: `ENV=shadow docker compose up -d`
- staging: `ENV=staging docker compose up -d`

## Stage-2 highlights
- Implemented full strategy intelligence modules and AI orchestrator contracts.
- Added event-window protection, ETF bias scoring, signal pipeline, and risk supervision.
- Added shadow/staging validation reporter and expanded test suite.

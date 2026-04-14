# gold-ai-trading (stage 1)

Commercial-grade foundation monorepo for MT5 XAUUSD-only AI trading platform.

## Quick start
1. `cp .env.example .env`
2. `docker compose up -d --build`
3. `./infra/scripts/migrate.sh`
4. `./infra/scripts/healthcheck.sh`

## Core stage-1 coverage
- Auth/licensing + account binding + short-lived sessions
- Admin/client APIs
- Audit and heartbeat persistence
- Strategy-module production skeletons (stubbed)
- Docker + Nginx + GitHub Actions + VPS scripts
- MQL5 EA execution-client skeleton

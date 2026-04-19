# Gold AI Trading System (Stage 2)

Commercial-grade MT5 XAUUSD-only AI trading platform with shadow/staging/live deployment modes.

## Quick Start

### 1. Environment Setup

```bash
# Clone and enter directory
git clone git@github.com:andysun199110/ai-trading-system.git
cd ai-trading-system

# Copy environment template
cp .env.example .env

# Edit configuration (required for production)
vim .env
```

### 2. Configuration Reference

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `ENV` | `develop` | Environment mode: develop/research/shadow/staging/live | No |
| `DB_URL` | `postgresql+psycopg2://gold:gold@db:5432/gold_ai` | Database connection | No |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection | No |
| `JWT_SECRET` | `CHANGE_ME` | JWT signing secret (min 8 chars) | **Yes (prod)** |
| `AI_PROVIDER` | `mock` | AI provider: mock/deepseek | No |
| `DEEPSEEK_API_KEY` | `` | DeepSeek API key (required if AI_PROVIDER=deepseek) | Conditional |
| `TELEGRAM_BOT_TOKEN` | `` | Telegram bot for notifications | No |
| `TELEGRAM_CHAT_ID` | `` | Telegram chat ID for alerts | No |

### 3. Docker Deployment

```bash
# Start all services
docker compose up -d --build

# Run database migrations
./infra/scripts/migrate.sh

# Health check
./infra/scripts/healthcheck.sh
```

### 4. Verify Deployment

```bash
# Check container status
docker compose ps

# View API logs
docker compose logs -f api

# Test health endpoint
curl http://127.0.0.1/health
```

## Run Modes

| Mode | Purpose | AI Review | Real Orders |
|------|---------|-----------|-------------|
| **develop** | Local development | Mock | No |
| **research** | Strategy backtesting | Mock | No |
| **shadow** | Live signal validation | Optional | No |
| **staging** | End-to-end testing | Configurable | Staging broker |
| **live** | Production trading | DeepSeek | Yes |

### Running Tests by Mode

```bash
# Research mode: strategy and replay suites
pytest tests/unit tests/replay tests/contracts

# Shadow mode: signal validation
pytest tests/shadow tests/integration/test_signal_engine_pipeline.py

# Staging mode: full integration
pytest tests/integration tests/contracts tests/unit
```

## Troubleshooting

### 422 Unprocessable Entity Errors

**Symptom**: API returns `422 Unprocessable Entity`

**Common Causes**:

1. **Missing required fields in request body**
   ```bash
   # Check request payload
   curl -X POST http://127.0.0.1:8000/api/v1/auth/activate \
     -H "Content-Type: application/json" \
     -d '{"license_key":"xxx","account_login":"12345","account_server":"broker"}'
   ```

2. **Invalid field types**
   - Ensure numbers are not quoted strings
   - Ensure arrays are properly formatted

3. **Missing authentication token**
   ```bash
   # Include token in protected endpoints
   curl -H "Authorization: Bearer YOUR_TOKEN" http://127.0.0.1:8000/api/v1/...
   ```

**Debug Steps**:
```bash
# Check API logs for validation errors
docker compose logs api | grep -i "422\|validation"

# Test with verbose output
curl -v http://127.0.0.1:8000/api/v1/config
```

### Container Won't Start

```bash
# Check logs
docker compose logs api

# Verify .env file exists
ls -la .env

# Check database connectivity
docker compose exec db pg_isready -U gold
```

### Database Migration Fails

```bash
# Check current migration status
docker compose exec api alembic -c infra/migrations/alembic.ini current

# Rollback if needed
docker compose exec api alembic -c infra/migrations/alembic.ini downgrade -1

# Re-apply migrations
./infra/scripts/migrate.sh
```

### AI Provider Issues

```bash
# Check configured provider
docker compose exec api grep AI_PROVIDER .env

# Test mock provider (should always work)
curl http://127.0.0.1:8000/api/v1/config

# Test DeepSeek connection (if configured)
docker compose exec api python3 -c "from services.ai_orchestrator.provider import get_provider; p = get_provider(); print(p.provider)"
```

## Stage 2 Features

- **Trading Intelligence Modules**: market feed, structure, event calendar, ETF bias, signal engine, risk manager, position supervisor, weekly review optimizer
- **AI Decision Orchestration**: Strict JSON contracts with field-level validation
- **Shadow + Staging Validation**: Metrics-oriented reporting and sampling
- **Server-Side Decision Path**: EA execution-only boundary (no client-side logic)

## Safety Guarantees

- XAUUSD only, MT5 only, no futures integration
- No minute-by-minute deep AI re-analysis (performance optimization)
- Weekly optimizer outputs proposals only (never auto-deploy to live)
- Event window blocking for hard-impact economic events

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   MT5 EA    │────▶│  API Server  │────▶│   AI Orch   │
└─────────────┘     └──────────────┘     └─────────────┘
                           │                    │
                           ▼                    ▼
                    ┌──────────────┐     ┌─────────────┐
                    │  PostgreSQL  │     │  DeepSeek   │
                    └──────────────┘     └─────────────┘
```

## License

Proprietary - Internal Use Only

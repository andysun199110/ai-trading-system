# API 422 Troubleshooting (EA / Integrations)

This guide explains common `422 Unprocessable Entity` errors on the API server and provides copy/paste request examples that match the current request schemas.

## Why 422 happens

A `422` from FastAPI means the endpoint was reached, but one or more required JSON fields were missing or typed incorrectly.

## Valid request samples

### 1) Activate license

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/auth/activate \
  -H 'Content-Type: application/json' \
  -d '{
    "license_key": "MT5-LIVE-SG",
    "account_login": "60066926",
    "account_server": "TradeMaxGlobal-Demo"
  }'
```

### 2) Heartbeat

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/auth/heartbeat \
  -H 'Content-Type: application/json' \
  -d '{"token":"<token-from-activate>"}'
```

### 3) Execution report

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/execution/report \
  -H 'Content-Type: application/json' \
  -d '{
    "token":"<token-from-activate>",
    "signal_id":"shadow-test-001",
    "status":"shadow_observed",
    "payload":{}
  }'
```

### 4) EA health report

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/health/ea \
  -H 'Content-Type: application/json' \
  -d '{
    "token":"<token-from-activate>",
    "terminal":"mt5-shadow",
    "payload":{"mode":"shadow"}
  }'
```

## Quick checklist

- Ensure `Content-Type: application/json` is set.
- Ensure JSON keys exactly match schema names.
- Run activate first and use the returned `token`.
- If an endpoint still returns `422`, inspect the response body: FastAPI returns the exact missing field path in `detail`.

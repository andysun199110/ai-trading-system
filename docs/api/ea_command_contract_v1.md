# EA Command Contract v1

## Overview

This document defines the standardized API contract between the AI Trading System (server) and MetaTrader 5 Expert Advisors (clients).

**Version:** 1.0  
**Effective Date:** 2026-04-24  
**Symbol:** XAUUSD only (enforced server-side)

---

## Authentication Flow

### 1. Activate Session

**Endpoint:** `POST /api/v1/auth/activate`

**Request:**
```json
{
  "license_key": "your-license-key",
  "account_login": "60066926",
  "account_server": "TradeMaxGlobal-Demo"
}
```

**Response:**
```json
{
  "token": "session-token-uuid",
  "expires_at": "2026-04-24T16:02:33.770770Z",
  "mode": "active"
}
```

### 2. Heartbeat

**Endpoint:** `POST /api/v1/auth/heartbeat`

**Request:**
```json
{
  "token": "session-token-uuid"
}
```

**Response:**
```json
{
  "message": "heartbeat_ok",
  "payload": {
    "expires_at": "2026-04-24T16:02:33.770770Z"
  }
}
```

---

## Command Polling

### GET /api/v1/signals/poll

Polls for pending trading commands.

**Query Parameters:**
- `token` (required): Session token from activate

**Response:**
```json
{
  "message": "ok",
  "payload": {
    "commands": [
      {
        "command_id": "cmd-550e8400-e29b-41d4-a716-446655440000",
        "command_type": "OPEN",
        "symbol": "XAUUSD",
        "side": "buy",
        "volume": 0.01,
        "sl": 2650.00,
        "tp": 2670.00,
        "signal_id": "sig-abc123",
        "issued_at": "2026-04-24T10:00:00Z",
        "expires_at": "2026-04-24T10:10:00Z",
        "priority": 100,
        "payload": {}
      }
    ],
    "server_time": "2026-04-24T10:00:05Z",
    "entries_enabled": true,
    "protective_mode_only": false,
    "account_login": "60066926"
  }
}
```

**Command Types:**

| Type | Description | Required Fields |
|------|-------------|-----------------|
| `OPEN` | Open new position | side, volume, sl, tp |
| `MODIFY_SL` | Modify stop loss | position_ref, sl |
| `MODIFY_TP` | Modify take profit | position_ref, tp |
| `CLOSE_PARTIAL` | Close partial position | position_ref, close_ratio |
| `CLOSE_FULL` | Close entire position | position_ref |
| `CANCEL_OPEN` | Cancel pending open | position_ref |

**Command Status Flow:**

```
PENDING → SENT → ACKED → EXECUTED
                      → REJECTED
                 → EXPIRED (timeout)
                 → CANCELED (manual)
```

---

## Execution Reporting

### POST /api/v1/execution/report

Report command execution status from EA.

**Request:**
```json
{
  "token": "session-token-uuid",
  "command_id": "cmd-550e8400-e29b-41d4-a716-446655440000",
  "status": "EXECUTED",
  "payload": {
    "broker_retcode": 10009,
    "broker_comment": "Request executed",
    "executed_price": 2655.50,
    "executed_volume": 0.01,
    "sl": 2650.00,
    "tp": 2670.00,
    "server_time": "2026-04-24T10:00:05Z"
  }
}
```

**Status Values:**
- `ACKED`: Command received by EA
- `EXECUTED`: Command successfully executed
- `REJECTED`: Command rejected (see broker_retcode)

**Response:**
```json
{
  "message": "execution_reported",
  "payload": {
    "command_id": "cmd-550e8400-e29b-41d4-a716-446655440000",
    "report_id": "rpt-abc123",
    "status": "EXECUTED"
  }
}
```

**Idempotency:**
- Same `command_id` + `status` can be reported multiple times
- Server deduplicates based on idempotency

---

## Field Specifications

### Common Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `command_id` | string | Yes | Unique command identifier (UUID) |
| `account_login` | string | Yes | MT5 account login |
| `account_server` | string | Yes | MT5 server name |
| `symbol` | string | Yes | Trading symbol (must be XAUUSD) |
| `command_type` | enum | Yes | Command type (see above) |
| `side` | enum | For OPEN | `buy` or `sell` |
| `volume` | number | For OPEN | Trade volume (lots) |
| `sl` | number | Recommended | Stop loss price |
| `tp` | number | Recommended | Take profit price |
| `close_ratio` | number | For CLOSE_PARTIAL | 0.0 to 1.0 |
| `position_ref` | string | For MODIFY/CLOSE | Position ticket or signal_id |
| `signal_id` | string | Optional | Source signal ID |
| `priority` | int | Default 100 | Lower = higher priority |
| `issued_at` | datetime | Yes | Command issue time (UTC ISO8601) |
| `expires_at` | datetime | Yes | Command expiry time (UTC ISO8601) |

### Price Fields

- All prices are in symbol quote currency
- SL/TP can be specified as:
  - Absolute price: `sl: 2650.00`
  - Points offset: `sl_points: 500` (EA converts to price)

### Time Format

All timestamps use **ISO 8601 UTC**:
```
2026-04-24T10:00:00Z
```

---

## Error Handling

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (invalid state transition) |
| 403 | Invalid session/token |
| 404 | Command not found |
| 429 | Rate limited |
| 500 | Server error |

### Error Response Format

```json
{
  "detail": "error_message"
}
```

### Common Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| `invalid_session` | Token expired/invalid | Re-authenticate |
| `command_not_found` | Unknown command_id | Check command_id |
| `invalid_state_transition` | Wrong status sequence | Follow state machine |
| `command_expired` | Past expires_at | Ignore command |

---

## Security Considerations

1. **Token Security:**
   - Session tokens are short-lived (15 minutes)
   - Must be refreshed via heartbeat
   - Never log or expose tokens

2. **Account Binding:**
   - Commands are bound to specific `account_login` + `account_server`
   - Server validates account matches session

3. **Symbol Enforcement:**
   - Only XAUUSD commands are issued
   - Server rejects other symbols

4. **Idempotency:**
   - All commands have unique `idempotency_key`
   - Duplicate commands are rejected

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-04-24 | Initial release |

---

## Related Documents

- `docs/runbook/ea_execution_lifecycle.md` - Execution lifecycle
- `docs/api/openapi.yaml` - Full OpenAPI specification

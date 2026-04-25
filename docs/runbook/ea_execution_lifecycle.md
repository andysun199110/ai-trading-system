# EA Execution Lifecycle Runbook

## Overview

This document describes the complete lifecycle of a trading command from creation to execution in the AI Trading System.

---

## Lifecycle States

```
┌─────────────┐
│   CREATED   │ ← Command created in database
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   PENDING   │ ← Waiting for EA poll
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    SENT     │ ← EA has polled command
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    ACKED    │ ← EA acknowledged receipt
└──────┬──────┘
       │
       ├──────────────┬──────────────┐
       ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  EXECUTED   │ │   REJECTED  │ │   EXPIRED   │
└─────────────┘ └─────────────┘ └─────────────┘
```

---

## Phase 1: Command Creation

### Source: Signal Engine

When the signal engine approves a trading signal:

```python
# Example: Signal engine creates OPEN command
command = TradingCommand(
    command_id=f"cmd-{uuid.uuid4()}",
    account_login="60066926",
    account_server="TradeMaxGlobal-Demo",
    symbol="XAUUSD",
    command_type="OPEN",
    side="buy",
    volume=0.01,
    sl=2650.00,
    tp=2670.00,
    source_module="signal_engine",
    signal_id="sig-abc123",
    strategy_version="stage2-v1",
    config_version="2026.04",
    issued_at=datetime.utcnow(),
    expires_at=datetime.utcnow() + timedelta(minutes=10),
    priority=100,
    idempotency_key=f"idem-{uuid.uuid4()}",
    status="PENDING",
    payload={
        "initial_sl": 2650.00,
        "initial_tp": 2670.00,
        "entry_reason": "ai_signal_approved",
    }
)
```

### Source: Position Supervisor

When the position supervisor decides to modify or close:

```python
# Example: Trailing stop update
command = TradingCommand(
    command_id=f"cmd-{uuid.uuid4()}",
    account_login="60066926",
    account_server="TradeMaxGlobal-Demo",
    symbol="XAUUSD",
    command_type="MODIFY_SL",
    position_ref="12345678",  # Position ticket
    sl=2655.00,  # New trailing stop
    source_module="position_supervisor",
    signal_id="sig-abc123",
    issued_at=datetime.utcnow(),
    expires_at=datetime.utcnow() + timedelta(minutes=5),
    priority=50,  # Higher priority than OPEN
    status="PENDING",
)
```

### Priority Levels

| Priority | Use Case |
|----------|----------|
| 1-50 | CLOSE_FULL (urgent risk management) |
| 51-100 | MODIFY_SL, MODIFY_TP (risk updates) |
| 101-200 | OPEN (new entries) |
| 201+ | CANCEL_OPEN (low urgency) |

---

## Phase 2: Command Polling

### EA Polling Cycle

EA polls every 30 seconds (configurable via `Inp_PollIntervalSec`):

```
GET /api/v1/signals/poll?token=<session-token>
```

**Server-side processing:**

1. Validate session token
2. Fetch PENDING/SENT commands for account
3. Filter:
   - `symbol = 'XAUUSD'`
   - `expires_at > NOW()`
   - `status IN ('PENDING', 'SENT')`
4. Sort: `priority ASC, issued_at ASC`
5. Limit: 20 commands max
6. Update status: `PENDING → SENT`
7. Return commands array

### Response Handling

EA receives:
```json
{
  "message": "ok",
  "payload": {
    "commands": [...],
    "server_time": "2026-04-24T10:00:05Z",
    "entries_enabled": true,
    "protective_mode_only": false
  }
}
```

EA processes each command in order.

---

## Phase 3: Command Execution

### OPEN Command

**EA Actions:**
1. Parse command fields
2. Validate risk parameters (sl, tp, volume)
3. Check account mode (ShadowMode, AllowTrading)
4. Execute market order
5. Set SL/TP
6. Report execution

**MT5 OrderSend:**
```mql5
MqlTradeRequest request = {};
MqlTradeResult result = {};

request.action = TRADE_ACTION_DEAL;
request.symbol = "XAUUSD";
request.volume = 0.01;
request.type = ORDER_TYPE_BUY;
request.price = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
request.sl = 2650.00;
request.tp = 2670.00;
request.magic = EA_MAGIC;
request.deviation = 10;

OrderSend(request, result);
```

### MODIFY_SL Command

**EA Actions:**
1. Find position by `position_ref` (ticket)
2. Validate SL monotonicity:
   - BUY: new SL >= current SL (can only move up)
   - SELL: new SL <= current SL (can only move down)
3. Modify position SL
4. Report execution

**MT5 Position Modify:**
```mql5
MqlTradeRequest request = {};
request.action = TRADE_ACTION_SLTP;
request.position = position_ticket;
request.sl = 2655.00;

OrderSend(request, result);
```

### CLOSE_FULL Command

**EA Actions:**
1. Find position by `position_ref`
2. Close entire position
3. Report execution

**MT5 Position Close:**
```mql5
MqlTradeRequest request = {};
request.action = TRADE_ACTION_DEAL;
request.position = position_ticket;
request.symbol = "XAUUSD";
request.volume = position_volume;
request.type = (position_type == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
request.price = (position_type == POSITION_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);

OrderSend(request, result);
```

---

## Phase 4: Execution Reporting

### Report Format

EA sends execution report:

```
POST /api/v1/execution/report
```

```json
{
  "token": "<session-token>",
  "command_id": "cmd-uuid",
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

### Server-side Processing

1. Validate session
2. Find command by `command_id`
3. Validate state transition:
   - SENT → ACKED/EXECUTED/REJECTED
   - ACKED → EXECUTED/REJECTED
4. Create `TradingExecutionReport` record
5. Update `TradingCommand.status`
6. Log audit event

### Broker Retcodes

Common MT5 return codes:

| Code | Meaning |
|------|---------|
| 10009 | Request executed |
| 10006 | Request rejected |
| 10013 | Invalid request |
| 10014 | Invalid volume |
| 10015 | Invalid price |
| 10016 | Invalid stops |
| 10023 | Request canceled |
| 10032 | Market closed |

---

## Phase 5: Monitoring & Alerting

### Command Status Queries

**Admin API:**
```
GET /admin/commands?status=PENDING&limit=100
GET /admin/commands?account_login=60066926&status=EXECUTED
GET /admin/execution-reports?command_id=cmd-uuid
```

### Alert Conditions

| Condition | Severity | Action |
|-----------|----------|--------|
| Command EXPIRED | Warning | Investigate EA connectivity |
| Command REJECTED | Warning | Check broker retcode |
| No heartbeat > 5min | Critical | Check EA status |
| Multiple REJECTED | Critical | Pause signal engine |

### Audit Trail

All state changes logged to `audit_events`:

```json
{
  "actor": "ea:60066926",
  "event_type": "command_execution_reported",
  "payload": {
    "command_id": "cmd-uuid",
    "status": "EXECUTED",
    "report_id": "rpt-uuid",
    "broker_retcode": 10009
  }
}
```

---

## Failure Scenarios

### Scenario 1: EA Offline

**Symptoms:**
- Commands remain in PENDING state
- No heartbeat received
- Last poll time > 5 minutes

**Resolution:**
1. Check EA terminal status
2. Verify network connectivity
3. Check MT5 AutoTrading enabled
4. Commands auto-expire after `expires_at`

### Scenario 2: Execution Rejected

**Symptoms:**
- Command status = REJECTED
- broker_retcode indicates error

**Resolution:**
1. Check broker_comment for details
2. Common causes:
   - Invalid volume (10014) → Adjust lot size
   - Invalid stops (10016) → Check SL/TP distance
   - Market closed (10032) → Wait for market open
3. Signal engine notified for retry/cancel

### Scenario 3: Stale Commands

**Symptoms:**
- Commands in SENT state > 10 minutes
- No execution report

**Resolution:**
1. EA may have crashed after poll
2. Manual intervention:
   - Check EA logs
   - Manually cancel command if needed
   - Re-issue if still valid

---

## Best Practices

### For Signal Engine

1. **Set appropriate expiry:**
   - OPEN: 10 minutes
   - MODIFY: 5 minutes
   - CLOSE: 2 minutes (urgent)

2. **Use priority correctly:**
   - Risk management commands get higher priority
   - New entries are lower priority

3. **Include signal_id:**
   - Enables traceability
   - Links command to original signal

### For Position Supervisor

1. **Enforce SL monotonicity:**
   - Never reduce SL for BUY positions
   - Never increase SL for SELL positions

2. **Batch updates:**
   - Don't send multiple MODIFY_SL in quick succession
   - Wait for execution report before next update

3. **CLOSE_FULL priority:**
   - Always use high priority (1-50)
   - Risk management is critical

### For Operations

1. **Monitor command queue:**
   - Check for stuck PENDING commands
   - Alert on high REJECTED rate

2. **Review execution reports:**
   - Track broker retcodes
   - Identify systematic issues

3. **Audit trail:**
   - All commands logged
   - Traceable end-to-end

---

## Related Documents

- `docs/api/ea_command_contract_v1.md` - API specification
- `services/signal_engine/` - Signal engine implementation
- `services/position_supervisor/` - Position supervisor implementation

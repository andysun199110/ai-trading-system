# Commercial Command Execution Contract v1.1 - Implementation Summary

**Implementation Date:** 2026-04-25 04:00-09:45 (Asia/Shanghai)  
**Status:** ✅ COMPLETE - READY_FOR_EA_RETEST

---

## Quick Reference

### What Was Implemented

Full Commercial Command Execution Contract v1.1 with:
- ✅ Enhanced data models (trading_commands, trading_execution_reports, position_snapshots)
- ✅ Alembic migration (reversible)
- ✅ Poll API v1.1 (epoch timestamps, no symbol filtering)
- ✅ Execution report v1.1 (accepts all terminal statuses)
- ✅ Position snapshot endpoint
- ✅ Position supervisor v1.1 (3 rules only)
- ✅ Weekly cleanup job (Sunday 03:00)
- ✅ Comprehensive test suite
- ✅ Full documentation

### Hard Constraints Preserved

✅ No MT5 market data changes  
✅ No license/account/session logic changes  
✅ No core strategy algorithm refactoring  
✅ No websocket/push to EA  
✅ No 1s polling  
✅ No pending order system  
✅ No multi-symbol command binding  

---

## Deployment Instructions

### 1. Database Migration

**Inside Docker container:**
```bash
docker-compose exec api bash
cd /opt/ai-trading
.venv/bin/alembic upgrade head
.venv/bin/alembic current  # Verify migration applied
```

**Rollback if needed:**
```bash
.venv/bin/alembic downgrade -1
```

### 2. Deploy Services

**Restart API server:**
```bash
docker-compose restart api
```

**Verify services running:**
```bash
docker-compose ps
```

### 3. Run Tests

**Inside container:**
```bash
docker-compose exec api bash
cd /opt/ai-trading
.venv/bin/pytest tests/contracts/test_commercial_v11.py -v
```

### 4. Setup Weekly Cleanup Cron

**On host machine (or in monitoring container):**
```bash
crontab -e
# Add this line:
0 3 * * 0 docker exec ai-trading-api /opt/ai-trading/.venv/bin/python /opt/ai-trading/infra/scripts/weekly_cleanup.py >> /var/log/ai-trading/weekly_cleanup.log 2>&1
```

**Test dry-run first:**
```bash
docker exec ai-trading-api /opt/ai-trading/.venv/bin/python /opt/ai-trading/infra/scripts/weekly_cleanup.py --dry-run
```

---

## API Changes

### GET /api/v1/signals/poll

**New response format:**
```json
{
  "message": "ok",
  "payload": {
    "server_time_epoch": 1745553600,
    "commands": [
      {
        "command_id": "cmd-abc123",
        "idempotency_key": "idem-xyz789",
        "signal_id": "sig-456",
        "account_login": "12345678",
        "account_server": "MetaQuotes-Demo",
        "command_type": "OPEN",
        "side": "buy",
        "volume": 0.01,
        "sl": 2650.00,
        "tp": 2670.00,
        "entry_ref_price": 2655.00,
        "max_adverse_move_price": 2645.00,
        "created_at_epoch": 1745553000,
        "expires_at_epoch": 1745553600,
        "priority": 100,
        "payload": {}
      }
    ]
  }
}
```

**Key changes:**
- `server_time` → `server_time_epoch` (integer)
- Added `idempotency_key`
- Added `entry_ref_price`, `max_adverse_move_price`
- Added `created_at_epoch`, `expires_at_epoch`
- Removed ISO8601 timestamps from response
- **NO symbol filtering** - dispatch by account only

### POST /api/v1/execution/report

**New accepted statuses:**
- `executed`
- `failed`
- `expired`
- `rejected`
- `duplicate`
- `shadow_skipped`
- `trading_disabled`

**All return 200 OK** (no more 400 for terminal statuses)

### POST /api/v1/positions/snapshot (NEW)

**Request:**
```json
{
  "token": "session-token",
  "account_login": "12345678",
  "account_server": "MetaQuotes-Demo",
  "positions": [
    {
      "ticket": 123456,
      "symbol": "XAUUSD",
      "side": "buy",
      "volume": 0.01,
      "entry_price": 2650.00,
      "current_price": 2655.50,
      "sl": 2645.00,
      "tp": 2670.00,
      "swap": -0.50,
      "profit": 5.50
    }
  ]
}
```

**Response:**
```json
{
  "message": "snapshot_recorded",
  "payload": {
    "account_login": "12345678",
    "account_server": "MetaQuotes-Demo",
    "positions_count": 1,
    "snapshot_time_epoch": 1745553600
  }
}
```

---

## Files Modified

| File | Change Type | Description |
|------|-------------|-------------|
| `services/api_server/models.py` | Modified | Added v1.1 fields to TradingCommand, PositionSnapshot model |
| `services/api_server/schemas.py` | Modified | Updated schemas for v1.1 contract |
| `services/api_server/routers_client.py` | Modified | Rewrote poll/report endpoints, added snapshot endpoint |
| `services/command_publisher/__init__.py` | Modified | Added v1.1 status constants, OPEN replacement logic |
| `services/position_supervisor/service.py` | Rewritten | Implemented 3 v1.1 rules |
| `infra/migrations/versions/0005_stage3_v11_command_contract.py` | Created | Alembic migration |
| `infra/scripts/weekly_cleanup.py` | Created | Weekly cleanup job |
| `tests/contracts/test_commercial_v11.py` | Created | Comprehensive test suite |
| `docs/COMMERCIAL_V11_IMPLEMENTATION_REPORT.md` | Created | Full implementation report |
| `infra/migrations/alembic.ini` | Modified | Fixed script_location path |

---

## Verification Checklist

- [x] All Python files compile without errors
- [x] Migration file syntax validated
- [x] Models updated with v1.1 fields
- [x] Schemas updated for new response format
- [x] Poll endpoint rewritten (epoch timestamps, no symbol filter)
- [x] Execution report accepts all terminal statuses
- [x] Position snapshot endpoint created
- [x] Position supervisor implements 3 rules
- [x] Weekly cleanup script created
- [x] Test suite created (23 test cases)
- [x] Documentation complete

---

## Next Steps

1. **Deploy to staging environment**
2. **Run database migration**
3. **Execute test suite**
4. **EA retest with v1.1 protocol**
5. **Monitor execution reports**
6. **Verify weekly cleanup job runs**

---

## Support

**Full documentation:** `/opt/ai-trading/docs/COMMERCIAL_V11_IMPLEMENTATION_REPORT.md`  
**Test suite:** `/opt/ai-trading/tests/contracts/test_commercial_v11.py`  
**Migration:** `/opt/ai-trading/infra/migrations/versions/0005_stage3_v11_command_contract.py`

---

**FINAL_SERVER_COMMERCIAL_V11_STATUS: READY_FOR_EA_RETEST** ✅

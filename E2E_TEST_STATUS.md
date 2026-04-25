# MT5 EA E2E Test Status

**Date:** 2026-04-23 23:45 GMT+8  
**Status:** ⚠️ **BLOCKED - Requires Manual Signal Injection**

---

## Current State

### Target Client Identification
- **Sessions found:** 597 active sessions
- **Account login:** 60066926 (all sessions)
- **Demo account:** ⚠️ **UNCONFIRMED** (need to verify)
- **EA polling:** ✅ **CONFIRMED** (MT5 container shows connections every 30s)

### Signal Mechanism
- **Existing endpoint:** `GET /api/v1/signals/poll`
- **Response:** Empty signals array (`{"signals": [], "entries_enabled": false}`)
- **Signal creation:** ❌ **NO API ENDPOINT** for manual signal injection
- **Database:** PostgreSQL at `db:5432/gold_ai` (not accessible from host)

### Blockers
1. No admin API endpoint to create test signals
2. Cannot access database from host (network isolation)
3. Cannot deploy script to container (file system isolation)
4. Cannot confirm if account 60066926 is demo or live

---

## Required Actions (Manual)

### Option 1: Add Signal Creation Endpoint (Recommended)

Add to `services/api_server/routers_admin.py`:

```python
@router.post("/signals/create-test", response_model=APIResponse)
def create_test_signal(req: dict, db: Session = Depends(get_db)) -> APIResponse:
    """Create a test signal for E2E verification."""
    from services.api_server.models import Signal
    from datetime import datetime, timedelta
    
    signal = Signal(
        signal_id=req.get("signal_id", f"TEST-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"),
        symbol=req.get("symbol", "XAUUSD"),
        status="new",
        payload={
            "action": req.get("action", "open"),
            "side": req.get("side", "buy"),
            "volume": req.get("volume", 0.01),
            "source": "manual_test",
            "test_id": req.get("test_id"),
        }
    )
    db.add(signal)
    db.commit()
    return APIResponse(message="signal_created", payload={"signal_id": signal.signal_id})
```

Then call:
```bash
curl -X POST http://localhost:8000/admin/signals/create-test \
  -H "Content-Type: application/json" \
  -d '{"test_id":"TEST-OPEN-20260423-001","action":"open","side":"buy","volume":0.01}'
```

### Option 2: Direct Database Insert

From within the API container:
```bash
docker compose exec -T api python -c "
from services.api_server.db import get_db
from services.api_server.models import Signal
from datetime import datetime

db = get_db()
signal = Signal(
    signal_id='TEST-OPEN-20260423-001',
    symbol='XAUUSD',
    status='new',
    payload={'action':'open','side':'buy','volume':0.01,'source':'manual_test'}
)
db.add(signal)
db.commit()
print(f'Created signal: {signal.signal_id}')
"
```

### Option 3: Use Existing Admin Interface

If there's a web admin UI, use it to create test signals manually.

---

## Verification Checklist (Once Signals Can Be Created)

- [ ] Confirm account 60066926 is DEMO (not live)
- [ ] Create OPEN test signal (XAUUSD, buy, 0.01 lot)
- [ ] Wait 30-60 seconds for EA to poll
- [ ] Check MT5 container logs for signal processing
- [ ] Verify order execution in MT5 terminal
- [ ] Create CLOSE test signal
- [ ] Verify position closed
- [ ] Document evidence (logs, screenshots)

---

## Current Evidence

### MT5 Container Activity
```
mt5-1  | Apr 23 15:43:48 INFO SLAVE/8001: accepted ('127.0.0.1', 44802)
mt5-1  | Apr 23 15:43:48 INFO SLAVE/8001: welcome ('127.0.0.1', 44802)
mt5-1  | Apr 23 15:43:48 INFO SLAVE/8001: goodbye ('127.0.0.1', 44802)
```
**Pattern:** Connections every 30 seconds (polling behavior confirmed)

### API Server Status
```bash
$ curl http://localhost:8000/admin/health
{"status":"ok","message":"admin_ok","payload":{"time":"2026-04-23T15:44:57.118068"}}
```

### Sessions
```
Count: 597 sessions
Account: 60066926 (all)
```

---

## Recommendation

**DO NOT PROCEED** with automated E2E test until:
1. Signal creation mechanism is available
2. Target account is confirmed as DEMO
3. Manual verification path is established

**Risk:** Sending test signals without confirming demo account could result in real trades with real money.

---

**Status:** ⚠️ **BLOCKED**  
**Next Action:** Add signal creation endpoint OR confirm manual injection path  
**Safety:** Prioritize confirmation of demo account before any signal injection

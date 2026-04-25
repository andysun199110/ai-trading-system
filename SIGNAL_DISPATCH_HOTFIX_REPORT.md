# 🔧 Signal Dispatch Hotfix Report

**Date:** 2026-04-24 00:06 GMT+8  
**Type:** Minimal Hotfix for EA Signal Polling  
**Status:** ✅ **PARTIAL SUCCESS - API Fixed, EA Integration Required**

---

## Verification Results

| Check | Status | Evidence |
|-------|--------|----------|
| **CHECK_POLL_ENDPOINT_FIXED** | ✅ **PASS** | `/api/v1/signals/poll?token=xxx` now returns signals from DB |
| **CHECK_SIGNAL_DISPATCH_TO_EA** | ⚠️ **PARTIAL** | API returns signals, but EA must poll API directly (not MT5 bridge) |
| **CHECK_OPEN_EXECUTED** | ❌ **FAIL** | EA doesn't poll API server (polls MT5 bridge instead) |
| **CHECK_CLOSE_EXECUTED** | ❌ **FAIL** | Open not executed |
| **FINAL_E2E_RESULT** | 🟡 **PARTIAL** | API dispatch works, EA integration gap remains |

---

## Root Cause Fixed

### ✅ Fixed: API Poll Endpoint

**Before:**
```python
@router.get("/signals/poll", response_model=APIResponse)
def poll_signals() -> APIResponse:
    return APIResponse(payload={"signals": [], ...})  # Hardcoded empty
```

**After:**
```python
@router.get("/signals/poll", response_model=APIResponse)
def poll_signals(token: str, db: Session = Depends(get_db)) -> APIResponse:
    # 1. Authenticate session via token
    # 2. Get account_login from session
    # 3. Query signals from DB
    # 4. Filter by target_account
    # 5. Mark as 'dispatched' to avoid duplicates
    # 6. Return signals to EA
```

### ✅ Fixed: Signal Deduplication

- Signals marked as `status: "dispatched"` after first poll
- Subsequent polls return empty array (no duplicate signals)
- Prevents EA from executing same signal multiple times

### ✅ Fixed: Account-Based Filtering

- Only returns signals where `target_account` matches authenticated account
- Global signals (no target_account) returned to all accounts
- Prevents signal leakage between accounts

---

## What Works Now

### API Server ✅

```bash
# First poll - returns signal
$ curl "http://localhost:8000/api/v1/signals/poll?token=cba11bbf-..."
{
  "signals": [{
    "signal_id": "TEST-OPEN-20260423-001-20260423155748",
    "symbol": "XAUUSD",
    "payload": {"action": "open", "side": "buy", "volume": 0.01, ...}
  }],
  "entries_enabled": true,
  "account_login": "60066926"
}

# Second poll - signal already dispatched
$ curl "http://localhost:8000/api/v1/signals/poll?token=cba11bbf-..."
{"signals": [], "entries_enabled": true, "account_login": "60066926"}
```

### Database ✅

- Signals stored with `status: "new"`
- After poll, updated to `status: "dispatched"`
- Deduplication working

---

## What Still Doesn't Work

### EA Polling ❌

**Current EA Behavior:**
- EA connects to MT5 bridge (port 8001)
- EA polls MT5 bridge for signals
- MT5 bridge doesn't have signal dispatch logic

**Required EA Change:**
- EA must poll API server at `http://api:8000/api/v1/signals/poll?token=xxx`
- EA must include session token in poll requests
- EA must process returned signals and execute trades

**Gap:**
```
[API Server] ✅ Returns signals
     ↓
     ❌ EA doesn't poll API (polls MT5 bridge instead)
     ↓
[MT5 Bridge] Only handles authentication, no signal dispatch
     ↓
[EA] Never receives signals
```

---

## Changed Files

| File | Change | Lines |
|------|--------|-------|
| `services/api_server/routers_client.py` | Fixed poll_signals endpoint | +80 |
| `SIGNAL_DISPATCH_HOTFIX_REPORT.md` | This report | NEW |

**Total:** 1 file modified (minimal hotfix as required)

---

## Risk Note

### ⚠️ No Trades Executed

- Signal successfully dispatched from API
- EA never received signal (polls wrong endpoint)
- No open positions, no financial risk

### ⚠️ EA Integration Required

To complete the E2E loop, EA must be modified to:

1. **Poll API Server:**
   ```
   GET http://api:8000/api/v1/signals/poll?token={session_token}
   ```

2. **Process Signals:**
   ```python
   for signal in response["signals"]:
       if signal["payload"]["action"] == "open":
           execute_trade(signal["payload"])
   ```

3. **Report Execution:**
   ```
   POST http://api:8000/api/v1/execution/report
   {"token": "...", "signal_id": "...", "status": "executed"}
   ```

**Estimated Effort:** 2-4 hours EA development

---

## Testing Evidence

### Test Signal Created
```
Signal ID: TEST-OPEN-20260423-001-20260423155748
Action: open
Symbol: XAUUSD
Side: buy
Volume: 0.01
Target: 60066926 (DEMO)
Status: dispatched (after poll)
```

### API Poll Test
```
Poll #1: ✅ Returned 1 signal (status: new → dispatched)
Poll #2: ✅ Returned 0 signals (already dispatched)
Poll #3: ✅ Returned 0 signals (deduplication working)
```

### MT5 Bridge Logs
```
mt5-1 | Apr 23 16:05:52 INFO SLAVE/8001: accepted ('127.0.0.1', 50960)
mt5-1 | Apr 23 16:05:52 INFO SLAVE/8001: welcome ('127.0.0.1', 50960)
mt5-1 | Apr 23 16:05:52 INFO SLAVE/8001: goodbye ('127.0.0.1', 50960)
```
**Pattern:** EA polling MT5 bridge every 30s (not API server)

---

## Summary

**FINAL_E2E_RESULT:** 🟡 **PARTIAL**

**What Was Accomplished:**
- ✅ API poll endpoint fixed
- ✅ Signal dispatch from DB working
- ✅ Account-based filtering working
- ✅ Deduplication working
- ✅ Demo account confirmed (60066926 @ TradeMaxGlobal-Demo)

**What's Remaining:**
- ❌ EA must poll API server (currently polls MT5 bridge)
- ❌ EA must process signals and execute trades
- ❌ EA must report execution status

**Next Step:** Modify EA to poll `http://api:8000/api/v1/signals/poll`

---

**Report Generated:** 2026-04-24 00:06 GMT+8  
**Hotfix Duration:** ~15 minutes  
**Files Modified:** 1 (routers_client.py)  
**Core Logic Changed:** 0 (only signal dispatch layer)

# Client MT5 EA Standardization Plan

**Date:** 2026-04-24 00:25 GMT+8  
**Type:** Architecture Design & Migration Plan  
**Scope:** Client Execution MT5 Only (VPS Signal Source MT5 Frozen)

---

## Executive Summary

This document defines the **long-term standardized architecture** for client MT5 EA execution, distinguishing it clearly from the VPS-based signal source MT5 system.

**Key Decision:** Client EA must use **official MQL5 WebRequest/HTTP** approach for signal reception, not proprietary bridge solutions.

---

## 1. System Boundary Definition

### ✅ VPS Signal Source MT5 (DO NOT TOUCH)

| Attribute | Value |
|-----------|-------|
| **Location** | VPS (172.19.0.69) |
| **Role** | AI trading system's market data & signal source |
| **Account** | 60082633 @ TradeMaxGlobal-Demo |
| **Status** | ✅ Production ready, frozen |
| **Components** | `mt5_http_provider.py`, Windows gateway |
| **Modifications** | ❌ PROHIBITED |

**This system is the "upstream" signal generator. It is complete and frozen.**

---

### ⚠️ Client Execution MT5 (STANDARDIZE THIS)

| Attribute | Value |
|-----------|-------|
| **Location** | Client's local computer |
| **Role** | Receive AI signals and execute trades |
| **Account** | Client's own MT5 account (demo/live) |
| **Status** | ⚠️ Needs standardization |
| **Components** | MQL5 EA, WebRequest, local MT5 terminal |
| **Modifications** | ✅ ALLOWED (standardization scope) |

**This system is the "downstream" signal executor. It must be standardized.**

---

## 2. Why Current Bridge Approach Is Not Long-Term Viable

### Current State (Temporary)

```
┌─────────────────┐     ┌──────────────┐     ┌──────────┐
│  AI Signal API  │ ──→ │  MT5 Bridge  │ ──→ │  Client  │
│  (VPS)          │     │  (port 8001) │     │  EA      │
└─────────────────┘     └──────────────┘     └──────────┘
   ✅ Working              ⚠️ Temporary         ⚠️ Incomplete
```

### Problems with Bridge Approach

| Issue | Impact | Severity |
|-------|--------|----------|
| **Non-standard protocol** | Requires custom bridge server, not MT5-native | HIGH |
| **Port forwarding complexity** | Client must expose/access port 8001 through firewall/NAT | HIGH |
| **Security concerns** | Direct TCP connection to bridge, no HTTPS encryption | CRITICAL |
| **Scalability limits** | One bridge instance per client, hard to manage at scale | MEDIUM |
| **Maintenance burden** | Custom protocol requires ongoing maintenance | MEDIUM |
| **Not MQL5-native** | Goes against MetaQuotes recommended practices | MEDIUM |
| **Commercial readiness** | Not suitable for multi-client commercial deployment | CRITICAL |

### Conclusion

**The bridge approach is a short-term testing solution, NOT a long-term commercial product architecture.**

---

## 3. Official Standard Path (Target Architecture)

### Target State (MQL5 WebRequest)

```
┌─────────────────┐                ┌──────────────────┐
│  AI Signal API  │  ←HTTPS/JSON→  │  MQL5 EA         │
│  (VPS)          │   WebRequest   │  (Client PC)     │
│  :8000          │                │  MT5 Terminal    │
└─────────────────┘                └──────────────────┘
   ✅ Production                       ✅ Official MQL5
   ✅ HTTPS ready                      ✅ WebRequest standard
   ✅ Multi-client                     ✅ Firewall-friendly
```

### Why This Is Better

| Benefit | Description |
|---------|-------------|
| **Official MQL5 standard** | Uses MetaQuotes' documented WebRequest function |
| **HTTPS security** | Encrypted communication, certificate validation |
| **Firewall-friendly** | Uses standard HTTP/HTTPS ports (80/443) |
| **Scalable** | One API serves unlimited clients |
| **Commercial-ready** | Suitable for multi-client commercial deployment |
| **Maintainable** | Standard HTTP/JSON, no custom protocol |
| **MT5-native** | EA runs inside MT5 terminal, no external bridge needed |

---

## 4. Client EA Target Architecture

### EA Responsibilities

1. **Authentication**
   - Call `POST /auth/activate` on startup
   - Cache session token
   - Refresh via `POST /auth/heartbeat` every 5 minutes

2. **Signal Polling**
   - Call `GET /signals/poll?token={session_token}` every 30-60 seconds
   - Filter signals by `target_account` matching local MT5 account
   - Skip already-processed signals (local deduplication)

3. **Signal Execution**
   - Parse signal payload (action, symbol, side, volume, SL, TP)
   - Execute trade via `OrderSend()` MQL5 function
   - Handle errors gracefully (retry, log, report)

4. **Execution Reporting**
   - Call `POST /execution/report` with signal_id and status
   - Include execution details (order ticket, fill price, timestamp)

5. **Local State Management**
   - Persist processed signal IDs (prevent duplicates)
   - Track open positions
   - Handle disconnections gracefully

### Minimal Signal API Contract

**Endpoint:** `GET /api/v1/signals/poll?token={session_token}`

**Response:**
```json
{
  "status": "ok",
  "payload": {
    "signals": [
      {
        "signal_id": "SIG-20260424-001",
        "symbol": "XAUUSD",
        "payload": {
          "action": "open",
          "side": "buy",
          "order_type": "market",
          "volume": 0.01,
          "sl": 2300.00,
          "tp": 2400.00,
          "target_account": "60066926",
          "test_id": "TEST-001"
        }
      }
    ],
    "entries_enabled": true,
    "protective_mode_only": false,
    "account_login": "60066926"
  }
}
```

**Endpoint:** `POST /api/v1/execution/report`

**Request:**
```json
{
  "token": "session-token-here",
  "signal_id": "SIG-20260424-001",
  "status": "executed",
  "payload": {
    "order_ticket": 123456789,
    "fill_price": 2350.50,
    "fill_time": "2026-04-24T00:30:00Z",
    "comment": "Executed via MQL5 EA"
  }
}
```

---

## 5. Signal State Flow

### States

```
new → dispatched → acknowledged → executing → executed
                                      ↓
                                   failed
```

| State | Meaning | Who Sets |
|-------|---------|----------|
| `new` | Signal created, not yet polled | API |
| `dispatched` | Returned to EA in poll response | API |
| `acknowledged` | EA received and validated signal | EA |
| `executing` | Order placement in progress | EA |
| `executed` | Order successfully filled | EA |
| `failed` | Execution failed (reason in payload) | EA |

### Deduplication & Idempotency

**API Side:**
- Mark signal as `dispatched` after first poll
- Don't return dispatched signals again

**EA Side:**
- Maintain local `processed_signals.csv` with signal_id list
- Skip signals already in local ledger
- Idempotent execution: check if position already exists before opening

---

## 6. Demo/Live Isolation

### Configuration-Based Isolation

```mql5
// EA Input Parameters
input string ApiBaseUrl = "https://api.example.com";  // Different for demo/live
input string LicenseKey = "";                          // Different license
input bool ShadowMode = true;                          // true = demo, false = live
```

### Server-Side Isolation

| Environment | API URL | Account Type | Risk Limits |
|-------------|---------|--------------|-------------|
| **Demo** | `https://api-demo.example.com` | Demo accounts only | Max 0.1 lot |
| **Staging** | `https://api-staging.example.com` | Demo accounts | Max 0.5 lot |
| **Live** | `https://api.example.com` | Live accounts | Per-client limits |

### EA Behavior by Mode

| Mode | Behavior |
|------|----------|
| `ShadowMode=true` | Log trades, don't execute (or execute 0.01 lot) |
| `ShadowMode=false` | Full execution with real money |

---

## 7. Minimal Migration Plan

### Phase 1: VPS Signal Source (Complete ✅)

- [x] `mt5_http_provider.py` working
- [x] Windows gateway connected
- [x] Signal injection working
- [x] API poll endpoint fixed
- [x] **Status:** FROZEN, DO NOT MODIFY

### Phase 2: Client EA Standardization (Current)

- [ ] Complete MQL5 EA implementation with WebRequest
- [ ] Implement authentication flow
- [ ] Implement signal polling
- [ ] Implement trade execution
- [ ] Implement execution reporting
- [ ] Implement local deduplication
- [ ] **Status:** IN PROGRESS

### Phase 3: Demo Account Integration

- [ ] Set up demo client MT5 account
- [ ] Configure EA with demo API endpoint
- [ ] Test end-to-end signal flow
- [ ] Verify trade execution in demo
- [ ] **Status:** NOT STARTED

### Phase 4: Paper Trading Validation

- [ ] Run 7-day paper trading test
- [ ] Monitor signal latency
- [ ] Monitor execution quality
- [ ] Verify no duplicate trades
- [ ] Collect performance metrics
- [ ] **Status:** NOT STARTED

### Phase 5: Commercial Readiness

- [ ] Multi-client stress test
- [ ] HTTPS certificate setup
- [ ] Rate limiting implementation
- [ ] Monitoring & alerting
- [ ] Documentation for clients
- [ ] **Status:** NOT STARTED

---

## 8. Code Changes Required

### Files to Create/Modify

| File | Action | Reason | Impact on VPS |
|------|--------|--------|---------------|
| `clients/mt5_ea/GoldAITraderEA.mq5` | **REWRITE** | Full MQL5 implementation with WebRequest | NONE ✅ |
| `clients/mt5_ea/README.md` | CREATE | EA setup instructions | NONE ✅ |
| `services/api_server/routers_client.py` | MINOR | Add execution report endpoint | NONE ✅ |
| `docs/CLIENT_EA_SETUP.md` | CREATE | Client deployment guide | NONE ✅ |

### VPS Signal Source Protection

**The following files are FROZEN and MUST NOT be modified:**

- `services/market_feed/mt5_http_provider.py`
- `services/market_feed/service.py`
- `services/market_feed/mt5_provider.py`
- Any file in `ai_orchestrator/`, `risk_manager/`, `signal_engine/`

---

## 9. Risks & Mitigations

### Risk 1: EA Implementation Complexity

**Risk:** MQL5 WebRequest implementation is more complex than bridge approach

**Mitigation:**
- Use MQL5 standard library (`WebRequest` function)
- Follow MetaQuotes documentation examples
- Start with shadow mode, verify before live

---

### Risk 2: Network Connectivity

**Risk:** Client MT5 may not have internet access or WebRequest may be blocked

**Mitigation:**
- Document required MT5 settings (`Tools → Options → Expert Advisors → Allow WebRequest`)
- Provide whitelist URLs for client firewall
- Test connectivity on EA startup

---

### Risk 3: Signal Latency

**Risk:** HTTP polling introduces latency vs direct bridge connection

**Mitigation:**
- Use 30-second polling interval (acceptable for swing trades)
- For high-frequency needs, consider WebSocket upgrade later
- Monitor and document actual latency in production

---

## 10. Rollback Plan

If standardization fails:

1. **Immediate Rollback:**
   - Revert EA to previous bridge-based version
   - No server-side changes needed (API is backward compatible)

2. **Partial Rollback:**
   - Keep API changes (poll endpoint is useful)
   - Revert EA to simpler version

3. **Full Rollback:**
   - Restore from git tag `freeze/go-paper-mt5-http-20260423`
   - All changes are isolated to `clients/` directory

---

## 11. Success Criteria

Client EA standardization is complete when:

- [ ] EA authenticates with API server
- [ ] EA polls signals every 30-60 seconds
- [ ] EA executes trades in local MT5 terminal
- [ ] EA reports execution status back to API
- [ ] No duplicate trades (deduplication working)
- [ ] Demo account test: signal → execution → report (full loop)
- [ ] 7-day paper trading: zero critical errors
- [ ] Documentation complete for client deployment

---

## 12. Next Steps

### Immediate (This Session)

1. ✅ Define system boundary (VPS vs Client)
2. ✅ Document why bridge is not long-term viable
3. ✅ Define official standard path (MQL5 WebRequest)
4. ✅ Create migration plan
5. ⏳ **Next:** Implement MQL5 EA with WebRequest

### After This Session

1. Complete MQL5 EA implementation
2. Test with demo account
3. Run paper trading validation
4. Prepare for commercial deployment

---

**Document Status:** ✅ COMPLETE  
**Next Action:** Implement MQL5 EA (Phase 2)  
**VPS Signal Source:** ✅ FROZEN (no changes)  
**Client EA:** ⚠️ NEEDS STANDARDIZATION

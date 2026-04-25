# Gold AI Trader EA - Demo Validation Plan

**Version:** 1.0  
**Date:** 2026-04-24  
**Purpose:** Systematic validation before live deployment

---

## Phase 1: Installation Validation (Day 1)

### Objective
Verify EA installs and connects correctly

### Steps

1. **Install EA**
   - [ ] Copy GoldAITraderEA.mq5 to Experts folder
   - [ ] Refresh Navigator in MT5
   - [ ] EA appears in list

2. **Configure WebRequest**
   - [ ] Tools → Options → Expert Advisors
   - [ ] WebRequest URL added: `https://api.example.com`
   - [ ] Checkbox enabled

3. **Attach to Chart**
   - [ ] Open XAUUSD chart
   - [ ] Attach EA
   - [ ] UI panel appears

4. **Verify Connection**
   - [ ] Status shows "Connected" (green)
   - [ ] HTTP Status shows 200
   - [ ] Last Poll timestamp updates

### Success Criteria
- ✅ EA installed without errors
- ✅ WebRequest configured
- ✅ UI panel visible
- ✅ Connection status green

---

## Phase 2: Shadow Mode Test (Days 1-3)

### Objective
Observe signal flow without execution

### Configuration
```
Inp_ShadowMode       = true
Inp_AllowTrading     = false
Inp_PollIntervalSec  = 30
```

### Daily Checks

**Day 1:**
- [ ] Status remains "Connected"
- [ ] Last Poll updates every 30 seconds
- [ ] No errors in Experts log
- [ ] UI panel stable (no flickering)

**Day 2:**
- [ ] Continue monitoring
- [ ] Check for any disconnections
- [ ] Verify HTTP status remains 200

**Day 3:**
- [ ] Wait for test signal from API
- [ ] Verify UI shows:
  - Signal ID populated
  - Action: "open" or "close"
  - Result: "shadow_skipped"
- [ ] Check Experts log:
  ```
  [GoldAI] SHADOW MODE: Would execute open buy 0.01 lots
  ```

### Success Criteria
- ✅ EA runs continuously for 72 hours
- ✅ No crashes or errors
- ✅ Signal polling works
- ✅ Shadow mode correctly skips execution
- ✅ UI panel remains stable

---

## Phase 3: Demo Execution Test (Days 4-10)

### Objective
Validate trade execution on demo account

### Configuration
```
Inp_ShadowMode       = false
Inp_AllowTrading     = false  ← Start disabled!
Inp_DefaultLotSize   = 0.01
```

### Days 4-5: Observe Mode

- [ ] Signals received
- [ ] UI shows Result: "trading_disabled"
- [ ] No trades executed
- [ ] Verify signal data correct

### Days 6-7: Enable Trading

**Update configuration:**
```
Inp_AllowTrading     = true
```

**Monitor:**
- [ ] Wait for open signal
- [ ] Verify UI shows Result: "executed"
- [ ] Position opens in MT5
- [ ] Position section shows:
  - Side (BUY/SELL)
  - Lots: 0.01
  - Entry price
  - P&L updating
- [ ] Check Experts log:
  ```
  [GoldAI] Order executed: ticket=123456789, price=2350.50
  ```

### Days 8-10: Close Signal Test

- [ ] Wait for close signal
- [ ] Verify position closes
- [ ] Check execution report sent to API
- [ ] Position section clears

### Success Criteria
- ✅ Trades execute correctly
- ✅ Position tracking accurate
- ✅ Close signals work
- ✅ No duplicate trades
- ✅ P&L calculation correct

---

## Phase 4: Stability Test (Days 11-17)

### Objective
Verify long-term stability

### Monitoring

**Daily:**
- [ ] EA still running
- [ ] No MT5 crashes
- [ ] Connection stable
- [ ] Signals processing correctly

**Metrics to Track:**

| Metric | Target | Actual |
|--------|--------|--------|
| Uptime | >99% | ___% |
| Signal latency | <60s | ___s |
| Execution success | 100% | ___% |
| Duplicate trades | 0 | ___ |

### Edge Case Tests

**Day 14: Network Interruption**
- [ ] Disconnect internet for 5 minutes
- [ ] Verify EA handles gracefully
- [ ] Reconnect
- [ ] Verify EA recovers automatically
- [ ] Check no duplicate signals executed

**Day 15: API Downtime**
- [ ] Simulate API unavailable
- [ ] Verify EA shows "Disconnected"
- [ ] Verify no errors/crashes
- [ ] Restore API
- [ ] Verify EA reconnects automatically

**Day 16: MT5 Restart**
- [ ] Restart MT5 terminal
- [ ] Verify EA auto-starts (if enabled)
- [ ] Verify state restored correctly
- [ ] Check processed signals file intact

### Success Criteria
- ✅ 7-day continuous operation
- ✅ Handles network issues gracefully
- ✅ Auto-recovers from disconnections
- ✅ No memory leaks or slowdowns
- ✅ State persists across restarts

---

## Phase 5: Pre-Live Checklist (Day 18)

### Final Validation

**Configuration Review:**
- [ ] API URL correct for live
- [ ] License key updated
- [ ] Lot size appropriate for account
- [ ] Stop loss/take profit set

**Account Verification:**
- [ ] Demo account balance sufficient
- [ ] Leverage appropriate
- [ ] Symbol available (XAUUSD)
- [ ] AutoTrading enabled

**Documentation:**
- [ ] All test results documented
- [ ] Issues logged and resolved
- [ ] Configuration backed up
- [ ] Support contact info available

**Sign-off:**
- [ ] Shadow mode: PASS
- [ ] Demo execution: PASS
- [ ] Stability test: PASS
- [ ] Edge cases: PASS
- [ ] Ready for live: YES / NO

---

## Issue Log Template

| Date | Issue | Severity | Resolution | Status |
|------|-------|----------|------------|--------|
| | | Critical/High/Medium/Low | | Open/Resolved |

**Example:**
| Date | Issue | Severity | Resolution | Status |
|------|-------|----------|------------|--------|
| 2026-04-24 | WebRequest not in whitelist | High | Added URL to MT5 options | Resolved |

---

## Go/No-Go Decision Matrix

### Must Pass All:

- [ ] 72-hour shadow mode without errors
- [ ] Successful demo trade execution
- [ ] Successful demo trade close
- [ ] 7-day stability test
- [ ] Network interruption recovery
- [ ] MT5 restart recovery
- [ ] No duplicate trades
- [ ] UI panel stable throughout

### If Any Fail:

**DO NOT PROCEED TO LIVE**

1. Document failure
2. Fix issue
3. Restart test phase from beginning
4. Re-validate all phases

---

## Contact & Support

**During Testing:**
- Monitor Experts log daily
- Check UI panel status
- Document any anomalies

**If Issues Occur:**
1. Screenshot UI panel
2. Export Experts log
3. Note timestamp of issue
4. Contact support with details

---

**Test Start Date:** ___________  
**Target Completion:** ___________  
**Actual Completion:** ___________  
**Final Result:** PASS / FAIL  
**Approved for Live:** YES / NO  

**Tester Signature:** ___________  
**Date:** ___________

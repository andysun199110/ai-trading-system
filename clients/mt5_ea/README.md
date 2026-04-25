# Gold AI Trader EA - Client Deployment Guide

**Version:** 2.0.0  
**Date:** 2026-04-24  
**Type:** Client-Side Execution EA (MQL5)

---

## Overview

This EA runs on the **client's local MT5 terminal** and executes trades based on signals from the AI Signal API.

**Key Features:**
- ✅ Official MQL5 WebRequest for signal polling
- ✅ Commercial-grade on-chart UI panel
- ✅ Shadow/Demo/Live mode support
- ✅ Automatic signal deduplication
- ✅ Position tracking & reporting

---

## Installation Steps

### Step 1: Copy EA File

1. Copy `GoldAITraderEA.mq5` to:
   ```
   C:\Users\<YourUsername>\AppData\Roaming\MetaQuotes\Terminal\<TerminalID>\MQL5\Experts\
   ```

2. Open MT5 terminal

3. In Navigator panel, right-click "Expert Advisors" → Refresh

4. You should see "GoldAITraderEA" in the list

---

### Step 2: Enable WebRequest (CRITICAL)

**MT5 must be configured to allow HTTP requests to the API server.**

1. In MT5, go to: **Tools → Options → Expert Advisors**

2. Check the box: ✅ **Allow WebRequest for listed URL:**

3. Click **Add** and enter your API URL:
   ```
   https://api.example.com
   ```
   
   **Important:** Add the domain only (not the full path):
   - ✅ Correct: `https://api.example.com`
   - ❌ Wrong: `https://api.example.com/api/v1/signals/poll`

4. Click **OK** to save

**Screenshot:**
```
┌──────────────────────────────────────────┐
│ Options - Expert Advisors                │
├──────────────────────────────────────────┤
│ ☑ Allow WebRequest for listed URL:       │
│                                          │
│  https://api.example.com           [Add] │
│                                    [Edit]│
│                                  [Delete]│
│                                          │
│                         [OK] [Cancel]    │
└──────────────────────────────────────────┘
```

---

### Step 3: Enable AutoTrading

1. In MT5 toolbar, click **AutoTrading** button (or press F4)
2. Ensure it shows **AutoTrading is enabled** (green icon)
3. Right-click chart → Expert Advisors → Allow Algorithmic Trading

---

### Step 4: Attach EA to Chart

1. Open chart for **XAUUSD** (Gold)
2. Drag "GoldAITraderEA" from Navigator onto the chart
3. Configure parameters (see below)
4. Click **OK**

You should see the UI panel appear on the chart.

---

## Configuration Parameters

### API Configuration

| Parameter | Description | Example |
|-----------|-------------|---------|
| `Inp_ApiBaseUrl` | AI Signal API base URL | `https://api.example.com/api/v1` |
| `Inp_LicenseKey` | Your license key | `YOUR-LICENSE-KEY-HERE` |
| `Inp_PollIntervalSec` | How often to poll for signals | `30` (seconds) |

### Account Settings

| Parameter | Description | Example |
|-----------|-------------|---------|
| `Inp_AccountServer` | Your MT5 server name | `TradeMaxGlobal-Demo` |
| `Inp_ShadowMode` | Shadow mode (no execution) | `true` for testing |
| `Inp_DefaultLotSize` | Default trade size | `0.01` (minimal) |

### Risk Management

| Parameter | Description | Example |
|-----------|-------------|---------|
| `Inp_StopLossPoints` | Stop loss in points | `500` |
| `Inp_TakeProfitPoints` | Take profit in points | `1000` |
| `Inp_AllowTrading` | Enable live trading | `false` (default: OFF) |

---

## Recommended Configuration by Environment

### Demo Testing (Recommended First)

```
Inp_ApiBaseUrl       = https://api-demo.example.com/api/v1
Inp_LicenseKey       = YOUR-DEMO-LICENSE
Inp_PollIntervalSec  = 30
Inp_ShadowMode       = false
Inp_DefaultLotSize   = 0.01
Inp_AllowTrading     = false  ← Start with false!
```

### Shadow Mode (Observe Only)

```
Inp_ShadowMode       = true   ← Will log but not execute
```

### Live Trading (After Validation)

```
Inp_ApiBaseUrl       = https://api.example.com/api/v1
Inp_LicenseKey       = YOUR-LIVE-LICENSE
Inp_ShadowMode       = false
Inp_DefaultLotSize   = 0.01   ← Start small!
Inp_AllowTrading     = true   ← Enable only after testing
```

---

## UI Panel Guide

The EA displays a commercial-grade panel on the chart with 4 sections:

### 1. CONNECTION Section

| Field | Meaning |
|-------|---------|
| **Status** | Connected / Disconnected |
| **Last Poll** | Timestamp of last successful poll |
| **HTTP Status** | HTTP response code (200 = OK) |
| **Mode** | SHADOW / DEMO / LIVE |

**Status Colors:**
- 🟢 Green = Connected / Success
- 🔴 Red = Disconnected / Error
- 🟠 Orange = Shadow Mode

### 2. LAST SIGNAL Section

| Field | Meaning |
|-------|---------|
| **Signal ID** | Unique identifier of last signal |
| **Action** | open / close |
| **Result** | executed / failed / shadow_skipped |

### 3. ACCOUNT Section

| Field | Meaning |
|-------|---------|
| **Account** | Your MT5 account number |
| **Server** | Broker/server name |
| **Symbol** | Current chart symbol |

### 4. POSITION Section

| Field | Meaning |
|-------|---------|
| **Side** | BUY / SELL (if position open) |
| **Lots** | Position size |
| **Entry** | Entry price |
| **Current** | Current market price |
| **P&L** | Floating profit/loss |
| **SL** | Stop loss level |
| **TP** | Take profit level |

---

## Testing Checklist

### Pre-Flight Checks

- [ ] WebRequest URL added to MT5 whitelist
- [ ] AutoTrading enabled (green icon)
- [ ] EA attached to XAUUSD chart
- [ ] UI panel visible on chart
- [ ] Status shows "Connected"

### Shadow Mode Test (Recommended First)

1. Set `Inp_ShadowMode = true`
2. Wait for signal from API
3. Verify UI shows:
   - [ ] Signal ID populated
   - [ ] Action shows "open" or "close"
   - [ ] Result shows "shadow_skipped"
4. Check Experts log for:
   ```
   [GoldAI] SHADOW MODE: Would execute open buy 0.01 lots
   ```

### Demo Account Test

1. Set `Inp_ShadowMode = false`
2. Set `Inp_AllowTrading = false` (still safe)
3. Wait for signal
4. Verify UI shows:
   - [ ] Result shows "trading_disabled"
5. Check Experts log for:
   ```
   [GoldAI] Trading disabled: open buy 0.01 lots
   ```

### Full Execution Test (Demo Only)

⚠️ **Only after shadow mode validated**

1. Set `Inp_AllowTrading = true`
2. Ensure demo account with sufficient balance
3. Wait for signal
4. Verify:
   - [ ] UI shows Result: "executed"
   - [ ] Position section shows open trade
   - [ ] P&L updating in real-time
5. Check Experts log for:
   ```
   [GoldAI] Order executed: ticket=123456789, price=2350.50
   ```

---

## Troubleshooting

### "WebRequest not allowed" Error

**Problem:** MT5 blocking HTTP requests

**Solution:**
1. Tools → Options → Expert Advisors
2. Add API domain to whitelist
3. Restart MT5

### "Disconnected" Status

**Problem:** Cannot reach API server

**Check:**
1. Internet connection
2. API URL correct (https, not http)
3. Firewall not blocking MT5
4. API server running

### No Signals Received

**Problem:** Signals not appearing

**Check:**
1. Session token valid (check API server logs)
2. Account login matches signal target_account
3. Signal status not already "dispatched"
4. Poll interval not too long (try 30s)

### EA Not Executing Trades

**Problem:** Signals received but no trades

**Check:**
1. `Inp_ShadowMode = false`
2. `Inp_AllowTrading = true`
3. AutoTrading enabled (green icon)
4. Sufficient margin in account
5. Symbol matches (XAUUSD)

---

## Log Files

### EA Logs

View in MT5: **Toolbox → Experts** tab

Look for entries like:
```
[GoldAI] Initializing EA v2.0.0
[GoldAI] API: https://api.example.com/api/v1
[GoldAI] Mode: SHADOW
[GoldAI] Auth successful
[GoldAI] Poll successful
[GoldAI] Order executed: ticket=123456789
```

### Processed Signals Log

File: `MQL5\Files\GoldAI_processed_signals.csv`

Contains history of processed signals to prevent duplicates.

---

## Rollback Instructions

If you need to revert to previous EA version:

1. Remove EA from chart (right-click → Remove)
2. Delete `GoldAITraderEA.mq5` from Experts folder
3. Copy old EA file to Experts folder
4. Refresh Navigator
5. Re-attach old EA to chart

---

## Support

For issues or questions:

1. Check Experts log first
2. Verify WebRequest configuration
3. Test in Shadow Mode first
4. Contact support with:
   - MT5 build number
   - EA version
   - Experts log excerpt
   - Screenshot of UI panel

---

## Safety Reminders

⚠️ **Always start with Shadow Mode**
- Observe signals without execution
- Verify connectivity
- Check UI panel working

⚠️ **Demo before Live**
- Test thoroughly on demo account
- Minimum 7 days demo validation
- No issues before going live

⚠️ **Start with minimal lot size**
- Default: 0.01 lots
- Increase only after validation
- Never risk more than you can afford to lose

⚠️ **Monitor regularly**
- Check UI panel daily
- Review Experts log
- Verify positions match expectations

---

**Document Version:** 1.0  
**Last Updated:** 2026-04-24  
**EA Version:** 2.0.0

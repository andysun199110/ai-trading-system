---
name: client-ea-ui-spec
description: Specification and guardrails for rewriting the client-side MT5 execution EA using official MQL5 WebRequest, with a commercial-grade on-chart UI panel showing AI interaction status and position info. Use for any task involving clients/mt5_ea/GoldAITraderEA.mq5, client execution flow, UI panel, or demo/paper validation for client-side MT5.
---

# Client EA UI Spec

## Scope

This skill applies only to the **client-side execution EA** on the customer's MT5 terminal.

Two MT5 roles exist in this system:

1. **VPS MT5 (signal/data source)**
   - Role: AI signal source / market data side
   - Status: already working and frozen
   - MUST NOT be modified

2. **Client PC MT5 (execution side)**
   - Role: receive strategy signals and execute trades locally
   - This is the only MT5 side that should be changed in tasks using this skill

## Non-Negotiable Architecture Rules

- Use **official MQL5 standard path only**
- Client EA must use **MQL5 WebRequest** for pulling signals / posting acknowledgements
- Do NOT design the long-term client execution solution around a private bridge as the final architecture
- Do NOT modify the frozen VPS signal-source MT5 chain
- Do NOT modify:
  - ai_orchestrator
  - risk_manager
  - signal_engine
  unless the task explicitly authorizes a minimal compatibility patch

## Main File Target

Primary file:
- `clients/mt5_ea/GoldAITraderEA.mq5`

Optional supporting files may be added only if clearly necessary and tightly scoped.

## Required Client EA Capabilities

### 1) Communication
The EA must:
- use `WebRequest`
- support configurable API base URL
- support configurable poll interval
- support configurable auth token/session token
- handle HTTP status codes and network failures cleanly
- avoid printing secrets in logs

### 2) Signal Pull
The EA must support:
- pull of signals addressed to the current account/client
- `open` and `close` actions
- unique `signal_id` / `test_id`
- idempotency / duplicate protection
- explicit handling of empty signal responses

### 3) Local Execution
The EA must:
- execute orders locally inside MT5
- track receive / execute / fail lifecycle
- support safe minimal-size demo execution
- prefer safe close behavior when receiving close instructions

### 4) UI / On-Chart Panel
The EA must show a clean, commercial-looking chart panel with at least:

#### AI connectivity / interaction section
- EA status
- API connection status
- last successful poll time
- last HTTP result / error summary
- current run mode (`shadow`, `demo`, `live`)
- last signal ID
- last signal action
- last execution result

#### Account / terminal section
- account login
- broker/server
- symbol currently managed
- autotrading status

#### Position section
- current position side
- lot size
- entry price
- current price
- floating PnL
- stop loss / take profit
- magic/comment if available

### 5) UI Style Requirements
The chart UI must be:
- visually clean and commercial-grade
- compact but readable
- aligned consistently
- color-coded by status
- non-intrusive to price action
- stable on refresh (avoid flicker)
- easy to understand for a non-technical customer

Prefer:
- one structured panel block
- headers + value rows
- connection status badges
- execution result badges

Avoid:
- cluttered labels everywhere
- excessive debug text on chart
- overlapping the core candle area
- flashing/redrawing the whole chart unnecessarily

## Safety Rules

- Default testing target is **demo only**
- Default execution lot should be minimal
- Support `shadow_mode=true` where signals are pulled and displayed but not executed
- Never assume live trading should be enabled by default
- If demo/live status is uncertain, prefer non-execution behavior

## Delivery Standard

When working under this skill, the agent should aim to produce:

1. a rewritten or refactored `GoldAITraderEA.mq5`
2. a clear list of input parameters
3. a client deployment guide
4. a demo validation checklist
5. a rollback note if any existing EA behavior changes materially

## Change Discipline

Prefer minimal, cohesive changes.

Do NOT:
- expand scope into unrelated backend work
- redesign the frozen VPS signal-source path
- add speculative architecture that is not needed for client EA execution
- create temporary hacks as the final commercial solution

## Expected Output Shape

For tasks using this skill, prefer final outputs that clearly state:
- what changed in the EA
- which client-side settings are required in MT5
- how to enable WebRequest in MT5
- how to run shadow/demo validation
- what remains before commercial readiness

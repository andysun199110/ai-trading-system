# Stage-2 Intelligence Architecture

## Core rules
- XAUUSD only, MT5 only, no futures.
- Per-minute loop only for lightweight position supervision.
- Deep AI invokes only at key nodes: candidate review, event windows, position state change, weekly review.

## Implemented modules
- `market_feed`: closed-bar safe feed snapshots.
- `market_structure`: H1 regime + M15 setup + swing/pivot/zone scoring.
- `event_calendar`: T-60/T-15/T-5/T+1/T+5/T+15 windows and block logic.
- `etf_bias`: GLD/IAU/SGOL daily and 4H light refresh bias output.
- `signal_engine`: guard pipeline + candidate creation + optional AI review.
- `risk_manager`: initial stop, TP, breakeven, trailing.
- `position_supervisor`: 1-minute lightweight supervision + event/state-change AI escalation.
- `review_optimizer`: weekly analysis and proposal-only outputs.

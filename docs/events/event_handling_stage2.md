# Event Handling Stage 2

Major-event windows:
- T-60
- T-15
- T-5
- T+1
- T+5
- T+15

Behavior:
- Before hard-impact event: block/restrict new entries.
- During window with open positions: invoke AI supervisor.
- After release: require stabilization before entry resumption.

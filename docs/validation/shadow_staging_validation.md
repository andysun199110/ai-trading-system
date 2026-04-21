# Shadow and Staging Validation

## Shadow mode
- Run full signal generation and supervision pipeline.
- Do not place broker orders.
- Persist all decisions with strategy/model/config versions.

## Staging mode
- Run end-to-end with isolated staging credentials and endpoints.
- Validate execution flow, duplicate prevention, and reconciliation.

## Validation report content
- AI response latency
- auth/session health
- signal generation counts
- blocked signal reasons
- order execution event flow
- duplicate prevention checks

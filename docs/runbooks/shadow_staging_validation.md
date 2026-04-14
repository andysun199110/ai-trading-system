# Shadow and Staging Validation

- Use `ValidationReporter` outputs for:
  - AI response latency
  - auth/session health
  - signal generation counts
  - blocked reasons
  - order execution flow
  - duplicate prevention checks
- Shadow mode: no live execution side effects.
- Staging mode: full pipeline with deployment candidate and report review.

# AI Invocation Policy (Stage 2)

Deep AI invocations are restricted to key nodes:
- candidate signal review (`candidate_signal_reviewer`)
- major event windows (`event_analyst`)
- important position state changes (`position_supervisor_ai`)
- weekend review (`weekly_review_ai`)

## Contract
All AI modules return strict JSON with:
- `decision`
- `confidence`
- `reasons[]`
- `risk_notes[]`
- `action`
- `model_version`
- `prompt_version`

No minute-by-minute full market deep re-analysis is allowed.

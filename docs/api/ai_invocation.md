# AI Invocation Contract

All AI modules must return strict JSON schema:
- decision
- confidence
- reasons[]
- risk_notes[]
- action
- model_version
- prompt_version

Modules:
- candidate_signal_reviewer
- event_analyst
- position_supervisor_ai
- weekly_review_ai

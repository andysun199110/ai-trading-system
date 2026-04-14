from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import mean

from services.ai_orchestrator.service import AIOrchestratorService


@dataclass
class TradeOutcome:
    pnl_r: float
    regime: str
    setup: str
    event_tag: str
    etf_bias: str


@dataclass
class WeeklyReviewOutput:
    summary: str
    optimization_proposals: list[dict]
    next_week_posture: str
    generated_at: datetime
    auto_deploy_allowed: bool


class ReviewOptimizerService:
    def __init__(self) -> None:
        self.ai = AIOrchestratorService()

    def weekly_review(self, outcomes: list[TradeOutcome]) -> WeeklyReviewOutput:
        avg_r = mean([o.pnl_r for o in outcomes]) if outcomes else 0.0
        by_regime: dict[str, float] = {}
        for regime in {o.regime for o in outcomes}:
            vals = [o.pnl_r for o in outcomes if o.regime == regime]
            by_regime[regime] = round(mean(vals), 3) if vals else 0.0
        ai, _ = self.ai.run(
            "weekly_review_ai",
            {
                "confidence_hint": 0.62,
                "reasons": [f"avg_r={avg_r:.2f}", f"regime_perf={by_regime}"],
                "risk_notes": ["proposals must be manually approved"],
                "action": "proposal_only",
            },
        )
        summary = f"Weekly avg R={avg_r:.2f}; regime split={by_regime}; ai_decision={ai.decision}"
        proposals = [
            {"type": "risk_tuning", "proposal": "reduce rr from 1.5 to 1.4 in range regime", "requires_manual_approval": True},
            {"type": "event_filter", "proposal": "increase pre-event block from T-15 to T-30 for high CPI", "requires_manual_approval": True},
        ]
        posture = "cautious" if avg_r < 0 else "balanced_growth"
        return WeeklyReviewOutput(
            summary=summary,
            optimization_proposals=proposals,
            next_week_posture=posture,
            generated_at=datetime.utcnow(),
            auto_deploy_allowed=False,
        )

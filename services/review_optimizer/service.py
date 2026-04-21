from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from services.ai_orchestrator.service import Service as AIService


@dataclass
class ServiceResult:
    status: str
    payload: dict[str, Any]


class Service:
    """Weekly post-close review. Generates proposals only; never live auto-deploy."""

    def run(self, payload: dict[str, Any] | None = None) -> ServiceResult:
        data = payload or {}
        trades = data.get("trades", [])
        by_regime: dict[str, list[float]] = defaultdict(list)
        by_setup: dict[str, list[float]] = defaultdict(list)
        event_pnl = 0.0

        for t in trades:
            pnl = float(t.get("pnl_r", 0.0))
            by_regime[t.get("regime", "unknown")].append(pnl)
            by_setup[t.get("setup", "unknown")].append(pnl)
            if t.get("during_event"):
                event_pnl += pnl

        regime_perf = {k: round(sum(v) / len(v), 3) for k, v in by_regime.items()}
        setup_perf = {k: round(sum(v) / len(v), 3) for k, v in by_setup.items()}
        ai = AIService().run(
            {
                "module": "weekly_review_ai",
                "context": {
                    "regime_perf": regime_perf,
                    "setup_perf": setup_perf,
                    "event_pnl": event_pnl,
                    "etf_bias_changes": data.get("etf_bias_changes", []),
                },
            }
        ).payload

        proposals = [
            {
                "proposal_id": "opt_1",
                "type": "risk_tuning",
                "details": "reduce risk 10% during hard-event week",
                "requires_manual_approval": True,
                "auto_deploy": False,
            }
        ]

        return ServiceResult(
            status="ok",
            payload={
                "review_summary": {
                    "trade_count": len(trades),
                    "performance_by_regime": regime_perf,
                    "performance_by_setup": setup_perf,
                    "event_impacts": {"event_pnl_r": round(event_pnl, 3)},
                    "etf_bias_changes": data.get("etf_bias_changes", []),
                },
                "optimization_proposals": proposals,
                "next_week_posture_recommendation": ai["response"],
                "live_config_modified": False,
            },
        )

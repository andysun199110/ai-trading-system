from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.ai_orchestrator.service import Service as AIService
from services.risk_manager.service import Service as RiskService


@dataclass
class ServiceResult:
    status: str
    payload: dict[str, Any]


class Service:
    """Every-minute lightweight supervision + deep AI on state changes or event windows."""

    def run(self, payload: dict[str, Any] | None = None) -> ServiceResult:
        data = payload or {}
        pos = data.get("position", {})
        risk = RiskService()
        actions: list[dict[str, Any]] = []

        be = risk.breakeven_action(
            {
                "entry": pos["entry"],
                "side": pos["side"],
                "current_price": pos["current_price"],
                "initial_sl": pos["initial_sl"],
                "breakeven_trigger_r": data.get("breakeven_trigger_r", 0.8),
                "fee_buffer": data.get("fee_buffer", 0.0),
            }
        )
        if be["move_to_breakeven"]:
            actions.append({"type": "breakeven", **be})

        trail = risk.trailing_action(
            {
                "side": pos["side"],
                "current_price": pos["current_price"],
                "structure_level": data.get("structure_trail_level"),
                "atr": data.get("atr", 2.0),
                "trail_atr_mult": data.get("trail_atr_mult", 1.0),
            }
        )
        actions.append({"type": "trailing", **trail})

        should_invoke_ai = data.get("event_window_active", False) or data.get("state_change", False)
        ai_payload = None
        if should_invoke_ai:
            ai_payload = AIService().run(
                {
                    "module": "position_supervisor_ai",
                    "context": {"state_change": data.get("state_change", False), "position": pos},
                }
            ).payload

        return ServiceResult(
            status="ok",
            payload={
                "cadence": "1m_lightweight",
                "actions": actions,
                "deep_ai_invoked": should_invoke_ai,
                "ai_payload": ai_payload,
                "no_time_stop_enforced": True,
            },
        )

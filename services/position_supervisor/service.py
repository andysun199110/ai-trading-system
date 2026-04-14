from __future__ import annotations

from dataclasses import dataclass

from services.ai_orchestrator.service import AIOrchestratorService
from services.event_calendar.service import EventWindowState
from services.risk_manager.service import RiskManagerService
from shared.schemas.trading import Side


@dataclass
class PositionState:
    position_id: str
    side: Side
    entry: float
    sl: float
    tp: float
    current_price: float
    protected_mode: bool


@dataclass
class SupervisorDecision:
    action: str
    new_sl: float | None
    reason: str
    used_ai: bool


class PositionSupervisorService:
    def __init__(self) -> None:
        self.risk = RiskManagerService()
        self.ai = AIOrchestratorService()

    def supervise_minute(self, pos: PositionState, atr_value: float, structure_level: float | None = None) -> SupervisorDecision:
        if self.risk.should_breakeven(pos.entry, pos.sl, pos.current_price, pos.side):
            be = self.risk.breakeven_stop(pos.entry, pos.side)
            return SupervisorDecision(action="move_to_breakeven", new_sl=be, reason="0.8R threshold reached", used_ai=False)
        tr = self.risk.trailing_stop(pos.side, structure_level=structure_level, atr_value=atr_value, last_price=pos.current_price)
        better = tr > pos.sl if pos.side == Side.BUY else tr < pos.sl
        if better:
            return SupervisorDecision(action="trail_stop", new_sl=tr, reason="structure/atr trailing", used_ai=False)
        return SupervisorDecision(action="hold", new_sl=None, reason="no_lightweight_adjustment", used_ai=False)

    def supervise_event_or_state_change(self, pos: PositionState, event_state: EventWindowState) -> SupervisorDecision:
        review, _ = self.ai.run(
            "position_supervisor_ai",
            {
                "confidence_hint": 0.58,
                "reasons": [f"event phase {event_state.phase}", "position state changed"],
                "risk_notes": ["possible spread expansion around news"],
                "action": "tighten_risk",
            },
        )
        if review.decision == "approve":
            return SupervisorDecision(action=review.action, new_sl=None, reason="ai_event_supervision", used_ai=True)
        return SupervisorDecision(action="hold", new_sl=None, reason="ai_declined_change", used_ai=True)

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4

from services.ai_orchestrator.service import AIOrchestratorService
from services.event_calendar.service import EventWindowState
from services.market_feed.service import FeedSnapshot, MarketFeedService
from services.market_structure.service import MarketStructureService
from services.risk_manager.service import RiskManagerService
from shared.config.settings import get_settings
from shared.constants.domain import SYMBOL_XAUUSD
from shared.schemas.trading import Side, SignalCandidate
from shared.utils.indicators import atr


@dataclass
class SignalDecision:
    candidate: SignalCandidate | None
    blocked_reason: str | None
    decision_path: list[str]


class SignalEngineService:
    def __init__(self) -> None:
        self.feed = MarketFeedService()
        self.structure = MarketStructureService()
        self.risk = RiskManagerService()
        self.ai = AIOrchestratorService()
        self.settings = get_settings()

    def _m5_trigger(self, m5: FeedSnapshot) -> tuple[bool, str, Side]:
        b1 = m5.bars[-3]
        b2 = m5.bars[-2]  # closed bar only
        bullish_engulf = b2.close > b2.open and b2.close > b1.high
        bearish_engulf = b2.close < b2.open and b2.close < b1.low
        if bullish_engulf:
            return True, "bullish_engulf_closed_bar", Side.BUY
        if bearish_engulf:
            return True, "bearish_engulf_closed_bar", Side.SELL
        return False, "no_trigger", Side.BUY

    def generate_candidate(
        self,
        h1_payload: list[dict],
        m15_payload: list[dict],
        m5_payload: list[dict],
        spread: float,
        event_state: EventWindowState,
        kill_switch: bool,
        ai_review_required: bool = True,
    ) -> SignalDecision:
        h1 = self.feed.from_payload(SYMBOL_XAUUSD, "H1", h1_payload)
        m15 = self.feed.from_payload(SYMBOL_XAUUSD, "M15", m15_payload)
        m5 = self.feed.from_payload(SYMBOL_XAUUSD, "M5", m5_payload)

        decision_path: list[str] = []
        structure_state = self.structure.evaluate(h1.bars, m15.bars)
        m15_setup = self.structure.m15_setup(m15.bars, structure_state.zones)
        trigger_ok, trigger_type, side = self._m5_trigger(m5)

        if kill_switch:
            return SignalDecision(None, "kill_switch_active", [*decision_path, "kill_switch"])
        if event_state.block_new_entries:
            return SignalDecision(None, "event_block_active", [*decision_path, "event_block"])
        if spread > 1.2:
            return SignalDecision(None, "spread_guard_failed", [*decision_path, "spread_guard"])
        if structure_state.regime.value == "range":
            return SignalDecision(None, "h1_regime_not_supported", [*decision_path, "h1_range"])
        if not m15_setup["setup_ok"]:
            return SignalDecision(None, "m15_setup_failed", [*decision_path, "m15_setup_failed"])
        if not trigger_ok:
            return SignalDecision(None, "m5_trigger_missing", [*decision_path, "m5_no_trigger"])

        entry = m5.bars[-2].close
        atr_val = atr([b.high for b in m15.bars], [b.low for b in m15.bars], [b.close for b in m15.bars])
        plan = self.risk.build_plan(entry=entry, side=side, atr_value=atr_val)
        zone = structure_state.zones[0] if structure_state.zones else None
        candidate = SignalCandidate(
            signal_id=f"sig-{uuid4().hex[:12]}",
            side=side,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=20),
            strategy_version=self.settings.strategy_version,
            config_version=self.settings.config_version,
            h1_state=structure_state.context,
            m15_state=str(m15_setup["state"]),
            m5_trigger_type=trigger_type,
            zone_reference=zone.zone_id if zone else "none",
            initial_sl=plan.initial_sl,
            tp=plan.tp,
            risk_mode=plan.risk_mode,
            rationale_summary="H1+M15+M5 aligned with spread/event/kill guards",
            ai_review_required=ai_review_required,
            ai_review_result="pending" if ai_review_required else "skipped",
            event_status=event_state.phase,
        )
        decision_path.extend(["h1_pass", "m15_pass", "m5_pass", "risk_plan_built"])

        if ai_review_required:
            review, _ = self.ai.run(
                "candidate_signal_reviewer",
                {
                    "confidence_hint": 0.68,
                    "reasons": ["multi-timeframe alignment", "spread guard pass", "event clear"],
                    "risk_notes": ["watch post-event volatility"],
                    "action": "approve_signal",
                },
            )
            candidate.ai_review_result = review.decision
            decision_path.append(f"ai_{review.decision}")
            if review.decision != "approve":
                return SignalDecision(None, "ai_blocked", decision_path)

        return SignalDecision(candidate=candidate, blocked_reason=None, decision_path=decision_path)

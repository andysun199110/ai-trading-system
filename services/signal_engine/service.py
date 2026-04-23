from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from services.ai_orchestrator.service import Service as AIOrchestratorService
from services.risk_manager.service import Service as RiskService
from shared.constants.domain import SYMBOL_XAUUSD


@dataclass
class ServiceResult:
    status: str
    payload: dict[str, Any]


class Service:
    """Builds XAUUSD entry candidates and optionally performs AI gate review."""

    def run(self, payload: dict[str, Any] | None = None) -> ServiceResult:
        data = payload or {}
        symbol = data.get("symbol", SYMBOL_XAUUSD)
        if symbol != SYMBOL_XAUUSD:
            return ServiceResult(status="blocked", payload={"reason": "symbol_not_allowed"})

        checks = {
            "h1": data.get("h1_regime_ok", False),
            "m15": data.get("m15_setup_ok", False),
            "m5": data.get("m5_trigger_ok", False),
            "spread": data.get("spread_ok", False),
            "event": not data.get("event_block_active", False),
            "kill": not data.get("kill_switch", False),
        }
        failed = [k for k, v in checks.items() if not v]
        if failed:
            return ServiceResult(status="blocked", payload={"blocked_reasons": failed})

        risk = RiskService().run(
            {
                "entry": data["entry"],
                "side": data["side"],
                "atr": data.get("atr", 2.0),
                "structure_sl": data.get("structure_sl"),
                "rr": data.get("rr", 1.5),
                "risk_mode": data.get("risk_mode", "balanced"),
            }
        ).payload

        signal = {
            "signal_id": f"sig_{uuid4().hex[:12]}",
            "symbol": symbol,
            "side": data["side"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=data.get("expires_minutes", 20))).isoformat(),
            "strategy_version": data.get("strategy_version", "stage2"),
            "config_version": data.get("config_version", "2026.04.stage2"),
            "H1_state": data.get("H1_state", {}),
            "M15_state": data.get("M15_state", {}),
            "M5_trigger_type": data.get("M5_trigger_type", "closed_bar_break"),
            "zone_reference": data.get("zone_reference", "M15_1"),
            "initial_sl": risk["initial_sl"],
            "tp": risk["tp"],
            "risk_mode": risk["risk_mode"],
            "rationale_summary": data.get("rationale_summary", "regime+setup+trigger aligned"),
            "ai_review_required": data.get("ai_review_required", True),
            "event_status": data.get("event_status", "clear"),
        }

        ai_result = {"decision": "skipped", "action": "none"}
        if signal["ai_review_required"]:
            ai_out = AIOrchestratorService().run({"module": "candidate_signal_reviewer", "context": signal}).payload
            ai_result = ai_out["response"]
            if ai_result["decision"] not in {"approve", "adjust"}:
                return ServiceResult(status="blocked", payload={"blocked_reasons": ["ai_review"], "ai_review_result": ai_result})
        signal["ai_review_result"] = ai_result
        return ServiceResult(status="approved", payload=signal)

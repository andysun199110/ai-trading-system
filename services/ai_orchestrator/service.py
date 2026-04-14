from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any


REQUIRED_FIELDS = {"decision", "confidence", "reasons", "risk_notes", "action", "model_version", "prompt_version"}


@dataclass
class ServiceResult:
    status: str
    payload: dict[str, Any]


class Service:
    """Routes key-node AI calls and enforces strict JSON contract."""

    def run(self, payload: dict[str, Any] | None = None) -> ServiceResult:
        data = payload or {}
        module = data.get("module", "candidate_signal_reviewer")
        context = data.get("context", {})

        if module not in {"candidate_signal_reviewer", "event_analyst", "position_supervisor_ai", "weekly_review_ai"}:
            return ServiceResult(status="blocked", payload={"reason": "unsupported_module", "module": module})

        start = perf_counter()
        response = self._mock_model(module, context)
        latency_ms = round((perf_counter() - start) * 1000, 3)
        valid = self.validate_contract(response)

        return ServiceResult(
            status="ok" if valid else "contract_error",
            payload={
                "module": module,
                "response": response,
                "latency_ms": latency_ms,
                "valid_contract": valid,
            },
        )

    def validate_contract(self, output: dict[str, Any]) -> bool:
        if set(output.keys()) != REQUIRED_FIELDS:
            return False
        if not isinstance(output["reasons"], list) or not isinstance(output["risk_notes"], list):
            return False
        return isinstance(output["confidence"], (float, int))

    def _mock_model(self, module: str, context: dict[str, Any]) -> dict[str, Any]:
        decision = "approve"
        action = "proceed"
        if module == "event_analyst" and context.get("event_block_active"):
            decision, action = "restrict", "block_entries"
        if module == "position_supervisor_ai" and context.get("state_change"):
            decision, action = "adjust", "tighten_risk"
        return {
            "decision": decision,
            "confidence": 0.74,
            "reasons": [f"module={module}", "contract_strict_json"],
            "risk_notes": ["no_minutely_deep_scan", "xauusd_only"],
            "action": action,
            "model_version": context.get("model_version", "ai-stage2-v1"),
            "prompt_version": context.get("prompt_version", "p-stage2-v1"),
        }

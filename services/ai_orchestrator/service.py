from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from services.ai_orchestrator.provider import get_provider

REQUIRED_FIELDS = {"decision", "confidence", "reasons", "risk_notes", "action", "model_version", "prompt_version"}


@dataclass
class ServiceResult:
    status: str
    payload: dict[str, Any]


class Service:
    """Routes AI calls through configured provider with strict JSON contract enforcement."""

    def run(self, payload: dict[str, Any] | None = None) -> ServiceResult:
        data = payload or {}
        module = data.get("module", "candidate_signal_reviewer")
        context = data.get("context", {})

        if module not in {"candidate_signal_reviewer", "event_analyst", "position_supervisor_ai", "weekly_review_ai"}:
            return ServiceResult(status="blocked", payload={"reason": "unsupported_module", "module": module})

        start = perf_counter()
        
        try:
            provider = get_provider()
            response = provider.generate(module, context)
            latency_ms = round((perf_counter() - start) * 1000, 3)
            
            return ServiceResult(
                status="ok" if response.confidence >= 0 else "contract_error",
                payload={
                    "module": module,
                    "response": {
                        "decision": response.decision,
                        "confidence": response.confidence,
                        "reasons": response.reasons,
                        "risk_notes": response.risk_notes,
                        "action": response.action,
                        "model_version": response.model_version,
                        "prompt_version": response.prompt_version,
                    },
                    "latency_ms": latency_ms,
                    "valid_contract": True,
                    "provider": response.provider,
                },
            )
        except Exception as e:
            latency_ms = round((perf_counter() - start) * 1000, 3)
            return ServiceResult(
                status="error",
                payload={
                    "module": module,
                    "error": str(e),
                    "latency_ms": latency_ms,
                    "provider": "unknown",
                },
            )

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from time import perf_counter
from typing import Any

from pydantic import ValidationError

from shared.schemas.trading import AIReviewResponse


@dataclass
class AIInvocationMetric:
    module: str
    latency_ms: float
    ok: bool


class _BaseAIModule:
    module_name = "base"
    model_version = "gpt-stage2-v1"
    prompt_version = "p1"

    def infer(self, context: dict[str, Any]) -> AIReviewResponse:
        decision = "approve" if context.get("confidence_hint", 0.5) >= 0.5 else "block"
        response = {
            "decision": decision,
            "confidence": float(context.get("confidence_hint", 0.6)),
            "reasons": context.get("reasons", [f"{self.module_name} default reasoning"]),
            "risk_notes": context.get("risk_notes", []),
            "action": context.get("action", "hold" if decision == "block" else "execute"),
            "model_version": self.model_version,
            "prompt_version": self.prompt_version,
        }
        return self.parse_strict_json(json.dumps(response))

    def parse_strict_json(self, text: str) -> AIReviewResponse:
        try:
            payload = json.loads(text)
            return AIReviewResponse.model_validate(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ValueError(f"invalid_ai_json:{self.module_name}") from exc


class CandidateSignalReviewer(_BaseAIModule):
    module_name = "candidate_signal_reviewer"


class EventAnalyst(_BaseAIModule):
    module_name = "event_analyst"


class PositionSupervisorAI(_BaseAIModule):
    module_name = "position_supervisor_ai"


class WeeklyReviewAI(_BaseAIModule):
    module_name = "weekly_review_ai"


class AIOrchestratorService:
    def __init__(self) -> None:
        self.modules = {
            "candidate_signal_reviewer": CandidateSignalReviewer(),
            "event_analyst": EventAnalyst(),
            "position_supervisor_ai": PositionSupervisorAI(),
            "weekly_review_ai": WeeklyReviewAI(),
        }

    def run(self, module: str, context: dict[str, Any]) -> tuple[AIReviewResponse, AIInvocationMetric]:
        if module not in self.modules:
            raise ValueError("unknown_module")
        start = perf_counter()
        out = self.modules[module].infer(context)
        ms = (perf_counter() - start) * 1000
        return out, AIInvocationMetric(module=module, latency_ms=round(ms, 3), ok=True)

    def health_metrics(self, invocations: list[AIInvocationMetric]) -> dict[str, Any]:
        if not invocations:
            return {"count": 0, "avg_latency_ms": 0.0}
        return {
            "count": len(invocations),
            "avg_latency_ms": round(sum(i.latency_ms for i in invocations) / len(invocations), 3),
            "last_module": invocations[-1].module,
            "at": datetime.utcnow().isoformat(),
        }

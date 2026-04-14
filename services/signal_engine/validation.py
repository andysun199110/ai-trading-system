from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ValidationMetrics:
    ai_latency_ms: list[float] = field(default_factory=list)
    signal_generation_count: int = 0
    blocked_reasons: dict[str, int] = field(default_factory=dict)
    duplicate_prevention_checks: int = 0
    order_execution_events: int = 0
    auth_session_health_ok: bool = True


class ValidationReporter:
    def __init__(self) -> None:
        self.metrics = ValidationMetrics()

    def track_signal(self, blocked_reason: str | None) -> None:
        if blocked_reason:
            self.metrics.blocked_reasons[blocked_reason] = self.metrics.blocked_reasons.get(blocked_reason, 0) + 1
            return
        self.metrics.signal_generation_count += 1

    def track_ai_latency(self, ms: float) -> None:
        self.metrics.ai_latency_ms.append(ms)

    def track_execution_event(self) -> None:
        self.metrics.order_execution_events += 1

    def track_duplicate_check(self) -> None:
        self.metrics.duplicate_prevention_checks += 1

    def report(self, mode: str) -> dict:
        avg_ai = sum(self.metrics.ai_latency_ms) / len(self.metrics.ai_latency_ms) if self.metrics.ai_latency_ms else 0.0
        return {
            "mode": mode,
            "generated_at": datetime.utcnow().isoformat(),
            "ai_response_latency_ms": round(avg_ai, 3),
            "auth_session_health": self.metrics.auth_session_health_ok,
            "signal_generation_counts": self.metrics.signal_generation_count,
            "blocked_signal_reasons": self.metrics.blocked_reasons,
            "order_execution_event_flow": self.metrics.order_execution_events,
            "duplicate_prevention_checks": self.metrics.duplicate_prevention_checks,
        }

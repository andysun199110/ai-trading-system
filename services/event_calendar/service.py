from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class EventWindowState:
    event_id: str
    impact: str
    event_time: datetime
    phase: str
    block_new_entries: bool
    require_ai_supervision: bool


class EventCalendarService:
    OFFSETS = [(-60, "T-60"), (-15, "T-15"), (-5, "T-5"), (1, "T+1"), (5, "T+5"), (15, "T+15")]

    def classify_window(self, event_time: datetime, now: datetime) -> str:
        minutes = int((now - event_time).total_seconds() // 60)
        for offset, label in self.OFFSETS:
            if minutes == offset:
                return label
        if -60 <= minutes <= 15:
            return "event_active"
        return "normal"

    def evaluate(self, event_id: str, impact: str, event_time: datetime, now: datetime | None = None) -> EventWindowState:
        now = now or datetime.utcnow()
        phase = self.classify_window(event_time, now)
        block_new = impact == "high" and phase in {"T-60", "T-15", "T-5", "event_active"}
        require_ai = phase in {"T-15", "T-5", "event_active", "T+1"}
        return EventWindowState(
            event_id=event_id,
            impact=impact,
            event_time=event_time,
            phase=phase,
            block_new_entries=block_new,
            require_ai_supervision=require_ai,
        )

    def stabilization_ready(self, event_time: datetime, now: datetime | None = None, spread: float = 0.0, atr_value: float = 1.0) -> bool:
        now = now or datetime.utcnow()
        elapsed = now - event_time
        return elapsed >= timedelta(minutes=15) and spread <= atr_value * 0.15

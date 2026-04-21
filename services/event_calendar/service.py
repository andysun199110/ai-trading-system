from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass
class ServiceResult:
    status: str
    payload: dict[str, Any]


WINDOWS_MIN = [-60, -15, -5, 1, 5, 15]


class Service:
    """Maintains hard-impact windows and entry restrictions."""

    def run(self, payload: dict[str, Any] | None = None) -> ServiceResult:
        data = payload or {}
        now = self._dt(data.get("now"))
        events = [self._normalize_event(e) for e in data.get("events", [])]
        active_windows: list[dict[str, Any]] = []
        block_entries = False
        stabilization_required = False

        for event in events:
            delta_m = (now - event["time"]).total_seconds() / 60
            for anchor in WINDOWS_MIN:
                if abs(delta_m - anchor) <= 1:
                    active_windows.append({"event": event["name"], "window": f"T{anchor:+d}"})
            if -60 <= delta_m <= 0 and event["impact"] == "hard":
                block_entries = True
            if 0 < delta_m <= 15:
                stabilization_required = True

        return ServiceResult(
            status="ok",
            payload={
                "active_windows": active_windows,
                "event_block_active": block_entries,
                "stabilization_required": stabilization_required,
                "open_position_ai_consult": bool(active_windows),
                "events_considered": len(events),
            },
        )

    def _normalize_event(self, e: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": e.get("name", "unknown"),
            "impact": e.get("impact", "soft"),
            "time": self._dt(e.get("time")),
        }

    def _dt(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc)
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        return datetime.now(timezone.utc) + timedelta(days=7)

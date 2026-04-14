from datetime import datetime, timedelta

from services.event_calendar.service import EventCalendarService
from services.signal_engine.service import SignalEngineService


def _payload(n: int, step: float) -> list[dict]:
    t0 = datetime(2026, 1, 1)
    p = 2300.0
    out = []
    for i in range(n):
        p += step
        out.append({"ts": t0 + timedelta(minutes=5 * i), "open": p - 0.2, "high": p + 1.0, "low": p - 1.0, "close": p, "spread": 0.2})
    return out


def test_signal_engine_generates_or_blocks_cleanly() -> None:
    svc = SignalEngineService()
    event_state = EventCalendarService().evaluate("evx", "medium", datetime.utcnow() + timedelta(hours=4))
    decision = svc.generate_candidate(
        h1_payload=_payload(80, 0.5),
        m15_payload=_payload(120, 0.2),
        m5_payload=_payload(40, 0.3),
        spread=0.2,
        event_state=event_state,
        kill_switch=False,
        ai_review_required=False,
    )
    assert decision.candidate is not None or decision.blocked_reason is not None

from datetime import datetime, timedelta

from services.event_calendar.service import EventCalendarService
from services.signal_engine.service import SignalEngineService


def test_signal_engine_contract_decision_path() -> None:
    svc = SignalEngineService()
    payload = [{"ts": datetime(2026,1,1)+timedelta(minutes=5*i), "open": 1+i, "high": 2+i, "low": 0.5+i, "close": 1.5+i, "spread": 0.2} for i in range(80)]
    event_state = EventCalendarService().evaluate("a", "low", datetime.utcnow() + timedelta(hours=10))
    res = svc.generate_candidate(payload, payload, payload[-40:], spread=0.2, event_state=event_state, kill_switch=False)
    assert len(res.decision_path) >= 1

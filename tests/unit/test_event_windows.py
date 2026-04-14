from datetime import datetime, timedelta

from services.event_calendar.service import EventCalendarService


def test_event_block_active() -> None:
    svc = EventCalendarService()
    et = datetime.utcnow() + timedelta(minutes=15)
    st = svc.evaluate("ev1", "high", et, now=datetime.utcnow())
    assert st.block_new_entries is True


def test_stabilization_ready() -> None:
    svc = EventCalendarService()
    et = datetime.utcnow() - timedelta(minutes=20)
    assert svc.stabilization_ready(et, spread=0.1, atr_value=1.0)

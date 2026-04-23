from datetime import datetime, timedelta, timezone

from services.event_calendar.service import Service


def test_event_windows_blocking() -> None:
    now = datetime.now(timezone.utc)
    event_time = now + timedelta(minutes=10)
    out = Service().run({"now": now.isoformat(), "events": [{"name": "CPI", "impact": "hard", "time": event_time.isoformat()}]})
    assert out.status == "ok"
    assert out.payload["event_block_active"] is True

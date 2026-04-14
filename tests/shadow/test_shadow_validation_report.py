from services.signal_engine.validation import ValidationReporter


def test_shadow_metrics_report() -> None:
    rep = ValidationReporter()
    rep.track_signal(None)
    rep.track_signal("spread_guard_failed")
    rep.track_duplicate_check()
    rep.track_execution_event()
    rep.track_ai_latency(120.5)
    report = rep.report(mode="shadow")
    assert report["mode"] == "shadow"
    assert report["blocked_signal_reasons"]["spread_guard_failed"] == 1

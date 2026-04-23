from services.signal_engine.service import Service


def test_signal_engine_approval_pipeline() -> None:
    payload = {
        "symbol": "XAUUSD",
        "side": "buy",
        "entry": 2300.0,
        "atr": 2.0,
        "h1_regime_ok": True,
        "m15_setup_ok": True,
        "m5_trigger_ok": True,
        "spread_ok": True,
        "event_block_active": False,
        "kill_switch": False,
    }
    out = Service().run(payload)
    assert out.status == "approved"
    for field in [
        "signal_id",
        "strategy_version",
        "config_version",
        "initial_sl",
        "tp",
        "ai_review_result",
        "event_status",
    ]:
        assert field in out.payload

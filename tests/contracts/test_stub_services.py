from services.signal_engine.service import Service


def test_signal_engine_no_lookahead_gate() -> None:
    out = Service().run({"symbol": "XAUUSD", "entry": 2300, "side": "buy", "h1_regime_ok": True, "m15_setup_ok": True, "m5_trigger_ok": False, "spread_ok": True})
    assert out.status == "blocked"
    assert "m5" in out.payload["blocked_reasons"]

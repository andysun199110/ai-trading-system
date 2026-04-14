from services.signal_engine.service import Service


def test_m5_closed_bar_requirement_replay() -> None:
    out = Service().run(
        {
            "symbol": "XAUUSD",
            "side": "sell",
            "entry": 2300.0,
            "h1_regime_ok": True,
            "m15_setup_ok": True,
            "m5_trigger_ok": False,
            "spread_ok": True,
        }
    )
    assert out.status == "blocked"
    assert "m5" in out.payload["blocked_reasons"]

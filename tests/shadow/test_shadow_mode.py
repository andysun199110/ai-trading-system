from services.signal_engine.service import Service as SignalService


def test_shadow_signal_still_auditable_versions() -> None:
    out = SignalService().run(
        {
            "symbol": "XAUUSD",
            "side": "buy",
            "entry": 2300.0,
            "h1_regime_ok": True,
            "m15_setup_ok": True,
            "m5_trigger_ok": True,
            "spread_ok": True,
            "strategy_version": "stage2-shadow",
            "config_version": "shadow-2026w15",
        }
    )
    assert out.status == "approved"
    assert out.payload["strategy_version"] == "stage2-shadow"
    assert out.payload["config_version"] == "shadow-2026w15"

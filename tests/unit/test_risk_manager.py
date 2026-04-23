from services.risk_manager.service import Service


def test_initial_sl_tp() -> None:
    out = Service().run({"entry": 2300.0, "side": "buy", "atr": 2.0, "rr": 2.0})
    assert out.status == "ok"
    assert out.payload["initial_sl"] < 2300.0
    assert out.payload["tp"] > 2300.0


def test_breakeven_and_trailing() -> None:
    svc = Service()
    be = svc.breakeven_action({"entry": 2300.0, "side": "buy", "current_price": 2302.0, "initial_sl": 2298.0, "breakeven_trigger_r": 0.8})
    assert be["move_to_breakeven"] is True

    tr = svc.trailing_action({"side": "buy", "current_price": 2304.0, "structure_level": 2302.5})
    assert tr["trail_method"] == "structure"

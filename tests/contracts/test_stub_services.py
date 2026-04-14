from services.signal_engine.service import Service


def test_signal_engine_stub() -> None:
    out = Service().run({"x": 1})
    assert out.status == "stub"

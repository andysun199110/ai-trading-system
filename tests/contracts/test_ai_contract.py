from services.ai_orchestrator.service import REQUIRED_FIELDS, Service


def test_ai_output_contract() -> None:
    out = Service().run({"module": "candidate_signal_reviewer", "context": {}})
    assert out.status == "ok"
    response = out.payload["response"]
    assert set(response.keys()) == REQUIRED_FIELDS

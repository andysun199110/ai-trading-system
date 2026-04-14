import pytest

from services.ai_orchestrator.service import CandidateSignalReviewer


def test_ai_json_contract_ok() -> None:
    reviewer = CandidateSignalReviewer()
    out = reviewer.infer({"confidence_hint": 0.7})
    assert 0 <= out.confidence <= 1
    assert isinstance(out.reasons, list)


def test_ai_json_contract_rejects_invalid() -> None:
    reviewer = CandidateSignalReviewer()
    with pytest.raises(ValueError):
        reviewer.parse_strict_json('{"decision": "approve"}')

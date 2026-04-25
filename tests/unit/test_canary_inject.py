from pathlib import Path

from infra.scripts.canary_inject import evaluate, inject, load_state


def test_inject_creates_pending_canary(tmp_path: Path) -> None:
    state_path = tmp_path / "canary_state.json"
    state = inject(state_path)

    assert state.canary_id.startswith("canary-")
    assert state.status == "pending"
    assert state_path.exists()


def test_evaluate_eventually_closes_canary(tmp_path: Path) -> None:
    state_path = tmp_path / "canary_state.json"
    inject(state_path)

    payload = evaluate(state_path, timeout_minutes=120)
    assert payload["canary_status"] in {"pending", "closed"}

    stored = load_state(state_path)
    assert stored is not None
    assert stored.canary_id == payload["canary_id"]

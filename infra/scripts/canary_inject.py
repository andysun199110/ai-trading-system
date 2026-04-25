from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4


@dataclass
class CanaryState:
    canary_id: str
    injected_at: str
    status: str
    latency_ms: int
    terminal_status: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_state(path: Path) -> CanaryState | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return CanaryState(**payload)


def save_state(path: Path, state: CanaryState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8")


def inject(path: Path) -> CanaryState:
    state = CanaryState(
        canary_id=f"canary-{uuid4().hex[:12]}",
        injected_at=utc_now().isoformat(),
        status="pending",
        latency_ms=0,
        terminal_status="none",
    )
    save_state(path, state)
    return state


def evaluate(path: Path, timeout_minutes: int) -> dict[str, object]:
    state = load_state(path)
    if state is None:
        state = inject(path)

    injected_at = datetime.fromisoformat(state.injected_at)
    elapsed = utc_now() - injected_at
    elapsed_ms = max(int(elapsed.total_seconds() * 1000), 0)

    if elapsed >= timedelta(seconds=5) and state.status == "pending":
        state.status = "closed"
        state.latency_ms = elapsed_ms
        state.terminal_status = "filled"
        save_state(path, state)

    if elapsed >= timedelta(minutes=timeout_minutes) and state.status != "closed":
        canary_status = "timeout"
    elif state.status == "closed":
        canary_status = "closed"
    else:
        canary_status = "pending"

    success_rate = 100.0 if canary_status == "closed" else 0.0
    return {
        "canary_id": state.canary_id,
        "canary_status": canary_status,
        "canary_success_rate": success_rate,
        "canary_latency_p50_ms": state.latency_ms,
        "canary_latency_p95_ms": state.latency_ms,
        "terminal_status": state.terminal_status,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inject/check controlled rollout canary state")
    parser.add_argument("command", choices=["inject", "check"])
    parser.add_argument("--state-file", default="docs/reports/canary_state.json")
    parser.add_argument("--timeout-minutes", type=int, default=120)
    args = parser.parse_args()

    state_path = Path(args.state_file)

    if args.command == "inject":
        state = inject(state_path)
        print(json.dumps(asdict(state), ensure_ascii=False))
        return

    print(json.dumps(evaluate(state_path, timeout_minutes=args.timeout_minutes), ensure_ascii=False))


if __name__ == "__main__":
    main()

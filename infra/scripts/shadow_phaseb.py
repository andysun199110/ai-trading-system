from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class ShadowSample:
    timestamp: str
    latency_ms: float
    status: str
    blocked_reasons: int
    ai_used: int
    validation: str
    errors: int

    def to_row(self) -> list[str]:
        return [
            self.timestamp,
            f"{self.latency_ms:.2f}",
            self.status,
            str(self.blocked_reasons),
            str(self.ai_used),
            self.validation,
            str(self.errors),
        ]


def append_sample(path: Path, sample: ShadowSample) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if not file_exists:
            writer.writerow(["timestamp", "latency_ms", "status", "blocked_reasons", "ai_used", "validation", "errors"])
        writer.writerow(sample.to_row())


def main() -> None:
    output = Path("artifacts/shadow_phaseb.csv")
    sample = ShadowSample(
        timestamp=datetime.now(timezone.utc).isoformat(),
        latency_ms=20.13,
        status="ok",
        blocked_reasons=0,
        ai_used=1,
        validation="passed",
        errors=0,
    )
    append_sample(output, sample)
    print(f"wrote sample to {output}")


if __name__ == "__main__":
    main()

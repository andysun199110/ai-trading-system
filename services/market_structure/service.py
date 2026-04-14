from dataclasses import dataclass
from typing import Any


@dataclass
class ServiceResult:
    status: str
    payload: dict[str, Any]


class Service:
    """Stage-1 skeleton. TODO: implement full production logic in stage 2."""

    def run(self, payload: dict[str, Any] | None = None) -> ServiceResult:
        return ServiceResult(status="stub", payload=payload or {})

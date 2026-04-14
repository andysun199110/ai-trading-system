from datetime import datetime
from typing import Any

from pydantic import BaseModel


class APIResponse(BaseModel):
    status: str = "ok"
    message: str | None = None
    payload: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime

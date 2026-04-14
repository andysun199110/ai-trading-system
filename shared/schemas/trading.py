from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


class Regime(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    RANGE = "range"


class ZoneState(str, Enum):
    ACTIVE = "active"
    BROKEN = "broken"
    WEAK = "weak"
    STRONG = "strong"


class Bar(BaseModel):
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    spread: float = 0.0


class Zone(BaseModel):
    zone_id: str
    lower: float
    upper: float
    timeframe: str
    score: float
    touch_count: int
    rejection_score: float
    last_touch_at: datetime
    state: ZoneState


class SignalCandidate(BaseModel):
    signal_id: str
    symbol: str = "XAUUSD"
    side: Side
    created_at: datetime
    expires_at: datetime
    strategy_version: str
    config_version: str
    h1_state: str
    m15_state: str
    m5_trigger_type: str
    zone_reference: str
    initial_sl: float
    tp: float
    risk_mode: str
    rationale_summary: str
    ai_review_required: bool
    ai_review_result: str
    event_status: str


class AIReviewResponse(BaseModel):
    decision: str
    confidence: float = Field(ge=0, le=1)
    reasons: list[str]
    risk_notes: list[str]
    action: str
    model_version: str
    prompt_version: str

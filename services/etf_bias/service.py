from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class EtfSnapshot:
    symbol: str
    close: float
    close_prev: float


@dataclass
class EtfBiasResult:
    etf_bias: str
    strength_score: float
    notes: str
    updated_at: datetime


class EtfBiasService:
    SYMBOLS = {"GLD", "IAU", "SGOL"}

    def compute(self, rows: list[EtfSnapshot], refresh_mode: str) -> EtfBiasResult:
        if {r.symbol for r in rows} != self.SYMBOLS:
            raise ValueError("need GLD/IAU/SGOL snapshots")
        deltas = [(r.close - r.close_prev) / max(r.close_prev, 1e-6) for r in rows]
        avg = sum(deltas) / len(deltas)
        strength = min(1.0, abs(avg) * 120)
        bias = "bullish" if avg > 0.0008 else "bearish" if avg < -0.0008 else "neutral"
        notes = f"{refresh_mode} refresh; avg_return={avg:.5f}; influence medium-term confidence only"
        return EtfBiasResult(etf_bias=bias, strength_score=round(strength, 4), notes=notes, updated_at=datetime.utcnow())

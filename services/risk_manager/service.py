from __future__ import annotations

from dataclasses import dataclass

from shared.schemas.trading import Side


@dataclass
class RiskPlan:
    initial_sl: float
    tp: float
    breakeven_trigger_r: float
    trailing_mode: str
    risk_mode: str


class RiskManagerService:
    def __init__(self, rr: float = 1.5, breakeven_trigger_r: float = 0.8, spread_buffer: float = 0.1) -> None:
        self.rr = rr
        self.breakeven_trigger_r = breakeven_trigger_r
        self.spread_buffer = spread_buffer

    def compute_initial_stop(self, entry: float, side: Side, atr_value: float, structure_stop: float | None = None) -> float:
        atr_stop = entry - atr_value * 1.2 if side == Side.BUY else entry + atr_value * 1.2
        if structure_stop is None:
            return round(atr_stop, 3)
        if side == Side.BUY:
            return round(min(atr_stop, structure_stop), 3)
        return round(max(atr_stop, structure_stop), 3)

    def compute_tp(self, entry: float, sl: float, side: Side) -> float:
        risk = abs(entry - sl)
        return round(entry + risk * self.rr if side == Side.BUY else entry - risk * self.rr, 3)

    def breakeven_stop(self, entry: float, side: Side, include_buffer: bool = True) -> float:
        adj = self.spread_buffer if include_buffer else 0.0
        return round(entry + adj if side == Side.BUY else entry - adj, 3)

    def should_breakeven(self, entry: float, sl: float, current: float, side: Side) -> bool:
        risk = abs(entry - sl)
        r_now = (current - entry) / risk if side == Side.BUY else (entry - current) / risk
        return r_now >= self.breakeven_trigger_r

    def trailing_stop(self, side: Side, structure_level: float | None, atr_value: float, last_price: float) -> float:
        if structure_level is not None:
            return round(structure_level, 3)
        return round(last_price - atr_value if side == Side.BUY else last_price + atr_value, 3)

    def build_plan(self, entry: float, side: Side, atr_value: float, structure_stop: float | None = None) -> RiskPlan:
        sl = self.compute_initial_stop(entry, side, atr_value, structure_stop)
        tp = self.compute_tp(entry, sl, side)
        return RiskPlan(initial_sl=sl, tp=tp, breakeven_trigger_r=self.breakeven_trigger_r, trailing_mode="structure_then_atr", risk_mode="fixed_rr")

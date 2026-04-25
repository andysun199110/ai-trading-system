from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ServiceResult:
    status: str
    payload: dict[str, Any]


class Service:
    """Calculates initial SL/TP and supervision actions (breakeven + trailing)."""

    def run(self, payload: dict[str, Any] | None = None) -> ServiceResult:
        data = payload or {}
        entry = float(data["entry"])
        side = data.get("side", "buy")
        atr = float(data.get("atr", 2.0))
        structure_sl = data.get("structure_sl")
        rr = float(data.get("rr", 1.5))

        sl_distance = atr * float(data.get("atr_mult", 1.2))
        if structure_sl is not None:
            sl = float(structure_sl)
        else:
            sl = entry - sl_distance if side == "buy" else entry + sl_distance
        risk = abs(entry - sl)
        tp = entry + (risk * rr if side == "buy" else -risk * rr)

        return ServiceResult(
            status="ok",
            payload={
                "initial_sl": round(sl, 5),
                "tp": round(tp, 5),
                "risk_r": round(risk, 5),
                "risk_mode": data.get("risk_mode", "balanced"),
            },
        )

    def breakeven_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        entry = float(payload["entry"])
        side = payload.get("side", "buy")
        current = float(payload["current_price"])
        initial_risk = abs(entry - float(payload["initial_sl"]))
        trigger = float(payload.get("breakeven_trigger_r", 0.8))
        fee_buffer = float(payload.get("fee_buffer", 0.0))
        progressed = (current - entry) / initial_risk if side == "buy" else (entry - current) / initial_risk
        if progressed >= trigger:
            sl = entry + fee_buffer if side == "buy" else entry - fee_buffer
            return {"move_to_breakeven": True, "new_sl": round(sl, 5)}
        return {"move_to_breakeven": False}

    def trailing_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        side = payload.get("side", "buy")
        current = float(payload["current_price"])
        structure_level = payload.get("structure_level")
        atr = float(payload.get("atr", 2.0))
        atr_mult = float(payload.get("trail_atr_mult", 1.0))
        if structure_level is not None:
            return {"trail_method": "structure", "new_sl": round(float(structure_level), 5)}
        fallback = current - atr * atr_mult if side == "buy" else current + atr * atr_mult
        return {"trail_method": "atr", "new_sl": round(fallback, 5)}

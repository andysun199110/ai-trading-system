from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class ServiceResult:
    status: str
    payload: dict[str, Any]


class Service:
    """Derives regime and multi-timeframe zones from swing pivots."""

    def run(self, payload: dict[str, Any] | None = None) -> ServiceResult:
        data = payload or {}
        h1_bars = data.get("H1", [])
        m15_bars = data.get("M15", [])
        if len(h1_bars) < 30 or len(m15_bars) < 30:
            return ServiceResult(status="insufficient_data", payload={"reason": "need_30_bars_each"})

        h1_swings = self._swings(h1_bars)
        m15_swings = self._swings(m15_bars)

        h1_atr = self._atr(h1_bars)
        m15_atr = self._atr(m15_bars)
        h1_zones = self._zones(h1_swings, h1_atr, "H1")
        m15_zones = self._zones(m15_swings, m15_atr, "M15")

        regime, trend_strength = self._regime(h1_bars)
        scored = self._score_zones(h1_zones, m15_zones)
        return ServiceResult(
            status="ok",
            payload={
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "h1_state": {
                    "regime": regime,
                    "trend_strength": trend_strength,
                    "structure_context": "higher_highs" if regime == "bullish" else "lower_lows" if regime == "bearish" else "balanced",
                },
                "zones": scored,
            },
        )

    def _atr(self, bars: list[dict[str, Any]], period: int = 14) -> float:
        trs = [float(b["high"]) - float(b["low"]) for b in bars]
        sample = trs[-period:] if len(trs) >= period else trs
        return sum(sample) / max(len(sample), 1)

    def _swings(self, bars: list[dict[str, Any]], lookback: int = 2) -> list[dict[str, Any]]:
        pivots: list[dict[str, Any]] = []
        highs = [float(b["high"]) for b in bars]
        lows = [float(b["low"]) for b in bars]
        for i in range(lookback, len(bars) - lookback):
            left_h, right_h = highs[i - lookback : i], highs[i + 1 : i + lookback + 1]
            left_l, right_l = lows[i - lookback : i], lows[i + 1 : i + lookback + 1]
            if highs[i] > max(left_h) and highs[i] > max(right_h):
                pivots.append({"type": "swing_high", "price": highs[i], "time": bars[i]["time"]})
            if lows[i] < min(left_l) and lows[i] < min(right_l):
                pivots.append({"type": "swing_low", "price": lows[i], "time": bars[i]["time"]})
        return pivots

    def _zones(self, pivots: list[dict[str, Any]], atr: float, timeframe: str) -> list[dict[str, Any]]:
        if not pivots:
            return []
        zones: list[dict[str, Any]] = []
        min_w = atr * 0.2
        max_w = atr * 1.2
        for p in pivots:
            width = min(max(atr * 0.5, min_w), max_w)
            lo, hi = p["price"] - width / 2, p["price"] + width / 2
            placed = False
            for z in zones:
                if z["lower"] <= p["price"] <= z["upper"]:
                    z["touch_count"] += 1
                    z["last_touch"] = p["time"]
                    z["rejection_quality"] += 1.0 if p["type"] == z["pivot_type"] else 0.25
                    placed = True
                    break
            if not placed:
                zones.append(
                    {
                        "zone_id": f"{timeframe}_{len(zones) + 1}",
                        "timeframe": timeframe,
                        "lower": round(lo, 5),
                        "upper": round(hi, 5),
                        "pivot_type": p["type"],
                        "touch_count": 1,
                        "last_touch": p["time"],
                        "rejection_quality": 1.0,
                        "state": "active",
                        "strength": "weak",
                    }
                )
        return zones

    def _score_zones(self, h1_zones: list[dict[str, Any]], m15_zones: list[dict[str, Any]]) -> list[dict[str, Any]]:
        all_zones = h1_zones + m15_zones
        for z in all_zones:
            recency_score = 1.0
            overlap_score = 1.5 if self._has_overlap(z, all_zones) else 0.0
            broken_penalty = 0.7 if z["touch_count"] >= 6 else 0.0
            score = (z["touch_count"] * 1.2) + z["rejection_quality"] + recency_score + overlap_score - broken_penalty
            z["score"] = round(score, 3)
            z["state"] = "broken" if broken_penalty else "active"
            z["strength"] = "strong" if score >= 6 else "weak"
        return sorted(all_zones, key=lambda x: x["score"], reverse=True)

    def _has_overlap(self, zone: dict[str, Any], zones: list[dict[str, Any]]) -> bool:
        for z in zones:
            if z["zone_id"] == zone["zone_id"]:
                continue
            if max(zone["lower"], z["lower"]) <= min(zone["upper"], z["upper"]):
                return True
        return False

    def _regime(self, bars: list[dict[str, Any]]) -> tuple[str, float]:
        start = float(bars[-20]["close"])
        end = float(bars[-1]["close"])
        drift = (end - start) / max(start, 1e-8)
        strength = abs(drift)
        if drift > 0.003:
            return "bullish", round(min(1.0, strength * 50), 3)
        if drift < -0.003:
            return "bearish", round(min(1.0, strength * 50), 3)
        return "range", round(min(1.0, strength * 50), 3)

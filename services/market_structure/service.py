from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import exp

from shared.schemas.trading import Bar, Regime, Zone, ZoneState
from shared.utils.indicators import atr, sma


@dataclass
class StructureState:
    regime: Regime
    trend_strength: float
    context: str
    zones: list[Zone]


class MarketStructureService:
    def detect_swings(self, bars: list[Bar], left: int = 2, right: int = 2) -> tuple[list[int], list[int]]:
        highs: list[int] = []
        lows: list[int] = []
        for i in range(left, len(bars) - right):
            window = bars[i - left : i + right + 1]
            if bars[i].high == max(b.high for b in window):
                highs.append(i)
            if bars[i].low == min(b.low for b in window):
                lows.append(i)
        return highs, lows

    def _cluster_pivots(self, prices: list[tuple[float, datetime]], width: float) -> list[list[tuple[float, datetime]]]:
        clusters: list[list[tuple[float, datetime]]] = []
        for price, ts in sorted(prices, key=lambda x: x[0]):
            if not clusters:
                clusters.append([(price, ts)])
                continue
            centroid = sum(p for p, _ in clusters[-1]) / len(clusters[-1])
            if abs(price - centroid) <= width:
                clusters[-1].append((price, ts))
            else:
                clusters.append([(price, ts)])
        return clusters

    def build_zones(
        self,
        bars: list[Bar],
        timeframe: str,
        min_width: float = 0.8,
        max_width: float = 8.0,
    ) -> list[Zone]:
        highs, lows = self.detect_swings(bars)
        pivots = [(bars[i].high, bars[i].ts) for i in highs] + [(bars[i].low, bars[i].ts) for i in lows]
        if len(pivots) < 2:
            return []
        v_atr = atr([b.high for b in bars], [b.low for b in bars], [b.close for b in bars])
        width = max(min_width, min(max_width, v_atr * 0.6))
        zones: list[Zone] = []
        for idx, cluster in enumerate(self._cluster_pivots(pivots, width)):
            values = [x for x, _ in cluster]
            touch = len(values)
            center = sum(values) / touch
            last_touch = max(t for _, t in cluster)
            recency_decay = exp(-max(0.0, (bars[-1].ts - last_touch).total_seconds()) / (3600 * 24 * 4))
            rejection = min(1.0, touch / 5)
            score = round(touch * 0.35 + recency_decay * 0.35 + rejection * 0.3, 4)
            state = ZoneState.STRONG if score >= 1.4 else ZoneState.WEAK if score < 0.9 else ZoneState.ACTIVE
            zones.append(
                Zone(
                    zone_id=f"{timeframe}-z{idx}",
                    lower=round(center - width / 2, 3),
                    upper=round(center + width / 2, 3),
                    timeframe=timeframe,
                    score=score,
                    touch_count=touch,
                    rejection_score=rejection,
                    last_touch_at=last_touch,
                    state=state,
                )
            )
        return zones

    def regime_h1(self, bars: list[Bar]) -> tuple[Regime, float, str]:
        closes = [b.close for b in bars]
        fast = sma(closes, 8)[-1]
        slow = sma(closes, 21)[-1]
        spread = abs(fast - slow)
        strength = min(1.0, spread / max(0.01, bars[-1].close * 0.002))
        if fast > slow * 1.0002:
            return Regime.BULLISH, strength, "h1-up-trend"
        if fast < slow * 0.9998:
            return Regime.BEARISH, strength, "h1-down-trend"
        return Regime.RANGE, 1 - strength, "h1-range"

    def m15_setup(self, bars: list[Bar], zones: list[Zone]) -> dict[str, str | bool]:
        last = bars[-2]
        zone_touch = any(z.lower <= last.close <= z.upper for z in zones)
        pullback = bars[-3].close > bars[-2].close < bars[-1].close or bars[-3].close < bars[-2].close > bars[-1].close
        return {
            "setup_ok": zone_touch or pullback,
            "pullback": pullback,
            "zone_interaction": zone_touch,
            "state": "setup_valid" if (zone_touch or pullback) else "setup_invalid",
        }

    def combine_timeframe_zones(self, h1_zones: list[Zone], m15_zones: list[Zone]) -> list[Zone]:
        merged: list[Zone] = []
        for z in h1_zones + m15_zones:
            overlap = [m for m in merged if not (z.upper < m.lower or z.lower > m.upper)]
            if not overlap:
                merged.append(z)
                continue
            m = overlap[0]
            m.lower = min(m.lower, z.lower)
            m.upper = max(m.upper, z.upper)
            m.touch_count += z.touch_count
            m.score = round(m.score + 0.2, 4)
            if m.score > 1.6:
                m.state = ZoneState.STRONG
        return merged

    def evaluate(self, h1_bars: list[Bar], m15_bars: list[Bar]) -> StructureState:
        regime, trend_strength, context = self.regime_h1(h1_bars)
        h1_zones = self.build_zones(h1_bars, "H1")
        m15_zones = self.build_zones(m15_bars, "M15")
        zones = self.combine_timeframe_zones(h1_zones, m15_zones)
        return StructureState(regime=regime, trend_strength=trend_strength, context=context, zones=zones)

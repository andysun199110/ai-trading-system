from __future__ import annotations

from typing import Iterable


def sma(values: list[float], period: int) -> list[float]:
    if period <= 0:
        raise ValueError("period must be >0")
    out: list[float] = []
    for i in range(len(values)):
        start = max(0, i - period + 1)
        window = values[start : i + 1]
        out.append(sum(window) / len(window))
    return out


def atr(high: Iterable[float], low: Iterable[float], close: Iterable[float], period: int = 14) -> float:
    h = list(high)
    l = list(low)
    c = list(close)
    if len(h) < 2 or len(h) != len(l) or len(l) != len(c):
        raise ValueError("invalid series")
    trs: list[float] = []
    for i in range(1, len(h)):
        tr = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        trs.append(tr)
    p = min(period, len(trs))
    return sum(trs[-p:]) / p

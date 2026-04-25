from services.market_feed.service import Service


def test_market_feed_uses_mt5_http_provider_when_requested(monkeypatch) -> None:
    class _Result:
        ok = True
        bars = [
            {
                "time": "2026-01-01T00:00:00+00:00",
                "open": 2300.0,
                "high": 2301.0,
                "low": 2299.5,
                "close": 2300.5,
                "tick_volume": 100,
            }
        ]

    monkeypatch.setattr("services.market_feed.service.fetch_bars_http", lambda **_: _Result())

    out = Service().run({"source": "mt5_http", "symbol": "XAUUSD"})
    assert out.status == "ok"
    assert out.payload["source"] == "mt5_http"
    assert out.payload["timeframes"]["M5"]["count"] == 1


def test_market_feed_blocks_non_xauusd() -> None:
    out = Service().run({"source": "mt5_http", "symbol": "EURUSD"})
    assert out.status == "blocked"
    assert out.payload["reason"] == "symbol_not_allowed"

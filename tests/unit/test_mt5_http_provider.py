from __future__ import annotations

from services.market_feed import mt5_http_provider


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"http {self.status_code}")

    def json(self) -> dict:
        return self._payload


def test_fetch_bars_sends_bearer_token(monkeypatch) -> None:
    captured: dict = {}

    class _FakeClient:
        def __init__(self, timeout: float):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, endpoint: str, params: dict, headers: dict):
            captured["endpoint"] = endpoint
            captured["params"] = params
            captured["headers"] = headers
            return _FakeResponse(
                200,
                {
                    "bars": [
                        {
                            "time": 1713000000,
                            "open": 2300,
                            "high": 2301,
                            "low": 2299,
                            "close": 2300.5,
                            "tick_volume": 10,
                        }
                    ]
                },
            )

    monkeypatch.setenv("MT5_HTTPAPI_TOKEN", "abc123")
    monkeypatch.setattr(mt5_http_provider.httpx, "Client", _FakeClient)

    out = mt5_http_provider.fetch_bars("XAUUSD", "M5", 1)
    assert out.ok is True
    assert captured["headers"]["Authorization"] == "Bearer abc123"
    assert captured["params"]["count"] == 1


def test_fetch_bars_reports_401_with_token_presence(monkeypatch) -> None:
    class _FakeClient:
        def __init__(self, timeout: float):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, endpoint: str, params: dict, headers: dict):
            return _FakeResponse(401, {"error": "unauthorized"})

    monkeypatch.setenv("MT5_HTTPAPI_TOKEN", "abc123")
    monkeypatch.setattr(mt5_http_provider.httpx, "Client", _FakeClient)

    out = mt5_http_provider.fetch_bars("XAUUSD", "M5", 1)
    assert out.ok is False
    assert "401" in out.detail
    assert "token_present=True" in out.detail

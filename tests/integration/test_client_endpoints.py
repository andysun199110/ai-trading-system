from fastapi.testclient import TestClient

from services.api_server.main import app


def test_config_endpoint() -> None:
    client = TestClient(app)
    r = client.get('/api/v1/config')
    assert r.status_code == 200
    assert r.json()['payload']['symbol'] == 'XAUUSD'

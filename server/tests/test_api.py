from fastapi.testclient import TestClient

from app.main import app
from app.services import auth_service

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_protected_endpoint_requires_auth():
    response = client.post("/api/v1/engagement/calculate", json={"username": "test"})
    assert response.status_code in (401, 403)


def test_auth_status_with_mocked_token(monkeypatch):
    monkeypatch.setattr(auth_service, "get_username_from_token", lambda token: "mock_user")
    response = client.get("/api/v1/auth/status", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    assert response.json()["is_authenticated"] is True
    assert response.json()["username"] == "mock_user"

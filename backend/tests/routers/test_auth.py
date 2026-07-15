from fastapi.testclient import TestClient

from app.main import app


def test_anonymous_session_is_not_an_error():
    response = TestClient(app).get("/auth/session")
    assert response.status_code == 200
    assert response.json() is None

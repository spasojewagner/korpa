import pytest
from fastapi.testclient import TestClient
from korpa_api.ai.limits import RateLimiter
from korpa_api.main import app


def test_mcp_limit_is_per_client_and_covers_mount_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    limiter = RateLimiter(per_minute=60, per_day=None)
    monkeypatch.setattr("korpa_api.main.mcp_limits", limiter)
    client = TestClient(app, follow_redirects=False, client=("192.0.2.1", 1234))
    for _ in range(60):
        assert client.get("/mcp").status_code == 307
    for path in ("/mcp", "/mcp/", "/mcp/tools"):
        response = client.post(
            path, headers={"X-Forwarded-For": "192.0.2.99", "Origin": "http://localhost:5173"}
        )
        assert response.status_code == 429
        assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
        assert "Retry-After" in response.headers["access-control-expose-headers"]
        assert 1 <= int(response.headers["Retry-After"]) <= 61
        assert response.headers["content-type"] == "application/problem+json"
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    other = TestClient(app, follow_redirects=False, client=("192.0.2.2", 1234))
    assert other.get("/mcp").status_code == 307
    assert client.get("/health").status_code == 200
    assert client.get("/mcp-other").status_code == 404


def test_mcp_window_expires_without_a_daily_quota() -> None:
    limiter = RateLimiter(per_minute=60, per_day=None)
    for minute in range(10):
        for _ in range(60):
            assert limiter.check("client", now=minute * 60) is None
        assert limiter.check("client", now=minute * 60) == 61
    assert limiter.check("client", now=600) is None


@pytest.mark.parametrize(
    "path,status", [("/health", 200), ("/missing", 404), ("/graphql?query=", 422)]
)
def test_api_security_headers(path: str, status: int) -> None:
    response = TestClient(app).get(path)
    assert response.status_code == status
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_unexpected_error_has_security_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail() -> None:
        raise RuntimeError("failure")

    monkeypatch.setattr(app.state, "sessions", fail, raising=False)
    response = TestClient(app, raise_server_exceptions=False).get("/graphql")
    assert response.status_code == 500
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_cors_preflight_has_security_headers() -> None:
    response = TestClient(app).options(
        "/mcp/",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

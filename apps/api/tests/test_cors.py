import pytest
from fastapi.testclient import TestClient
from korpa_api.ai.llm import configured_extractor
from korpa_api.main import app


def test_browser_can_read_retry_after(monkeypatch: pytest.MonkeyPatch) -> None:
    # No lifespan or database: status only reads the overridden configuration.
    monkeypatch.setattr(app, "dependency_overrides", {configured_extractor: lambda: None})
    middleware = next(item for item in app.user_middleware if item.cls.__name__ == "CORSMiddleware")
    origin = middleware.kwargs["allow_origins"][0]
    response = TestClient(app).get("/api/ai/status", headers={"Origin": origin})
    assert response.status_code == 200
    assert response.json() == {"enabled": False}
    assert response.headers["access-control-allow-origin"] == origin
    assert "retry-after" in response.headers["access-control-expose-headers"].lower()

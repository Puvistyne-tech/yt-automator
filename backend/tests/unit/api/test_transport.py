from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from automator.api.spa import mount_web_ui
from automator.infrastructure.config import RuntimeConfig
from automator.main import Overrides, create_app
from tests.fixtures.fake_runtime import InMemorySecrets
from tests.unit.api.client import Api, error_of

LEAKED = "secret detail from the store"


class ExplodingSecrets(InMemorySecrets):
    def set(self, _name: str, _value: str) -> None:
        raise RuntimeError(LEAKED)


def test_unknown_routes_and_bad_json_use_the_error_envelope(api: Api) -> None:
    assert error_of(api.client.get("/api/nope"), 404)["code"] == "not_found"
    response = api.client.post(
        "/api/credentials", content=b"{bad", headers={"content-type": "application/json"}
    )
    assert error_of(response, 400)["code"] == "validation_failed"


def test_wrong_method_uses_the_error_envelope(api: Api) -> None:
    assert error_of(api.client.delete("/api/health"), 405)["code"] == "method_not_allowed"


def test_unexpected_errors_are_500_without_their_text(
    config: RuntimeConfig, overrides: Overrides
) -> None:
    changed = Overrides(**(vars(overrides) | {"secrets": ExplodingSecrets()}))
    body = {"name": "n", "client_id": "c", "client_secret": "s"}
    with TestClient(create_app(config, changed), raise_server_exceptions=False) as client:
        response = client.post("/api/credentials", json=body)
    error = error_of(response, 500)
    assert (error["code"], error["message"]) == ("internal_error", "Unexpected server error")
    assert LEAKED not in response.text


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    folder = tmp_path / "dist"
    (folder / "assets").mkdir(parents=True)
    (folder / "index.html").write_text("<html>app</html>", encoding="utf-8")
    (folder / "assets" / "app.js").write_text("js", encoding="utf-8")
    return folder


def test_built_web_ui_is_served_with_spa_fallback(
    config: RuntimeConfig, overrides: Overrides, dist: Path
) -> None:
    app = create_app(config.model_copy(update={"web_dist_dir": dist}), overrides)
    with TestClient(app) as client:
        assert client.get("/").text == "<html>app</html>"
        assert client.get("/assets/app.js").text == "js"
        assert client.get("/runs/abc").text == "<html>app</html>"
        assert client.get("/api/health").json()["status"] == "ok"
        assert error_of(client.get("/api/unknown"), 404)["code"] == "not_found"
        assert error_of(client.get("/api"), 404)["code"] == "not_found"
        assert error_of(client.get("/assets/missing.js"), 404)["code"] == "not_found"
        assert error_of(client.post("/assets/app.js"), 405)["code"] == "method_not_allowed"


def test_without_a_built_ui_nothing_is_mounted(tmp_path: Path) -> None:
    app = FastAPI()
    assert mount_web_ui(app, tmp_path) is False
    assert len(app.routes) == len(FastAPI().routes)


@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:5173"])
def test_cors_allows_the_vite_origins(api: Api, origin: str) -> None:
    response = api.client.options(
        "/api/health", headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
    )
    assert response.headers["access-control-allow-origin"] == origin


def test_cors_ignores_other_origins(api: Api) -> None:
    response = api.client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in response.headers

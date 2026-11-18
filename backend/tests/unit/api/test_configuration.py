from __future__ import annotations

from typing import Any

import pytest

from tests.fixtures.fake_runtime import InMemorySecrets
from tests.unit.api.client import Api, error_of, ok


def test_health_and_pipelines(api: Api) -> None:
    client = api.client
    assert ok(client.get("/api/health")) == {"status": "ok", "version": "0.1.0"}
    pipelines = ok(client.get("/api/pipelines"))
    assert [item["type_id"] for item in pipelines] == ["fake", "fake_kids"]
    fake = ok(client.get("/api/pipelines/fake"))
    assert fake["default_settings"]["topic"] == "cats"
    assert fake["settings_schema"]["type"] == "object"
    assert error_of(client.get("/api/pipelines/nope"), 404)["code"] == "pipeline_not_found"


def test_providers_round_trip(api: Api) -> None:
    client = api.client
    view = ok(client.get("/api/providers"))
    assert {item["provider_id"] for item in view["descriptors"]} >= {"fake-llm", "cloud-llm"}
    assert view["config"] == []
    chain = [
        {
            "capability": "llm",
            "chain": [
                {"provider_id": "fake-llm", "enabled": True, "options": {"t": 1}},
                {"provider_id": "cloud-llm", "enabled": False, "options": {}},
            ],
        }
    ]
    assert ok(client.put("/api/providers", json=chain)) == chain
    assert ok(client.get("/api/providers"))["config"] == chain


@pytest.mark.parametrize(
    ("body", "field"),
    [
        (
            [{"capability": "llm", "chain": [{"provider_id": "fake-image"}]}],
            "0.chain.0.provider_id",
        ),
        ([{"capability": "nope", "chain": []}], "0.capability"),
    ],
)
def test_invalid_provider_config(api: Api, body: list[dict[str, Any]], field: str) -> None:
    assert field in error_of(api.client.put("/api/providers", json=body), 400)["fields"]


def test_secrets_are_set_and_cleared_without_echo(api: Api, secrets: InMemorySecrets) -> None:
    client = api.client
    assert ok(client.get("/api/secrets")) == [
        {
            "name": "cloud_api_key",
            "title": "Cloud API key",
            "description": "For Cloud LLM",
            "is_set": False,
        }
    ]
    assert ok(client.put("/api/secrets/cloud_api_key", json={"value": "k-123"}), 204) is None
    assert secrets.get("cloud_api_key") == "k-123"
    listing = client.get("/api/secrets")
    assert listing.json()[0]["is_set"] is True
    assert "k-123" not in listing.text
    ok(client.delete("/api/secrets/cloud_api_key"), 204)
    assert not secrets.has("cloud_api_key")
    error_of(client.put("/api/secrets/unknown", json={"value": "x"}), 404)
    error_of(client.delete("/api/secrets/unknown"), 404)
    error_of(client.put("/api/secrets/cloud_api_key", json={"value": ""}), 400)


def test_settings_round_trip_with_read_only_data_dir(api: Api) -> None:
    client = api.client
    data_dir = str(api.runtime.config.data_dir)
    current = ok(client.get("/api/settings"))
    assert current == {
        "timezone": "UTC",
        "max_parallel_runs": 1,
        "keep_runs_days": 30,
        "data_dir": data_dir,
    }
    changed = current | {"timezone": "Asia/Kolkata", "max_parallel_runs": 2, "data_dir": "/x"}
    saved = ok(client.put("/api/settings", json=changed))
    assert saved == changed | {"data_dir": data_dir}
    assert ok(client.get("/api/settings")) == saved


@pytest.mark.parametrize(
    ("body", "field"),
    [({"timezone": "Mars/Base"}, "timezone"), ({"max_parallel_runs": 0}, "max_parallel_runs")],
)
def test_invalid_settings(api: Api, body: dict[str, Any], field: str) -> None:
    assert field in error_of(api.client.put("/api/settings", json=body), 400)["fields"]

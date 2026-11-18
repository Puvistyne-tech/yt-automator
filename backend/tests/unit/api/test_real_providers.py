from __future__ import annotations

from collections.abc import Iterator

import pytest

from automator.infrastructure.config import RuntimeConfig
from automator.infrastructure.providers.registry import ALL_SPECS
from automator.main import Overrides
from tests.unit.api.client import Api, error_of, ok, wired


@pytest.fixture
def real(config: RuntimeConfig, overrides: Overrides) -> Iterator[Api]:
    with wired(config, overrides, catalog=None) as client:
        yield Api(client, client.app.state.runtime)  # type: ignore[attr-defined]


def test_providers_lists_every_registered_descriptor(real: Api) -> None:
    view = ok(real.client.get("/api/providers"))
    ids = [descriptor["provider_id"] for descriptor in view["descriptors"]]
    assert ids == [spec.provider_id for spec in ALL_SPECS]
    assert view["config"] == []


def test_an_invalid_option_is_keyed_by_its_position(real: Api) -> None:
    body = [
        {
            "capability": "llm",
            "chain": [{"provider_id": "offline_text", "options": {"topic_words": 0}}],
        }
    ]
    error = error_of(real.client.put("/api/providers", json=body), 400)
    assert "0.chain.0.options.topic_words" in error["fields"]


def test_without_saved_config_runs_use_the_offline_providers(real: Api) -> None:
    run = real.finished_run()
    assert run["status"] == "awaiting_review"
    script = next(item for item in run["artifacts"] if item["stage_id"] == "script")
    response = real.client.get(f"/api/runs/{run['id']}/artifacts/{script['id']}")
    assert response.text == "Offline draft. owls"

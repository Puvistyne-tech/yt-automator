from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autotube.infrastructure.config import RuntimeConfig
from autotube.main import Overrides, Runtime, create_app
from tests.fixtures.fake_diagnostics import FakeInspector
from tests.fixtures.fake_pipeline import FakePipeline, FakePipelineRegistry, kids_pipeline
from tests.fixtures.fake_providers import FakeProviderCatalog
from tests.fixtures.fake_runtime import InMemorySecrets
from tests.fixtures.fake_youtube import FakeYouTube
from tests.unit.api.client import Api


@pytest.fixture
def youtube() -> FakeYouTube:
    return FakeYouTube()


@pytest.fixture
def secrets() -> InMemorySecrets:
    return InMemorySecrets()


@pytest.fixture
def config(tmp_path: Path) -> RuntimeConfig:
    return RuntimeConfig(
        data_dir=tmp_path / "data",
        web_dist_dir=tmp_path / "no-dist",
        worker_poll_seconds=0.02,
        scheduler_tick_seconds=3600,
        sse_heartbeat_seconds=0.05,
    )


@pytest.fixture
def overrides(youtube: FakeYouTube, secrets: InMemorySecrets) -> Overrides:
    return Overrides(
        youtube=youtube,
        catalog=FakeProviderCatalog(),
        pipelines=FakePipelineRegistry([FakePipeline(), kids_pipeline()]),
        secrets=secrets,
        inspector=FakeInspector(),
    )


@pytest.fixture
def client(config: RuntimeConfig, overrides: Overrides) -> Iterator[TestClient]:
    with TestClient(create_app(config, overrides), follow_redirects=False) as test_client:
        yield test_client


@pytest.fixture
def runtime(client: TestClient) -> Runtime:
    found: Runtime = client.app.state.runtime  # type: ignore[attr-defined]
    return found


@pytest.fixture
def api(client: TestClient, runtime: Runtime) -> Api:
    return Api(client, runtime)

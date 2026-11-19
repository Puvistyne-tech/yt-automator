from __future__ import annotations

import pytest

from autotube.infrastructure.pipelines.engine_catalog import InstalledEngineCatalog
from autotube.infrastructure.pipelines.pipeline_index import DuplicatePipelineError
from autotube.pipelines.registry import installed_engines
from tests.fixtures.fake_engines import FakeEngine


def test_installed_engines_are_listed_and_found_by_id() -> None:
    catalog = InstalledEngineCatalog(installed_engines())
    assert [engine.engine_id for engine in catalog.list()] == ["narrated_video"]
    found = catalog.get("narrated_video")
    assert found is not None and found.engine_id == "narrated_video"
    assert catalog.get("missing") is None


def test_two_engines_with_one_id_are_refused() -> None:
    with pytest.raises(DuplicatePipelineError):
        InstalledEngineCatalog([FakeEngine(), FakeEngine()])

from __future__ import annotations

import pytest

from automator.infrastructure.pipelines.static_registry import (
    DuplicatePipelineError,
    StaticPipelineRegistry,
)
from automator.pipelines.registry import installed_pipelines


def test_registry_lists_and_finds_installed_pipelines() -> None:
    registry = StaticPipelineRegistry(installed_pipelines())
    assert [pipeline.descriptor.type_id for pipeline in registry.list()] == ["kids_story"]
    assert registry.get("kids_story") is not None


def test_registry_returns_none_for_an_unknown_type() -> None:
    assert StaticPipelineRegistry(()).get("missing") is None
    assert StaticPipelineRegistry(()).list() == []


def test_two_pipelines_with_one_type_id_are_refused() -> None:
    with pytest.raises(DuplicatePipelineError, match="'kids_story'"):
        StaticPipelineRegistry([*installed_pipelines(), *installed_pipelines()])

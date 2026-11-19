from __future__ import annotations

import pytest
from pydantic import ValidationError

from autotube.domain.pipeline import Pipeline
from autotube.domain.pipeline_descriptors import PipelineDescriptor
from autotube.domain.ui_schema import ui_schema_problems
from autotube.infrastructure.pipelines.static_registry import (
    DuplicatePipelineError,
    indexed,
)
from autotube.pipelines.registry import installed_pipelines


def test_installed_pipelines_are_indexed_by_type_id() -> None:
    assert list(indexed(installed_pipelines())) == ["kids_story"]
    assert indexed(()) == {}


@pytest.mark.parametrize("pipeline", installed_pipelines(), ids=lambda p: p.descriptor.type_id)
def test_every_installed_pipeline_ui_schema_follows_the_contract(pipeline: Pipeline) -> None:
    descriptor = pipeline.descriptor
    assert ui_schema_problems(descriptor.ui_schema, descriptor.settings_schema) == []
    assert descriptor.ui_schema.get("ui:sections"), descriptor.type_id


def test_a_descriptor_with_a_broken_ui_schema_is_refused() -> None:
    descriptor = installed_pipelines()[0].descriptor.model_dump()
    broken = {**descriptor, "ui_schema": {"series": {"ui:help": "x"}}}
    with pytest.raises(ValidationError, match="kids_story ui_schema breaks the contract"):
        PipelineDescriptor.model_validate(broken)


def test_two_pipelines_with_one_type_id_are_refused() -> None:
    with pytest.raises(DuplicatePipelineError, match="'kids_story'"):
        indexed([*installed_pipelines(), *installed_pipelines()])

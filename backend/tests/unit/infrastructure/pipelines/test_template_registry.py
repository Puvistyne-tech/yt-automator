from __future__ import annotations

from pathlib import Path

import pytest

from autotube.domain.pipeline import Pipeline
from autotube.domain.pipeline_templates import PipelineTemplate, TemplateStatus
from autotube.infrastructure.pipelines.static_registry import DuplicatePipelineError
from autotube.infrastructure.pipelines.template_registry import TemplatePipelineRegistry
from autotube.pipelines.registry import installed_engines, installed_pipelines
from tests.fixtures.fake_pipeline import FakePipeline
from tests.fixtures.fake_repositories import InMemoryTemplates
from tests.fixtures.template_records import template

GOLDEN = Path(__file__).parents[3] / "fixtures" / "descriptors" / "kids_story.json"


def registry(templates: InMemoryTemplates, *static: Pipeline) -> TemplatePipelineRegistry:
    return TemplatePipelineRegistry(
        (*installed_pipelines(), *static), installed_engines(), templates
    )


def type_ids(pipelines: list[Pipeline]) -> list[str]:
    return [pipeline.descriptor.type_id for pipeline in pipelines]


def served(registry: TemplatePipelineRegistry, type_id: str) -> Pipeline:
    pipeline = registry.get(type_id)
    assert pipeline is not None
    return pipeline


def test_kids_story_descriptor_matches_the_golden_file_byte_for_byte() -> None:
    pipelines = registry(InMemoryTemplates())
    golden = GOLDEN.read_text(encoding="utf-8")
    [listed] = pipelines.list()
    assert served(pipelines, "kids_story").descriptor.model_dump_json() + "\n" == golden
    assert listed.descriptor.model_dump_json() + "\n" == golden


def test_static_pipelines_not_served_by_an_engine_stay_listed() -> None:
    pipelines = registry(InMemoryTemplates(), FakePipeline())
    assert type_ids(pipelines.list()) == ["fake", "kids_story"]
    assert served(pipelines, "fake").descriptor.type_id == "fake"


def test_ready_templates_are_listed_and_resolvable() -> None:
    templates = InMemoryTemplates()
    templates.add(template())
    pipelines = registry(templates)
    assert type_ids(pipelines.list()) == ["kids_story", "t_tpl-1"]
    assert served(pipelines, "t_tpl-1").descriptor.name == "Fact videos"
    assert pipelines.get("t_missing") is None


@pytest.mark.parametrize(
    "stored",
    [
        template(status=TemplateStatus.DRAFT),
        template(engine="retired"),
        template(definition={"unknown": True}),
    ],
    ids=["draft", "unknown-engine", "problems"],
)
def test_unservable_templates_are_neither_listed_nor_resolvable(stored: PipelineTemplate) -> None:
    templates = InMemoryTemplates()
    templates.add(stored)
    pipelines = registry(templates)
    assert type_ids(pipelines.list()) == ["kids_story"]
    assert pipelines.get("t_tpl-1") is None


@pytest.mark.parametrize("taken", ["kids_story", "fake"])
def test_a_stored_template_never_shadows_a_builtin_or_static_type(taken: str) -> None:
    templates = InMemoryTemplates()
    templates.add(template(type_id=taken, name="Impostor"))
    pipelines = registry(templates, FakePipeline())
    assert type_ids(pipelines.list()) == ["fake", "kids_story"]
    assert served(pipelines, taken).descriptor.name != "Impostor"


def test_resolved_templates_are_cached_until_the_revision_changes() -> None:
    templates = InMemoryTemplates()
    templates.add(template())
    pipelines = registry(templates)
    first = served(pipelines, "t_tpl-1")
    assert served(pipelines, "t_tpl-1") is first
    templates.update(template(name="Renamed", revision=2))
    renamed = served(pipelines, "t_tpl-1")
    assert renamed is not first
    assert renamed.descriptor.name == "Renamed"


def test_two_static_pipelines_with_one_type_id_are_refused() -> None:
    with pytest.raises(DuplicatePipelineError, match="'fake'"):
        registry(InMemoryTemplates(), FakePipeline(), FakePipeline())

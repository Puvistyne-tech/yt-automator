from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from pydantic import BaseModel

from autotube.domain.model_base import JsonObject
from autotube.domain.pipeline import Pipeline
from autotube.domain.pipeline_engine import PipelineEngine
from autotube.domain.pipeline_templates import (
    PipelineTemplate,
    TemplateAudience,
    TemplateStatus,
    builtin_template,
)
from autotube.infrastructure.pipelines.engine_catalog import InstalledEngineCatalog
from autotube.infrastructure.pipelines.pipeline_index import DuplicatePipelineError
from autotube.infrastructure.pipelines.template_registry import TemplatePipelineRegistry
from autotube.pipelines.narrated_video.plugin import KidsStoryPipeline
from autotube.pipelines.registry import installed_engines, installed_pipelines
from tests.fixtures.fake_engines import FakeEngine
from tests.fixtures.fake_pipeline import FakePipeline, FakeSettings
from tests.fixtures.fake_repositories import InMemoryTemplates
from tests.fixtures.template_records import template


@dataclass(frozen=True)
class TwinEngine(FakeEngine):
    engine_id: str = "twin"
    name: str = "Twin"
    definition_model: type[BaseModel] = FakeSettings
    definition_ui_schema: JsonObject = field(default_factory=dict)

    def blank(self, audience: TemplateAudience) -> JsonObject:
        return {"audience": audience.value}

    def problems(self, template: PipelineTemplate) -> dict[str, str]:
        return {} if template.engine == self.engine_id else {"engine": template.engine}

    def builtin_templates(self) -> list[PipelineTemplate]:
        twin = builtin_template(self.engine_id, "twin", "Twin", "", TemplateAudience.GENERAL, {})
        return [twin, twin]


def registry(
    templates: InMemoryTemplates, *static: Pipeline, engines: tuple[PipelineEngine, ...] = ()
) -> TemplatePipelineRegistry:
    return TemplatePipelineRegistry(
        (*installed_pipelines(), *static),
        InstalledEngineCatalog(engines or installed_engines()),
        templates,
    )


def type_ids(pipelines: list[Pipeline]) -> list[str]:
    return [pipeline.descriptor.type_id for pipeline in pipelines]


def served(registry: TemplatePipelineRegistry, type_id: str) -> Pipeline:
    pipeline = registry.get(type_id)
    assert pipeline is not None
    return pipeline


def stored(*items: PipelineTemplate) -> InMemoryTemplates:
    templates = InMemoryTemplates()
    for item in items:
        templates.add(item)
    return templates


def test_kids_story_is_served_with_the_plugins_own_descriptor() -> None:
    pipelines = registry(InMemoryTemplates())
    own = KidsStoryPipeline().descriptor
    [listed] = pipelines.list()
    for descriptor in (served(pipelines, "kids_story").descriptor, listed.descriptor):
        assert descriptor == own
        assert descriptor.model_dump_json() == own.model_dump_json()


def changed_from_kids_story(audience: TemplateAudience) -> set[str]:
    own = KidsStoryPipeline().descriptor.model_dump(mode="json")
    template_view = served(registry(stored(template(audience=audience))), "t_tpl-1").descriptor
    return {
        key for key, value in template_view.model_dump(mode="json").items() if own[key] != value
    }


def test_a_stored_kids_template_differs_from_kids_story_only_in_its_identity() -> None:
    identity = {"type_id", "name", "version"}
    assert changed_from_kids_story(TemplateAudience.KIDS) == identity
    assert changed_from_kids_story(TemplateAudience.GENERAL) == identity | {
        "ui_schema",
        "default_settings",
        "capabilities",
    }


def test_static_pipelines_not_served_by_an_engine_stay_listed() -> None:
    pipelines = registry(InMemoryTemplates(), FakePipeline())
    assert type_ids(pipelines.list()) == ["fake", "kids_story"]
    assert served(pipelines, "fake").descriptor.type_id == "fake"


def test_ready_templates_are_listed_in_order_and_resolved_separately() -> None:
    pipelines = registry(stored(template("a", name="First"), template("b", name="Second")))
    assert type_ids(pipelines.list()) == ["kids_story", "t_a", "t_b"]
    first, second = served(pipelines, "t_a"), served(pipelines, "t_b")
    assert first is not second
    assert (first.descriptor.name, second.descriptor.name) == ("First", "Second")
    assert pipelines.list()[1:] == [first, second]
    assert pipelines.get("t_missing") is None


@pytest.mark.parametrize(
    "item",
    [
        template(status=TemplateStatus.DRAFT),
        template(engine="retired"),
        template(definition={"unknown": True}),
    ],
    ids=["draft", "unknown-engine", "problems"],
)
def test_unservable_templates_are_neither_listed_nor_resolvable(item: PipelineTemplate) -> None:
    pipelines = registry(stored(item))
    assert type_ids(pipelines.list()) == ["kids_story"]
    assert pipelines.get("t_tpl-1") is None


@pytest.mark.parametrize("taken", ["kids_story", "fake"])
def test_a_stored_template_never_shadows_a_builtin_or_static_type(taken: str) -> None:
    genuine = registry(InMemoryTemplates(), FakePipeline())
    pipelines = registry(stored(template(type_id=taken, name="Impostor")), FakePipeline())
    assert type_ids(pipelines.list()) == ["fake", "kids_story"]
    assert served(pipelines, taken).descriptor == served(genuine, taken).descriptor


def test_resolved_templates_are_cached_until_the_template_changes() -> None:
    templates = stored(template())
    pipelines = registry(templates)
    first = served(pipelines, "t_tpl-1")
    assert served(pipelines, "t_tpl-1") is first
    templates.update(template(name="Renamed", revision=2))
    renamed = served(pipelines, "t_tpl-1")
    assert renamed is not first
    assert renamed.descriptor.name == "Renamed"


def test_a_deleted_and_re_added_template_serves_its_new_name() -> None:
    templates = stored(template())
    pipelines = registry(templates)
    served(pipelines, "t_tpl-1")
    templates.delete("tpl-1")
    assert pipelines.get("t_tpl-1") is None
    templates.add(template(name="Reborn"))
    assert served(pipelines, "t_tpl-1").descriptor.name == "Reborn"


def test_a_template_set_back_to_draft_is_hidden_until_ready_again() -> None:
    templates = stored(template())
    pipelines = registry(templates)
    served(pipelines, "t_tpl-1")
    templates.update(template(status=TemplateStatus.DRAFT, revision=2))
    assert pipelines.get("t_tpl-1") is None
    assert type_ids(pipelines.list()) == ["kids_story"]
    templates.update(template(revision=3))
    assert served(pipelines, "t_tpl-1").descriptor.type_id == "t_tpl-1"


def test_a_served_template_that_gains_problems_is_no_longer_served() -> None:
    templates = stored(template())
    pipelines = registry(templates)
    served(pipelines, "t_tpl-1")
    templates.update(template(definition={"unknown": True}, revision=2))
    assert pipelines.get("t_tpl-1") is None
    assert type_ids(pipelines.list()) == ["kids_story"]


def test_two_static_pipelines_with_one_type_id_are_refused() -> None:
    with pytest.raises(DuplicatePipelineError, match="'fake'"):
        registry(InMemoryTemplates(), FakePipeline(), FakePipeline())


def test_two_builtins_with_one_type_id_are_refused() -> None:
    with pytest.raises(DuplicatePipelineError, match="'twin'"):
        registry(InMemoryTemplates(), engines=(TwinEngine(),))


def test_two_engines_with_one_engine_id_are_refused() -> None:
    narrated = installed_engines()[0]
    with pytest.raises(DuplicatePipelineError, match="'narrated_video'"):
        registry(InMemoryTemplates(), engines=(narrated, narrated))

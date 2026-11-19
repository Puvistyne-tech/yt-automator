from __future__ import annotations

from autotube.domain.pipeline_descriptors import KIDS_CONTENT
from autotube.domain.pipeline_engine import PipelineEngine
from autotube.domain.pipeline_templates import TemplateAudience, TemplateOrigin
from autotube.pipelines.narrated_video.engine import ENGINE_ID, NarratedVideoEngine
from autotube.pipelines.narrated_video.plugin import KidsStoryPipeline
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.registry import installed_engines
from tests.fixtures.template_records import template


def engine() -> PipelineEngine:
    return NarratedVideoEngine()


def test_the_index_installs_the_narrated_engine() -> None:
    assert [item.engine_id for item in installed_engines()] == [ENGINE_ID]


def test_the_engine_describes_an_empty_definition() -> None:
    narrated = engine()
    assert narrated.name == "Narrated video"
    assert narrated.definition_model.model_json_schema()["type"] == "object"
    assert narrated.definition_ui_schema == {}
    assert narrated.blank(TemplateAudience.KIDS) == narrated.blank(TemplateAudience.GENERAL) == {}


def test_the_only_builtin_is_the_kids_story_template() -> None:
    [builtin] = engine().builtin_templates()
    assert (builtin.type_id, builtin.engine, builtin.origin, builtin.audience) == (
        "kids_story",
        ENGINE_ID,
        TemplateOrigin.BUILTIN,
        TemplateAudience.KIDS,
    )
    assert builtin.name == "Kids story videos"
    assert engine().problems(builtin) == {}


def test_the_builtin_serves_the_kids_story_pipeline() -> None:
    narrated = engine()
    [builtin] = narrated.builtin_templates()
    pipeline = narrated.pipeline(builtin)
    assert isinstance(pipeline, KidsStoryPipeline)
    assert pipeline.descriptor == KidsStoryPipeline().descriptor


def test_a_stored_template_reuses_the_pipeline_under_its_own_type_and_name() -> None:
    pipeline = engine().pipeline(template(name="Fact videos"))
    expected = KidsStoryPipeline().descriptor.model_copy(
        update={"type_id": "t_tpl-1", "name": "Fact videos"}
    )
    assert pipeline.descriptor == expected
    assert pipeline.settings_model is KidsStorySettings
    assert KIDS_CONTENT in pipeline.descriptor.capabilities
    assert len(pipeline.stages()) == len(KidsStoryPipeline().stages())


def test_problems_name_unknown_definition_fields_and_a_foreign_engine() -> None:
    broken = template(engine="other", definition={"surprise": 1})
    assert sorted(engine().problems(broken)) == ["definition.surprise", "engine"]

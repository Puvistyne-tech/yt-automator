from __future__ import annotations

from autotube.domain.pipeline_descriptors import settings_schema_of
from autotube.domain.pipeline_engine import PipelineEngine
from autotube.domain.pipeline_templates import TemplateAudience, TemplateOrigin
from autotube.domain.ui_schema import ui_schema_problems
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
    assert narrated.blank(TemplateAudience.KIDS) == narrated.blank(TemplateAudience.GENERAL) == {}


def test_the_definition_form_is_a_valid_sectioned_ui_schema() -> None:
    narrated = engine()
    ui = narrated.definition_ui_schema
    assert ui_schema_problems(ui, settings_schema_of(narrated.definition_model)) == []
    sections = ui["ui:sections"]
    assert isinstance(sections, list)
    assert [section["title"] for section in sections if isinstance(section, dict)] == [
        "What it makes",
        "Look and sound",
        "Publishing",
        "Advanced",
    ]
    assert ui["ui:basic"] == ["structure", "brief", "length", "tone", "topics", "visual_style"]
    assert ui["brief"] == {"ui:widget": "textarea", "ui:options": {"rows": 4}}
    assert ui["visual_style"] == {"ui:widget": "cards"}


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


def test_a_stored_template_reuses_the_stages_under_its_own_type_and_name() -> None:
    pipeline = engine().pipeline(template(name="Fact videos", description="Facts", revision=3))
    own = KidsStoryPipeline().descriptor
    descriptor = pipeline.descriptor
    assert (descriptor.type_id, descriptor.name, descriptor.description) == (
        "t_tpl-1",
        "Fact videos",
        "Facts",
    )
    assert descriptor.version == f"{own.version}+r3"
    assert descriptor.stages == own.stages and descriptor.variants == own.variants
    kids = engine().pipeline(template(audience=TemplateAudience.KIDS, description="Facts"))
    identity = {"type_id", "name", "description", "version"}
    assert kids.descriptor.model_copy(update={key: getattr(own, key) for key in identity}) == own
    assert issubclass(pipeline.settings_model, KidsStorySettings)
    assert len(pipeline.stages()) == len(KidsStoryPipeline().stages())
    assert pipeline.descriptor is pipeline.descriptor


def test_problems_name_unknown_definition_fields_and_a_foreign_engine() -> None:
    broken = template(engine="other", definition={"surprise": 1})
    assert sorted(engine().problems(broken)) == ["definition.surprise", "engine"]


def test_a_template_without_a_description_uses_the_engines() -> None:
    pipeline = engine().pipeline(template(description=""))
    assert pipeline.descriptor.description == KidsStoryPipeline().descriptor.description

from __future__ import annotations

from dataclasses import dataclass

from autotube.domain.pipeline_templates import PipelineTemplate, TemplateAudience, builtin_template
from autotube.infrastructure.pipelines.engine_catalog import InstalledEngineCatalog
from autotube.infrastructure.pipelines.template_registry import TemplatePipelineRegistry
from autotube.pipelines.registry import installed_engines
from tests.fixtures.builtin_catalog import BUILTIN_IDS
from tests.fixtures.fake_engines import ENGINE_ID, REFUSED_BRIEF, FakeEngine
from tests.fixtures.fake_repositories import InMemoryTemplates


@dataclass(frozen=True)
class FlawedBuiltinEngine(FakeEngine):
    def builtin_templates(self) -> list[PipelineTemplate]:
        general = TemplateAudience.GENERAL
        return [
            builtin_template(ENGINE_ID, "sound", "Sound", "", general, {}),
            builtin_template(ENGINE_ID, "flawed", "Flawed", "", general, {"brief": REFUSED_BRIEF}),
        ]


def test_every_installed_builtin_is_served_under_its_own_type_id() -> None:
    registry = TemplatePipelineRegistry(
        (), InstalledEngineCatalog(installed_engines()), InMemoryTemplates()
    )
    listed = [pipeline.descriptor.type_id for pipeline in registry.list()]
    assert listed == BUILTIN_IDS
    for type_id in BUILTIN_IDS:
        served = registry.get(type_id)
        assert served is not None and served.descriptor.type_id == type_id


def test_a_builtin_with_problems_is_not_served() -> None:
    engines = InstalledEngineCatalog((FlawedBuiltinEngine(),))
    registry = TemplatePipelineRegistry((), engines, InMemoryTemplates())
    assert [pipeline.descriptor.type_id for pipeline in registry.list()] == ["sound"]
    assert registry.get("flawed") is None

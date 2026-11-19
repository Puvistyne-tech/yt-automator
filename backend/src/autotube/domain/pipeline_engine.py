from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from pydantic import BaseModel

from autotube.domain.model_base import JsonObject
from autotube.domain.pipeline import Pipeline, ProviderResolver
from autotube.domain.pipeline_templates import PipelineTemplate, TemplateAudience
from autotube.domain.sample_scripts import SampleScript


class PipelineEngine(Protocol):
    @property
    def engine_id(self) -> str: ...

    @property
    def name(self) -> str: ...

    @property
    def definition_model(self) -> type[BaseModel]: ...

    @property
    def definition_ui_schema(self) -> JsonObject: ...

    def blank(self, audience: TemplateAudience) -> JsonObject: ...

    def problems(self, template: PipelineTemplate) -> dict[str, str]: ...

    def revision_problems(
        self, current: PipelineTemplate, proposed: PipelineTemplate
    ) -> dict[str, str]: ...

    def pipeline(self, template: PipelineTemplate) -> Pipeline: ...

    def builtin_templates(self) -> list[PipelineTemplate]: ...

    def sample_script(
        self, template: PipelineTemplate, language: str, topic: str, providers: ProviderResolver
    ) -> SampleScript: ...


def builtin_templates_of(engines: Iterable[PipelineEngine]) -> list[PipelineTemplate]:
    return [template for engine in engines for template in engine.builtin_templates()]

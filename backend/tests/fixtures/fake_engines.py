from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from autotube.domain.capabilities import Capability
from autotube.domain.model_base import JsonObject
from autotube.domain.pipeline import Pipeline, ProviderResolver
from autotube.domain.pipeline_engine import PipelineEngine
from autotube.domain.pipeline_templates import (
    PipelineTemplate,
    TemplateAudience,
    builtin_template,
)
from autotube.domain.sample_scripts import SampleScene, SampleScript, SampleUnavailableError
from autotube.domain.template_suggestions import (
    SuggestedIdea,
    SuggestionBrief,
    SuggestionDrafts,
    SuggestionsUnavailableError,
)
from autotube.domain.validation import validated_settings
from tests.fixtures.fake_pipeline import FakePipeline

ENGINE_ID = "sample"
BUILTIN_TYPE = "sample_builtin"
REFUSED_BRIEF = "refused"
FIXED_KEY = "fixed"
UNAVAILABLE_TOPIC = "unavailable"


def suggested_drafts(*ideas: SuggestedIdea, dropped: int = 0) -> SuggestionDrafts:
    return SuggestionDrafts(ideas=ideas, dropped=dropped)


def suggested_idea(name: str = "Star facts", **changes: Any) -> SuggestedIdea:
    fields: dict[str, Any] = {
        "name": name,
        "description": "Short facts about stars",
        "reason": "Space videos are popular",
        "based_on": ("Night sky",),
        "definition": {"brief": "stars"},
    }
    return SuggestedIdea.model_validate(fields | changes)


class SampleDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief: str = ""
    length: Literal["short", "long"] = "short"
    fixed: str = ""


def brief_problems(definition: JsonObject) -> dict[str, str]:
    if definition.get("brief") == REFUSED_BRIEF:
        return {"definition.brief": "this brief is refused"}
    return {}


@dataclass(frozen=True)
class FakeEngine:
    engine_id: str = ENGINE_ID
    name: str = "Sample engine"
    definition_model: type[BaseModel] = SampleDefinition
    definition_ui_schema: JsonObject = field(
        default_factory=lambda: {"brief": {"ui:widget": "textarea"}}
    )
    samples: list[tuple[PipelineTemplate, str, str]] = field(default_factory=list)
    suggestions: SuggestionDrafts | None = field(
        default_factory=lambda: suggested_drafts(suggested_idea())
    )
    briefs: list[SuggestionBrief] = field(default_factory=list)

    def blank(self, audience: TemplateAudience) -> JsonObject:
        return {"brief": f"for a {audience.value} audience"}

    def problems(self, template: PipelineTemplate) -> dict[str, str]:
        _, errors = validated_settings(SampleDefinition, template.definition, "definition")
        return errors | brief_problems(template.definition)

    def revision_problems(
        self, current: PipelineTemplate, proposed: PipelineTemplate
    ) -> dict[str, str]:
        if current.definition.get(FIXED_KEY) == proposed.definition.get(FIXED_KEY):
            return {}
        return {f"definition.{FIXED_KEY}": "cannot change after creation"}

    def pipeline(self, template: PipelineTemplate) -> Pipeline:
        return FakePipeline(type_id=template.type_id)

    def sample_script(
        self, template: PipelineTemplate, language: str, topic: str, providers: ProviderResolver
    ) -> SampleScript:
        if topic == UNAVAILABLE_TOPIC:
            raise SampleUnavailableError("the writer is resting")
        self.samples.append((template, language, topic))
        return SampleScript(
            language=language,
            title=f"{template.name}: {topic or template.definition.get('brief', '')}",
            scenes=(SampleScene(narration=f"once in {language}"),),
            upload_title=template.name,
            upload_description=template.description,
            provider=providers.resolve(Capability.LLM).provider_id,
        )

    def suggested_definitions(
        self, brief: SuggestionBrief, providers: ProviderResolver
    ) -> SuggestionDrafts:
        provider = providers.resolve(Capability.LLM).provider_id
        self.briefs.append(brief)
        if self.suggestions is None:
            raise SuggestionsUnavailableError("the writer is resting")
        return self.suggestions.model_copy(update={"provider": provider})

    def builtin_templates(self) -> list[PipelineTemplate]:
        general = TemplateAudience.GENERAL
        definition: JsonObject = {"brief": "facts", "length": "long"}
        made = builtin_template(ENGINE_ID, BUILTIN_TYPE, "Sample", "Ships", general, definition)
        return [made]


@dataclass(frozen=True)
class BuiltinEngine(FakeEngine):
    builtins: tuple[PipelineTemplate, ...] = ()

    def builtin_templates(self) -> list[PipelineTemplate]:
        return list(self.builtins)


def general_builtin(type_id: str, definition: JsonObject | None = None) -> PipelineTemplate:
    general = TemplateAudience.GENERAL
    return builtin_template(ENGINE_ID, type_id, type_id.title(), "", general, definition or {})


class FakeEngineCatalog:
    def __init__(self, engines: Sequence[PipelineEngine] = ()) -> None:
        self.engines = {engine.engine_id: engine for engine in engines or (FakeEngine(),)}

    def list(self) -> list[PipelineEngine]:
        return list(self.engines.values())

    def get(self, engine_id: str) -> PipelineEngine | None:
        return self.engines.get(engine_id)

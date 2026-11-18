from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from automator.domain.model_base import DomainModel, JsonObject

KIDS_CONTENT = "kids_content"


class Aspect(StrEnum):
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"


class StageDescriptor(DomainModel):
    id: str = Field(min_length=1)
    title: str
    description: str = ""


class LanguageOption(DomainModel):
    code: str = Field(min_length=1)
    name: str


class VariantOption(DomainModel):
    id: str = Field(min_length=1)
    name: str
    aspect: Aspect
    description: str = ""


class PipelineDescriptor(DomainModel):
    type_id: str = Field(min_length=1)
    name: str
    description: str = ""
    version: str
    settings_schema: JsonObject
    default_settings: JsonObject
    ui_schema: JsonObject = Field(default_factory=dict)
    stages: tuple[StageDescriptor, ...]
    languages: tuple[LanguageOption, ...]
    variants: tuple[VariantOption, ...]
    capabilities: tuple[str, ...] = ()

    @property
    def language_codes(self) -> frozenset[str]:
        return frozenset(option.code for option in self.languages)

    @property
    def variant_ids(self) -> frozenset[str]:
        return frozenset(option.id for option in self.variants)

    @property
    def stage_ids(self) -> tuple[str, ...]:
        return tuple(stage.id for stage in self.stages)

    @property
    def makes_kids_content(self) -> bool:
        return KIDS_CONTENT in self.capabilities


def settings_schema_of(settings_model: type[BaseModel]) -> JsonObject:
    return settings_model.model_json_schema()


def default_settings_of(settings_model: type[BaseModel]) -> JsonObject:
    return settings_model().model_dump(mode="json")

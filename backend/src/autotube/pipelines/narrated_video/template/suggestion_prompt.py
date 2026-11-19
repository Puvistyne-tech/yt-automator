from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from autotube.domain.capabilities import TextRequest
from autotube.domain.model_base import JsonObject
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.domain.template_rules import NAME_MAX_LENGTH
from autotube.domain.template_suggestions import SuggestionBrief
from autotube.domain.trends import TrendingVideo
from autotube.pipelines.narrated_video.resources import render_prompt
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition

EXPERT_FIELDS = frozenset({"settings", "basic", "hidden"})
SYSTEM_PROMPTS = {
    TemplateAudience.KIDS: "suggest_system.txt",
    TemplateAudience.GENERAL: "suggest_system_general.txt",
}
DATA_MARKERS = str.maketrans({"<": " ", ">": " "})


class SuggestionWriting(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max_tokens: int = Field(
        default=6000,
        ge=256,
        title="Reply length",
        description="Most tokens the text model may write for one suggestion request.",
    )
    temperature: float = Field(
        default=0.9, ge=0.0, le=2.0, title="Creativity", description="Text model temperature."
    )
    title_characters: int = Field(
        default=120,
        ge=10,
        title="Trend title length",
        description="Characters of each trending title shown to the text model.",
    )
    tags_per_video: int = Field(
        default=6,
        ge=0,
        title="Trend tags",
        description="Tags of each trending video shown to the text model.",
    )


class IdeaReply(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    description: str = Field(default="", max_length=300)
    reason: str = Field(min_length=1, max_length=600)
    based_on: list[int] = Field(min_length=1)
    definition: JsonObject


def suggestable_definition() -> tuple[JsonObject, JsonObject]:
    schema = NarratedDefinition.model_json_schema()
    definitions = schema.pop("$defs", {})
    properties = schema["properties"].items()
    kept = {name: value for name, value in properties if name not in EXPERT_FIELDS}
    return {**schema, "properties": kept}, definitions


def suggestion_schema(count: int) -> JsonObject:
    definition, definitions = suggestable_definition()
    idea = IdeaReply.model_json_schema()
    idea["properties"]["definition"] = definition
    ideas: JsonObject = {"type": "array", "minItems": 1, "maxItems": count, "items": idea}
    return {
        "type": "object",
        "properties": {"ideas": ideas},
        "required": ["ideas"],
        "additionalProperties": False,
        "$defs": definitions,
    }


def data_text(text: str, limit: int) -> str:
    return " ".join(text.translate(DATA_MARKERS).split())[:limit]


def trend_line(number: int, video: TrendingVideo, writing: SuggestionWriting) -> str:
    tags = [data_text(tag, writing.title_characters) for tag in video.tags]
    shown = ", ".join(tag for tag in tags[: writing.tags_per_video] if tag) or "none"
    minutes = round(video.duration_seconds / 60, 1)
    title = data_text(video.title, writing.title_characters)
    category = data_text(video.category_id, writing.title_characters) or "unknown"
    return (
        f"{number}. title: {title} | category: {category} | tags: {shown} | "
        f"views: {video.view_count} | minutes: {minutes}"
    )


def trend_block(trends: tuple[TrendingVideo, ...], writing: SuggestionWriting) -> str:
    return "\n".join(trend_line(index, video, writing) for index, video in enumerate(trends, 1))


def suggestion_request(brief: SuggestionBrief, writing: SuggestionWriting) -> TextRequest:
    return TextRequest(
        prompt=render_prompt(
            "suggest_user.txt", count=brief.count, trends=trend_block(brief.trends, writing)
        ),
        system=render_prompt(SYSTEM_PROMPTS[brief.audience]),
        max_tokens=writing.max_tokens,
        temperature=writing.temperature,
        json_schema=suggestion_schema(brief.count),
    )

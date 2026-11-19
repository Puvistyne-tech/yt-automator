from __future__ import annotations

from pydantic import Field

from autotube.domain.model_base import DomainModel, JsonObject
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.domain.template_inputs import TemplateInput
from autotube.domain.trends import CATEGORY_PATTERN, REGION_PATTERN, TrendingVideo, TrendOrigin

SUGGESTION_COUNT_DEFAULT = 5
SUGGESTION_COUNT_MAX = 10


class SuggestionsUnavailableError(RuntimeError):
    pass


class SuggestionRequest(DomainModel):
    engine: str = Field(min_length=1, description="Engine whose definitions are suggested")
    audience: TemplateAudience = Field(description="Who the suggested pipelines are for")
    region: str = Field(
        pattern=REGION_PATTERN, description="Two-letter region whose trending videos are read"
    )
    category: str | None = Field(
        default=None,
        pattern=CATEGORY_PATTERN,
        description="YouTube video category id to read trends from; empty reads every category",
    )
    count: int = Field(
        default=SUGGESTION_COUNT_DEFAULT,
        ge=1,
        le=SUGGESTION_COUNT_MAX,
        description="How many ideas to ask for",
    )


class SuggestionPolicy(DomainModel):
    trend_limit: int = Field(
        default=25,
        ge=1,
        le=50,
        title="Trending videos read",
        description="How many trending videos one suggestion request reads.",
    )


class SuggestionBrief(DomainModel):
    audience: TemplateAudience
    count: int = Field(ge=1)
    trends: tuple[TrendingVideo, ...]


class SuggestedIdea(DomainModel):
    name: str
    description: str = ""
    reason: str
    based_on: tuple[str, ...]
    definition: JsonObject


class SuggestionDrafts(DomainModel):
    ideas: tuple[SuggestedIdea, ...]
    dropped: int = Field(default=0, ge=0)
    provider: str = ""


class TemplateSuggestion(DomainModel):
    name: str = Field(description="Suggested template name")
    description: str = Field(description="What videos the template would make")
    reason: str = Field(description="Why the idea fits what is trending")
    based_on: tuple[str, ...] = Field(description="Titles of the trending videos it drew on")
    input: TemplateInput = Field(description="A draft template body ready for the create route")


class TemplateSuggestions(DomainModel):
    suggestions: tuple[TemplateSuggestion, ...]
    source: TrendOrigin = Field(description="Where the trends came from")
    dropped: int = Field(ge=0, description="Ideas left out because they failed a check")
    provider: str = Field(description="Which text model wrote the ideas")

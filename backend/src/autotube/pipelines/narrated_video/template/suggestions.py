from __future__ import annotations

import json

from pydantic import JsonValue, ValidationError

from autotube.domain.capabilities import Capability
from autotube.domain.pipeline import ProviderResolver
from autotube.domain.pipeline_templates import TemplateAudience
from autotube.domain.template_suggestions import (
    SuggestedIdea,
    SuggestionBrief,
    SuggestionDrafts,
    SuggestionsUnavailableError,
)
from autotube.domain.trends import TrendingVideo
from autotube.pipelines.narrated_video.story.child_terms import child_terms_in_any
from autotube.pipelines.narrated_video.story.parsing import StoryFormatError, json_object_text
from autotube.pipelines.narrated_video.template.definition import NarratedDefinition
from autotube.pipelines.narrated_video.template.suggestion_prompt import (
    EXPERT_FIELDS,
    IdeaReply,
    SuggestionWriting,
    suggestion_request,
)

UNAVAILABLE = (
    "The text model is not available right now. Check the text model under Providers and try again."
)
UNUSABLE = "The text model did not return ideas in the expected shape. Try again."


def reply_items(raw: str) -> list[JsonValue]:
    try:
        document = json.loads(json_object_text(raw))
    except (StoryFormatError, json.JSONDecodeError) as error:
        raise SuggestionsUnavailableError(UNUSABLE) from error
    ideas = document.get("ideas") if isinstance(document, dict) else None
    if not isinstance(ideas, list):
        raise SuggestionsUnavailableError(UNUSABLE)
    return ideas


def drawn_titles(numbers: list[int], trends: tuple[TrendingVideo, ...]) -> tuple[str, ...]:
    titles = (trends[number - 1].title for number in numbers if 1 <= number <= len(trends))
    return tuple(dict.fromkeys(titles))


def addresses_children(reply: IdeaReply, audience: TemplateAudience) -> bool:
    texts = [reply.name, reply.description, reply.reason]
    return audience is TemplateAudience.GENERAL and bool(child_terms_in_any(texts))


def parsed_idea(item: JsonValue, brief: SuggestionBrief) -> SuggestedIdea | None:
    try:
        reply = IdeaReply.model_validate(item)
        definition = NarratedDefinition.model_validate(reply.definition)
    except ValidationError:
        return None
    titles = drawn_titles(reply.based_on, brief.trends)
    expert = EXPERT_FIELDS & reply.definition.keys()
    if expert or not titles or addresses_children(reply, brief.audience):
        return None
    return SuggestedIdea(
        name=reply.name,
        description=reply.description,
        reason=reply.reason,
        based_on=titles,
        definition=definition.model_dump(mode="json", exclude_defaults=True),
    )


def parsed_drafts(raw: str, brief: SuggestionBrief) -> SuggestionDrafts:
    found = [parsed_idea(item, brief) for item in reply_items(raw)[: brief.count]]
    ideas = tuple(idea for idea in found if idea is not None)
    return SuggestionDrafts(ideas=ideas, dropped=len(found) - len(ideas))


def written_reply(
    brief: SuggestionBrief, providers: ProviderResolver, writing: SuggestionWriting
) -> str:
    request = suggestion_request(brief, writing)
    try:
        return providers.resolve(Capability.LLM).generate(request)
    except Exception as error:
        raise SuggestionsUnavailableError(UNAVAILABLE) from error


def template_suggestions(
    brief: SuggestionBrief, providers: ProviderResolver, writing: SuggestionWriting
) -> SuggestionDrafts:
    return parsed_drafts(written_reply(brief, providers, writing), brief)

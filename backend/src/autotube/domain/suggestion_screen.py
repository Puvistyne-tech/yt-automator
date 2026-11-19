from __future__ import annotations

import re
from collections.abc import Callable, Sequence

from autotube.domain.json_text import text_leaves
from autotube.domain.pipeline_templates import TemplateAudience, TemplateOrigin, TemplateStatus
from autotube.domain.template_inputs import TemplateInput
from autotube.domain.template_suggestions import (
    SuggestedIdea,
    SuggestionDrafts,
    TemplateSuggestion,
)
from autotube.domain.trends import TrendingVideo

WORD = re.compile(r"\w+")
InputProblems = Callable[[TemplateInput], dict[str, str]]


def suggestion_input(
    engine_id: str, audience: TemplateAudience, idea: SuggestedIdea
) -> TemplateInput:
    return TemplateInput(
        engine=engine_id,
        name=idea.name.strip(),
        description=idea.description.strip(),
        audience=audience,
        status=TemplateStatus.DRAFT,
        origin=TemplateOrigin.SUGGESTED,
        definition=idea.definition,
    )


def phrase_key(text: str) -> str:
    return " ".join(WORD.findall(text.casefold()))


def mentions(text: str, phrase: str) -> bool:
    wanted = phrase_key(phrase)
    return bool(wanted) and f" {wanted} " in f" {phrase_key(text)} "


def idea_texts(idea: SuggestedIdea) -> list[str]:
    return [idea.name, idea.description, idea.reason, *text_leaves(idea.definition)]


def mentioned(texts: Sequence[str], phrases: Sequence[str]) -> list[str]:
    return [phrase for phrase in phrases if any(mentions(text, phrase) for text in texts)]


def copied_channels(idea: SuggestedIdea, trends: Sequence[TrendingVideo]) -> list[str]:
    return mentioned(idea_texts(idea), [video.channel_title for video in trends])


def copied_titles(idea: SuggestedIdea, trends: Sequence[TrendingVideo]) -> list[str]:
    texts = [idea.name, idea.description, *text_leaves(idea.definition)]
    return mentioned(texts, [video.title for video in trends])


def suggestion_of(idea: SuggestedIdea, data: TemplateInput) -> TemplateSuggestion:
    return TemplateSuggestion(
        name=data.name,
        description=data.description,
        reason=idea.reason.strip(),
        based_on=idea.based_on,
        input=data,
    )


def kept_suggestion(
    idea: SuggestedIdea,
    data: TemplateInput,
    trends: Sequence[TrendingVideo],
    problems: InputProblems,
) -> TemplateSuggestion | None:
    if copied_channels(idea, trends) or copied_titles(idea, trends) or problems(data):
        return None
    return suggestion_of(idea, data)


def screened_suggestions(
    drafts: SuggestionDrafts,
    trends: Sequence[TrendingVideo],
    make_input: Callable[[SuggestedIdea], TemplateInput],
    problems: InputProblems,
) -> tuple[tuple[TemplateSuggestion, ...], int]:
    found = [kept_suggestion(idea, make_input(idea), trends, problems) for idea in drafts.ideas]
    kept = tuple(suggestion for suggestion in found if suggestion is not None)
    return kept, drafts.dropped + len(found) - len(kept)

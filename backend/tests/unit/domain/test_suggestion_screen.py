from __future__ import annotations

from functools import partial
from typing import Any

import pytest
from pydantic import ValidationError

from autotube.domain.pipeline_templates import TemplateAudience, TemplateOrigin, TemplateStatus
from autotube.domain.suggestion_screen import (
    copied_channels,
    mentions,
    screened_suggestions,
    suggestion_input,
)
from autotube.domain.template_inputs import TemplateInput
from autotube.domain.template_suggestions import (
    SUGGESTION_COUNT_MAX,
    SuggestedIdea,
    SuggestionDrafts,
    SuggestionRequest,
)
from autotube.domain.trends import TrendingVideo

TRENDS = (
    TrendingVideo(title="Pantry dinners", channel_title="Weeknight Kitchen"),
    TrendingVideo(title="Sunset colours", channel_title="Curious Lab"),
    TrendingVideo(title="Untitled", channel_title=""),
)
REFUSED = "refused"


def idea(**changes: Any) -> SuggestedIdea:
    fields: dict[str, Any] = {
        "name": " Cupboard cooking ",
        "description": "Quick meals from what is at home",
        "reason": "Short practical cooking is popular",
        "based_on": ("Pantry dinners",),
        "definition": {"brief": "meals from the cupboard", "topics": ["rice", "beans"]},
    }
    return SuggestedIdea.model_validate(fields | changes)


def refusing(data: TemplateInput) -> dict[str, str]:
    return {"definition.brief": "no"} if data.definition.get("brief") == REFUSED else {}


def screen(*ideas: SuggestedIdea, dropped: int = 0) -> tuple[Any, int]:
    drafts = SuggestionDrafts(ideas=ideas, dropped=dropped)
    make = partial(suggestion_input, "sample", TemplateAudience.GENERAL)
    return screened_suggestions(drafts, TRENDS, make, refusing)


def test_a_suggestion_input_is_a_suggested_draft_with_a_trimmed_name() -> None:
    data = suggestion_input("sample", TemplateAudience.KIDS, idea())
    assert (data.engine, data.name, data.audience) == ("sample", "Cupboard cooking", "kids")
    assert (data.status, data.origin) == (TemplateStatus.DRAFT, TemplateOrigin.SUGGESTED)
    assert data.definition == idea().definition


@pytest.mark.parametrize(
    ("text", "phrase", "found"),
    [
        ("Inspired by curious lab videos", "Curious Lab", True),
        ("A CURIOUS-LAB style", "Curious Lab", True),
        ("Curious laboratories", "Curious Lab", False),
        ("anything", "", False),
    ],
)
def test_mentions_match_whole_words_without_case(text: str, phrase: str, found: bool) -> None:
    assert mentions(text, phrase) is found


@pytest.mark.parametrize(
    "changes",
    [
        {"name": "Weeknight Kitchen Junior"},
        {"description": "Like curious lab, but shorter"},
        {"reason": "Weeknight Kitchen does well"},
        {"definition": {"topics": ["the curious lab way"]}},
    ],
)
def test_a_trending_channel_title_anywhere_in_an_idea_is_a_copy(changes: dict[str, Any]) -> None:
    assert copied_channels(idea(**changes), TRENDS)


def test_an_original_idea_copies_no_channel() -> None:
    assert copied_channels(idea(), TRENDS) == []


def test_screening_keeps_good_ideas_and_counts_the_rest() -> None:
    copy = idea(name="Curious Lab facts")
    refused = idea(definition={"brief": REFUSED})
    kept, dropped = screen(idea(), copy, refused, dropped=2)
    [suggestion] = kept
    assert (suggestion.name, suggestion.reason, suggestion.based_on) == (
        "Cupboard cooking",
        "Short practical cooking is popular",
        ("Pantry dinners",),
    )
    assert suggestion.input.origin is TemplateOrigin.SUGGESTED
    assert dropped == 4


@pytest.mark.parametrize(
    "fields",
    [{"region": "gb"}, {"count": 0}, {"count": SUGGESTION_COUNT_MAX + 1}, {"category": "x"}],
)
def test_a_suggestion_request_refuses_bad_fields(fields: dict[str, Any]) -> None:
    base = {"engine": "sample", "audience": "general", "region": "GB"}
    with pytest.raises(ValidationError):
        SuggestionRequest.model_validate(base | fields)


def test_a_suggestion_request_defaults_to_five_ideas_from_every_category() -> None:
    request = SuggestionRequest(engine="sample", audience=TemplateAudience.KIDS, region="IN")
    assert (request.count, request.category) == (5, None)

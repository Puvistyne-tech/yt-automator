from __future__ import annotations

from typing import Any

import pytest

from autotube.domain.pipeline_templates import TemplateAudience, TemplateOrigin, TemplateStatus
from autotube.domain.suggestion_screen import (
    copied_channels,
    copied_titles,
    mentions,
    suggestion_input,
)
from autotube.domain.template_suggestions import SuggestedIdea
from autotube.domain.trends import TrendingVideo

TRENDS = (
    TrendingVideo(title="Pantry dinners", channel_title="Weeknight Kitchen"),
    TrendingVideo(title="Sunset colours", channel_title="Curious Lab"),
    TrendingVideo(title="Untitled", channel_title=""),
)


def idea(**changes: Any) -> SuggestedIdea:
    fields: dict[str, Any] = {
        "name": " Cupboard cooking ",
        "description": "Quick meals from what is at home",
        "reason": "Short practical cooking is popular",
        "based_on": ("Pantry dinners",),
        "definition": {"brief": "meals from the cupboard", "topics": ["rice", "beans"]},
    }
    return SuggestedIdea.model_validate(fields | changes)


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


@pytest.mark.parametrize(
    "changes",
    [
        {"name": "pantry DINNERS"},
        {"description": "Our take on Sunset colours"},
        {"definition": {"brief": "Like pantry dinners, at home"}},
    ],
)
def test_a_whole_trending_title_in_the_name_description_or_definition_is_a_copy(
    changes: dict[str, Any],
) -> None:
    assert copied_titles(idea(**changes), TRENDS)


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"reason": "Pantry dinners shows quick cooking is popular"},
        {"name": "Sunset"},
    ],
)
def test_a_cited_or_partial_title_is_not_a_copy(changes: dict[str, Any]) -> None:
    assert copied_titles(idea(**changes), TRENDS) == []

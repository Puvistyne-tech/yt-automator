from __future__ import annotations

import pytest
from pydantic import ValidationError

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.domain.template_suggestions import SuggestionPolicy, SuggestionRequest


def test_a_suggestion_request_defaults_to_five_ideas_from_every_category() -> None:
    request = SuggestionRequest(engine="sample", audience=TemplateAudience.KIDS, region="IN")
    assert (request.count, request.category) == (5, None)


@pytest.mark.parametrize("limit", [0, 51])
def test_the_trend_limit_stays_within_one_chart_page(limit: int) -> None:
    with pytest.raises(ValidationError):
        SuggestionPolicy(trend_limit=limit)


@pytest.mark.parametrize("limit", [1, 50])
def test_the_trend_limit_accepts_its_bounds(limit: int) -> None:
    assert SuggestionPolicy(trend_limit=limit).trend_limit == limit

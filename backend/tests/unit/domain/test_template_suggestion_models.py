from __future__ import annotations

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.domain.template_suggestions import SuggestionRequest


def test_a_suggestion_request_defaults_to_five_ideas_from_every_category() -> None:
    request = SuggestionRequest(engine="sample", audience=TemplateAudience.KIDS, region="IN")
    assert (request.count, request.category) == (5, None)

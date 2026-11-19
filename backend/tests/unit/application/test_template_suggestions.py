from __future__ import annotations

from typing import Any

import pytest

from autotube.domain.pipeline_templates import TemplateAudience, TemplateOrigin, TemplateStatus
from autotube.domain.runs import RunQuery
from autotube.domain.template_suggestions import SuggestionDrafts, SuggestionRequest
from autotube.domain.trends import TrendingVideo, TrendOrigin
from autotube.shared.errors import RuleConflict, ValidationFailed
from tests.fixtures.builders import add_channel, add_credential
from tests.fixtures.fake_engines import (
    REFUSED_BRIEF,
    FakeEngine,
    FakeEngineCatalog,
    suggested_drafts,
    suggested_idea,
)
from tests.fixtures.harness import Harness
from tests.fixtures.suggestion_data import TRENDS
from tests.fixtures.template_rig import TemplateRig

KIDS_TREND = TrendingVideo(title="Counting ducks", channel_title="Pond Pals", made_for_kids=True)


def request(**changes: Any) -> SuggestionRequest:
    fields: dict[str, Any] = {"engine": "sample", "audience": "general", "region": "GB"}
    return SuggestionRequest.model_validate(fields | changes)


def rig_with(harness: Harness, drafts: SuggestionDrafts | None) -> TemplateRig:
    engine = FakeEngine(suggestions=drafts)
    return TemplateRig(harness, engines=FakeEngineCatalog([engine]))


def engine_of(rig: TemplateRig) -> FakeEngine:
    engine = rig.engines.get("sample")
    assert isinstance(engine, FakeEngine)
    return engine


def assert_nothing_stored(rig: TemplateRig) -> None:
    assert rig.templates.list() == []
    assert rig.harness.runs.list(RunQuery()) == []


def test_suggestions_from_the_sample_are_suggested_drafts(rig: TemplateRig) -> None:
    result = rig.suggest().execute(request(category="26", count=3))
    [suggestion] = result.suggestions
    assert (result.source, result.dropped) == (TrendOrigin.SAMPLE, 0)
    assert (suggestion.name, suggestion.reason, suggestion.based_on) == (
        "Star facts",
        "Space videos are popular",
        ("Night sky",),
    )
    data = suggestion.input
    assert (data.engine, data.audience, data.status, data.origin) == (
        "sample",
        TemplateAudience.GENERAL,
        TemplateStatus.DRAFT,
        TemplateOrigin.SUGGESTED,
    )
    [query] = rig.trends.queries
    assert (query.region, query.category, query.limit) == ("GB", "26", 25)
    [brief] = engine_of(rig).briefs
    assert (brief.count, brief.trends) == (3, TRENDS)
    assert_nothing_stored(rig)


def test_a_connected_channel_supplies_youtube_trends(rig: TemplateRig) -> None:
    add_credential(rig.harness)
    add_channel(rig.harness)
    result = rig.suggest().execute(request(audience="kids"))
    [brief] = engine_of(rig).briefs
    assert result.source is TrendOrigin.YOUTUBE
    assert brief.trends == tuple(rig.harness.youtube.popular)


def test_general_requests_never_pass_made_for_kids_trends(rig: TemplateRig) -> None:
    rig.trends.videos.append(KIDS_TREND)
    rig.suggest().execute(request())
    [brief] = engine_of(rig).briefs
    assert KIDS_TREND not in brief.trends


def test_a_general_request_with_only_kids_trends_is_unavailable(rig: TemplateRig) -> None:
    rig.trends.videos[:] = [KIDS_TREND]
    with pytest.raises(RuleConflict) as conflict:
        rig.suggest().execute(request())
    assert conflict.value.code == "suggestions_unavailable"
    assert engine_of(rig).briefs == []


def test_failing_and_copied_ideas_are_dropped_and_counted(harness: Harness) -> None:
    drafts = suggested_drafts(
        suggested_idea(),
        suggested_idea("Curious Lab minis"),
        suggested_idea("Refused", definition={"brief": REFUSED_BRIEF}),
        suggested_idea(" "),
        dropped=2,
    )
    result = rig_with(harness, drafts).suggest().execute(request())
    assert [s.name for s in result.suggestions] == ["Star facts"]
    assert result.dropped == 5


def test_nothing_usable_is_a_suggestions_unavailable_conflict(harness: Harness) -> None:
    drafts = suggested_drafts(suggested_idea("Weeknight Kitchen remix"), dropped=1)
    with pytest.raises(RuleConflict) as conflict:
        rig_with(harness, drafts).suggest().execute(request())
    assert conflict.value.code == "suggestions_unavailable"
    assert conflict.value.message.startswith("None of the suggested ideas passed")


def test_an_unavailable_writer_is_a_suggestions_unavailable_conflict(harness: Harness) -> None:
    rig = rig_with(harness, None)
    with pytest.raises(RuleConflict) as conflict:
        rig.suggest().execute(request())
    assert (conflict.value.code, conflict.value.message) == (
        "suggestions_unavailable",
        "the writer is resting",
    )
    assert_nothing_stored(rig)


def test_an_unknown_engine_is_a_field_error(rig: TemplateRig) -> None:
    with pytest.raises(ValidationFailed) as refused:
        rig.suggest().execute(request(engine="missing"))
    assert list(refused.value.fields) == ["engine"]
    assert rig.trends.queries == []


def test_the_saved_provider_chain_is_used(rig: TemplateRig) -> None:
    rig.suggest().execute(request())
    assert rig.harness.catalog.resolved_with == [rig.harness.provider_configs.list()]


def test_a_suggestion_can_be_created_as_returned(rig: TemplateRig) -> None:
    [suggestion] = rig.suggest().execute(request()).suggestions
    created = rig.create().execute(suggestion.input)
    assert (created.origin, created.status) == (TemplateOrigin.SUGGESTED, TemplateStatus.DRAFT)

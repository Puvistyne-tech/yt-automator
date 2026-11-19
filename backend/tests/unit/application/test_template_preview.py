from __future__ import annotations

from typing import Any

import pytest

from autotube.domain.pipeline_templates import TemplateStatus
from autotube.domain.runs import RunQuery
from autotube.domain.sample_scripts import TemplatePreviewInput
from autotube.shared.errors import RuleConflict, ValidationFailed
from tests.fixtures.fake_engines import REFUSED_BRIEF, UNAVAILABLE_TOPIC, FakeEngine
from tests.fixtures.template_rig import TemplateRig, template_input


def preview_input(**changes: Any) -> TemplatePreviewInput:
    fields = template_input().model_dump() | changes
    return TemplatePreviewInput.model_validate(fields)


def sample_engine(rig: TemplateRig) -> FakeEngine:
    engine = rig.engines.get("sample")
    assert isinstance(engine, FakeEngine)
    return engine


def assert_nothing_stored(rig: TemplateRig) -> None:
    assert rig.templates.list() == []
    assert rig.harness.runs.list(RunQuery()) == []


def test_a_preview_writes_a_sample_in_the_first_language_by_default(rig: TemplateRig) -> None:
    sample = rig.preview().execute(preview_input())
    assert (sample.language, sample.title, sample.provider) == (
        "en",
        "Space facts: planets",
        "fake-llm",
    )
    [(template, language, topic)] = sample_engine(rig).samples
    assert (template.name, template.definition, language, topic) == (
        "Space facts",
        {"brief": "planets"},
        "en",
        "",
    )
    assert_nothing_stored(rig)


def test_a_preview_uses_the_chosen_language_and_topic(rig: TemplateRig) -> None:
    sample = rig.preview().execute(preview_input(language="ta", topic="comets"))
    assert (sample.language, sample.title) == ("ta", "Space facts: comets")


@pytest.mark.parametrize("status", list(TemplateStatus))
def test_a_preview_works_the_same_for_draft_and_ready_input(
    rig: TemplateRig, status: TemplateStatus
) -> None:
    sample = rig.preview().execute(preview_input(status=status))
    [(template, _, _)] = sample_engine(rig).samples
    assert (sample.title, template.status) == ("Space facts: planets", status)
    assert_nothing_stored(rig)


def test_a_preview_resolves_the_saved_provider_chain(rig: TemplateRig) -> None:
    rig.preview().execute(preview_input())
    assert rig.harness.catalog.resolved_with == [rig.harness.provider_configs.list()]


@pytest.mark.parametrize(
    ("changes", "fields"),
    [
        ({"name": " ", "origin": "builtin"}, ["name", "origin"]),
        ({"definition": {"brief": REFUSED_BRIEF}}, ["definition.brief"]),
        ({"engine": "missing"}, ["engine"]),
        ({"language": "fr"}, ["language"]),
    ],
)
def test_a_preview_reports_the_same_field_errors_as_create(
    rig: TemplateRig, changes: dict[str, Any], fields: list[str]
) -> None:
    with pytest.raises(ValidationFailed) as refused:
        rig.preview().execute(preview_input(**changes))
    assert sorted(refused.value.fields) == fields
    assert sample_engine(rig).samples == []
    assert_nothing_stored(rig)


def test_an_unavailable_writer_is_a_preview_unavailable_conflict(rig: TemplateRig) -> None:
    with pytest.raises(RuleConflict) as conflict:
        rig.preview().execute(preview_input(topic=UNAVAILABLE_TOPIC))
    assert (conflict.value.code, conflict.value.message) == (
        "preview_unavailable",
        "the writer is resting",
    )
    assert_nothing_stored(rig)

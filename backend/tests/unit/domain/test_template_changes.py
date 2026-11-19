from __future__ import annotations

import pytest

from autotube.domain.automations import Automation
from autotube.domain.deletion_rules import automations_using, ensure_template_deletable
from autotube.domain.pipeline_templates import PipelineTemplate, TemplateOrigin, TemplateStatus
from autotube.domain.template_rules import (
    NAME_MAX_LENGTH,
    copy_name,
    engine_change_errors,
    ensure_draft_allowed,
    missing_engine_errors,
    origin_errors,
)
from autotube.domain.template_views import engine_summary, template_summary
from autotube.shared.errors import RuleConflict
from tests.fixtures.fake_engines import FakeEngine
from tests.fixtures.template_records import template

DRAFT = template(status=TemplateStatus.DRAFT)


def using(automation: Automation, name: str, type_id: str = "t_tpl-1") -> Automation:
    return automation.model_copy(update={"name": name, "pipeline_type": type_id})


def test_automations_using_a_type_are_named_in_order(automation: Automation) -> None:
    found = [using(automation, "b"), using(automation, "a"), using(automation, "c", "fake")]
    assert automations_using("t_tpl-1", found) == ["a", "b"]


def test_a_template_in_use_cannot_be_deleted(automation: Automation) -> None:
    with pytest.raises(RuleConflict, match="Comets") as raised:
        ensure_template_deletable(template(), [using(automation, "Comets")])
    assert raised.value.code == "template_in_use"
    ensure_template_deletable(template(), [automation])


@pytest.mark.parametrize(
    ("current", "proposed", "users", "refused"),
    [
        (template(), DRAFT, ["Comets"], True),
        (template(), DRAFT, [], False),
        (template(), template(), ["Comets"], False),
        (DRAFT, DRAFT, ["Comets"], False),
    ],
    ids=["ready-to-draft-in-use", "unused", "stays-ready", "already-draft"],
)
def test_only_an_in_use_ready_template_cannot_become_a_draft(
    current: PipelineTemplate, proposed: PipelineTemplate, users: list[str], refused: bool
) -> None:
    if not refused:
        ensure_draft_allowed(current, proposed, users)
        return
    with pytest.raises(RuleConflict, match="stay ready") as raised:
        ensure_draft_allowed(current, proposed, users)
    assert raised.value.code == "template_in_use"


def test_engine_and_origin_errors() -> None:
    assert engine_change_errors(template(), "narrated_video") == {}
    assert list(engine_change_errors(template(), "other")) == ["engine"]
    assert missing_engine_errors("gone") == {"engine": "engine 'gone' is not installed"}
    assert list(origin_errors(TemplateOrigin.BUILTIN)) == ["origin"]
    assert origin_errors(TemplateOrigin.SUGGESTED) == {}


@pytest.mark.parametrize(
    ("name", "expected"),
    [("Facts", "Facts (copy)"), ("x" * NAME_MAX_LENGTH, f"{'x' * 73} (copy)")],
)
def test_copy_names_fit_the_limit(name: str, expected: str) -> None:
    assert copy_name(name, " (copy)") == expected
    assert len(expected) <= NAME_MAX_LENGTH


def test_summaries_carry_usage_and_engine_forms(automation: Automation) -> None:
    summary = template_summary(template(), [using(automation, "a"), automation])
    assert (summary.builtin, summary.automations_using, summary.id) == (False, 1, "tpl-1")
    engine = engine_summary(FakeEngine())
    assert sorted(engine.model_dump(mode="json")["blank"]) == ["general", "kids"]

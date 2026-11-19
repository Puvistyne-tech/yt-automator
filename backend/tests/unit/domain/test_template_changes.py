from __future__ import annotations

from datetime import timedelta

import pytest

from autotube.domain.automations import Automation
from autotube.domain.copy_names import COPY_NAME_SUFFIX, copy_name
from autotube.domain.deletion_rules import ensure_template_deletable
from autotube.domain.pipeline_templates import TemplateOrigin, TemplateStatus
from autotube.domain.run_enums import RunStatus
from autotube.domain.runs import Run
from autotube.domain.template_rules import (
    NAME_MAX_LENGTH,
    ensure_draft_allowed,
    found_template,
    missing_engine_errors,
    origin_errors,
    taken_type_ids,
)
from autotube.domain.template_usage import automations_using, is_open_run, runs_using
from autotube.domain.template_views import template_summary
from autotube.shared.errors import RuleConflict
from tests.fixtures.fake_runtime import START
from tests.fixtures.template_records import template

TYPE_ID = "t_tpl-1"
DRAFT = template(status=TemplateStatus.DRAFT)


def using(automation: Automation, name: str, type_id: str = TYPE_ID) -> Automation:
    return automation.model_copy(update={"name": name, "pipeline_type": type_id})


def run(status: RunStatus, run_id: str = "r1", type_id: str = TYPE_ID, **extra: object) -> Run:
    fields = {
        "id": run_id,
        "automation_id": "a1",
        "automation_name": "Bedtime",
        "pipeline_type": type_id,
        "languages": ("en",),
        "settings_snapshot": {},
        "status": status,
        "created_at": START,
    }
    return Run.model_validate(fields | extra)


def test_automations_using_a_type_include_disabled_ones_in_name_order(
    automation: Automation,
) -> None:
    disabled = using(automation, "b").model_copy(update={"enabled": False})
    found = [disabled, using(automation, "a"), using(automation, "c", "fake")]
    assert automations_using(TYPE_ID, found) == ["a", "b"]


@pytest.mark.parametrize(
    ("made", "open_run"),
    [
        (run(RunStatus.QUEUED), True),
        (run(RunStatus.RUNNING), True),
        (run(RunStatus.PUBLISHING), True),
        (run(RunStatus.AWAITING_REVIEW), True),
        (run(RunStatus.APPROVED), True),
        (run(RunStatus.FAILED, retry_at=START + timedelta(minutes=5)), True),
        (run(RunStatus.FAILED), False),
        (run(RunStatus.REJECTED), False),
        (run(RunStatus.PUBLISHED), False),
        (run(RunStatus.CANCELLED), False),
    ],
    ids=lambda value: value.status.value if isinstance(value, Run) else str(value),
)
def test_open_runs_are_unfinished_or_unpublished(made: Run, open_run: bool) -> None:
    assert is_open_run(made) is open_run


def test_runs_using_a_type_are_its_open_runs_in_id_order() -> None:
    runs = [
        run(RunStatus.APPROVED, "r2"),
        run(RunStatus.AWAITING_REVIEW, "r1"),
        run(RunStatus.PUBLISHED, "r3"),
        run(RunStatus.QUEUED, "r4", "fake"),
    ]
    assert runs_using(TYPE_ID, runs) == ["r1", "r2"]


def test_a_template_with_automations_or_open_runs_cannot_be_deleted(
    automation: Automation,
) -> None:
    with pytest.raises(RuleConflict, match="automations: Comets and open runs: r1") as raised:
        ensure_template_deletable(
            TYPE_ID, [using(automation, "Comets")], [run(RunStatus.AWAITING_REVIEW)]
        )
    assert raised.value.code == "template_in_use"
    with pytest.raises(RuleConflict, match="used by open runs: r1;"):
        ensure_template_deletable(TYPE_ID, [automation], [run(RunStatus.APPROVED)])
    ensure_template_deletable(TYPE_ID, [automation], [run(RunStatus.PUBLISHED)])


def test_a_ready_template_in_use_cannot_become_a_draft(automation: Automation) -> None:
    with pytest.raises(RuleConflict, match="stay ready") as by_automation:
        ensure_draft_allowed(template(), DRAFT, [using(automation, "Comets")], [])
    with pytest.raises(RuleConflict, match="open runs: r1") as by_run:
        ensure_draft_allowed(template(), DRAFT, [], [run(RunStatus.AWAITING_REVIEW)])
    assert {by_automation.value.code, by_run.value.code} == {"template_in_use"}


def test_other_status_changes_are_allowed_while_in_use(automation: Automation) -> None:
    users = [using(automation, "Comets")]
    runs = [run(RunStatus.APPROVED)]
    ensure_draft_allowed(template(), template(), users, runs)
    ensure_draft_allowed(DRAFT, DRAFT, users, runs)
    ensure_draft_allowed(DRAFT, template(), users, runs)
    ensure_draft_allowed(template(), DRAFT, [automation], [run(RunStatus.PUBLISHED)])


def test_builtins_win_the_lookup_and_reserve_their_type_ids() -> None:
    builtin = template("kids_story", type_id="kids_story", origin=TemplateOrigin.BUILTIN)
    stored = template("kids_story")
    assert found_template("kids_story", [builtin], stored) == builtin
    assert found_template("tpl-1", [builtin], stored) == stored
    assert found_template("tpl-1", [builtin], None) is None
    assert taken_type_ids(["fake"], [builtin]) == {"fake", "kids_story"}


def test_engine_and_origin_errors() -> None:
    assert missing_engine_errors("gone") == {"engine": "engine 'gone' is not installed"}
    assert list(origin_errors(TemplateOrigin.BUILTIN)) == ["origin"]
    assert origin_errors(TemplateOrigin.SUGGESTED) == {}


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Facts", "Facts (copy)"),
        ("x" * 73, f"{'x' * 73} (copy)"),
        ("x" * 74, f"{'x' * 73} (copy)"),
        (f"{'x' * 72} yz", f"{'x' * 72} (copy)"),
    ],
    ids=["short", "73-fits", "74-cut", "cut-on-space"],
)
def test_copy_names_fit_the_limit(name: str, expected: str) -> None:
    made = copy_name(name, NAME_MAX_LENGTH)
    assert made == expected
    assert made.endswith(COPY_NAME_SUFFIX) and len(made) <= NAME_MAX_LENGTH


def test_summaries_count_every_automation_using_the_template(automation: Automation) -> None:
    disabled = using(automation, "b").model_copy(update={"enabled": False})
    summary = template_summary(template(), [using(automation, "a"), disabled, automation])
    assert (summary.builtin, summary.automations_using, summary.id) == (False, 2, "tpl-1")

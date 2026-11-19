from __future__ import annotations

from typing import Any

import pytest

from autotube.domain.pipeline_templates import TemplateAudience, TemplateOrigin, TemplateStatus
from autotube.domain.run_enums import RunStatus
from autotube.shared.errors import RuleConflict, ValidationFailed
from tests.fixtures.fake_engines import BUILTIN_TYPE, FIXED_KEY, REFUSED_BRIEF
from tests.fixtures.template_records import template
from tests.fixtures.template_rig import TemplateRig, template_input

DRAFT = TemplateStatus.DRAFT


def test_update_revises_the_editable_fields(rig: TemplateRig) -> None:
    created = rig.created()
    later = rig.harness.clock.advance(hours=1)
    changes = {"name": " Moon facts ", "description": "Moon", "definition": {"length": "long"}}
    updated = rig.update().execute(created.id, template_input(**changes))
    assert (updated.name, updated.description, updated.definition) == (
        "Moon facts",
        "Moon",
        {"length": "long"},
    )
    assert (updated.id, updated.type_id, updated.origin, updated.revision) == (
        created.id,
        created.type_id,
        TemplateOrigin.BLANK,
        2,
    )
    assert (updated.created_at, updated.updated_at) == (created.created_at, later)
    assert rig.get().execute(created.id) == updated


def test_update_keeps_the_stored_origin(rig: TemplateRig) -> None:
    created = rig.created()
    updated = rig.update().execute(created.id, template_input(origin=TemplateOrigin.SUGGESTED))
    assert updated.origin is TemplateOrigin.BLANK


def test_update_refuses_builtins(rig: TemplateRig) -> None:
    with pytest.raises(RuleConflict) as raised:
        rig.update().execute(BUILTIN_TYPE, template_input())
    assert raised.value.code == "template_builtin"


@pytest.mark.parametrize(
    ("changes", "fields"),
    [
        ({"audience": TemplateAudience.KIDS}, ["audience"]),
        ({"engine": "other"}, ["engine"]),
        ({"name": " ", "definition": {"brief": REFUSED_BRIEF}}, ["definition.brief", "name"]),
        ({"name": "x" * 81}, ["name"]),
        ({"definition": {"brief": "planets", FIXED_KEY: "moved"}}, [f"definition.{FIXED_KEY}"]),
    ],
    ids=["audience", "engine", "name-and-definition", "81-characters", "engine-fixed-field"],
)
def test_update_reports_field_errors_and_keeps_the_template(
    rig: TemplateRig, changes: dict[str, Any], fields: list[str]
) -> None:
    created = rig.created()
    with pytest.raises(ValidationFailed) as raised:
        rig.update().execute(created.id, template_input(**changes))
    assert sorted(raised.value.fields) == fields
    assert rig.get().execute(created.id) == created


def test_update_of_a_template_whose_engine_is_gone_names_the_engine(rig: TemplateRig) -> None:
    rig.templates.add(template(engine="retired"))
    with pytest.raises(ValidationFailed) as raised:
        rig.update().execute("tpl-1", template_input(engine="retired"))
    assert raised.value.fields == {"engine": "engine 'retired' is not installed"}


def test_ready_to_draft_is_refused_while_an_automation_uses_it(rig: TemplateRig) -> None:
    created = rig.created()
    rig.automation_using(created.type_id, "Comets")
    with pytest.raises(RuleConflict, match="Comets") as raised:
        rig.update().execute(created.id, template_input(status=DRAFT))
    assert raised.value.code == "template_in_use"
    renamed = rig.update().execute(created.id, template_input(name="Still ready"))
    assert (renamed.status, renamed.automations_using) == (TemplateStatus.READY, 1)


def test_a_disabled_automation_still_uses_the_template(rig: TemplateRig) -> None:
    created = rig.created()
    using = rig.automation_using(created.type_id, "Paused")
    rig.harness.automations.save(using.model_copy(update={"enabled": False}))
    assert rig.get().execute(created.id).automations_using == 1
    with pytest.raises(RuleConflict, match="Paused"):
        rig.update().execute(created.id, template_input(status=DRAFT))
    with pytest.raises(RuleConflict, match="Paused"):
        rig.delete().execute(created.id)


def test_a_kids_template_with_an_open_run_stays_after_its_automation_moves(
    rig: TemplateRig,
) -> None:
    created = rig.created(audience=TemplateAudience.KIDS)
    automation = rig.automation_using(created.type_id, "Bedtime")
    run = rig.run_using(created.type_id, RunStatus.AWAITING_REVIEW)
    rig.harness.automations.save(automation.model_copy(update={"pipeline_type": "fake"}))
    assert rig.get().execute(created.id).automations_using == 0
    with pytest.raises(RuleConflict, match=f"open runs: {run.id}") as deleting:
        rig.delete().execute(created.id)
    with pytest.raises(RuleConflict, match=f"open runs: {run.id}") as drafting:
        rig.update().execute(created.id, template_input(audience="kids", status=DRAFT))
    assert {deleting.value.code, drafting.value.code} == {"template_in_use"}
    assert rig.templates.get(created.id) is not None


def test_ready_to_draft_is_allowed_when_unused(rig: TemplateRig) -> None:
    created = rig.created()
    rig.run_using(created.type_id, RunStatus.PUBLISHED)
    drafted = rig.update().execute(created.id, template_input(status=DRAFT))
    assert drafted.status is DRAFT
    readied = rig.update().execute(created.id, template_input())
    assert (readied.status, readied.revision) == (TemplateStatus.READY, 3)

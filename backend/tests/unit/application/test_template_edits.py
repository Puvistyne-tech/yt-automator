from __future__ import annotations

from typing import Any

import pytest

from autotube.domain.pipeline_templates import TemplateAudience, TemplateOrigin, TemplateStatus
from autotube.shared.errors import NotFound, RuleConflict, ValidationFailed
from tests.fixtures.fake_engines import BUILTIN_TYPE, ENGINE_ID, REFUSED_BRIEF
from tests.fixtures.harness import Harness
from tests.fixtures.template_records import template
from tests.fixtures.template_rig import TemplateRig, template_input


@pytest.fixture
def rig(harness: Harness) -> TemplateRig:
    return TemplateRig(harness)


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
    ],
    ids=["audience", "engine", "name-and-definition"],
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


def test_ready_to_draft_is_refused_while_automations_use_it(rig: TemplateRig) -> None:
    created = rig.created()
    rig.automation_using(created.type_id, "Comets")
    with pytest.raises(RuleConflict, match="Comets") as raised:
        rig.update().execute(created.id, template_input(status=TemplateStatus.DRAFT))
    assert raised.value.code == "template_in_use"
    assert rig.get().execute(created.id) == created.model_copy(update={"automations_using": 1})
    renamed = rig.update().execute(created.id, template_input(name="Still ready"))
    assert (renamed.status, renamed.automations_using) == (TemplateStatus.READY, 1)


def test_ready_to_draft_is_allowed_when_unused(rig: TemplateRig) -> None:
    created = rig.created()
    drafted = rig.update().execute(created.id, template_input(status=TemplateStatus.DRAFT))
    assert drafted.status is TemplateStatus.DRAFT
    readied = rig.update().execute(created.id, template_input())
    assert (readied.status, readied.revision) == (TemplateStatus.READY, 3)


def test_delete_removes_an_unused_template(rig: TemplateRig) -> None:
    created = rig.created()
    rig.delete().execute(created.id)
    assert rig.templates.list() == []
    with pytest.raises(NotFound):
        rig.delete().execute(created.id)


def test_delete_refuses_builtins_and_templates_in_use(rig: TemplateRig) -> None:
    created = rig.created()
    rig.automation_using(created.type_id, "Night sky")
    rig.automation_using(created.type_id, "Comets")
    with pytest.raises(RuleConflict, match="Comets, Night sky") as in_use:
        rig.delete().execute(created.id)
    with pytest.raises(RuleConflict) as builtin:
        rig.delete().execute(BUILTIN_TYPE)
    assert (in_use.value.code, builtin.value.code) == ("template_in_use", "template_builtin")
    assert [t.id for t in rig.templates.list()] == [created.id]


def test_duplicate_of_a_builtin_is_a_fresh_draft_with_its_definition(rig: TemplateRig) -> None:
    copy = rig.duplicate().execute(BUILTIN_TYPE)
    [builtin] = rig.engines.list()[0].builtin_templates()
    assert (copy.id, copy.type_id, copy.name, copy.engine) == (
        "id-1",
        "t_id-1",
        "Sample (copy)",
        ENGINE_ID,
    )
    assert (copy.origin, copy.status, copy.revision, copy.builtin) == (
        TemplateOrigin.DUPLICATE,
        TemplateStatus.DRAFT,
        1,
        False,
    )
    assert (copy.definition, copy.audience) == (builtin.definition, builtin.audience)
    assert rig.templates.get("id-1") is not None


def test_duplicate_takes_a_new_name_and_audience(rig: TemplateRig) -> None:
    created = rig.created()
    rig.update().execute(created.id, template_input(name="Moon"))
    copy = rig.duplicate().execute(created.id, " Kids moon ", TemplateAudience.KIDS)
    assert (copy.name, copy.audience, copy.revision) == ("Kids moon", TemplateAudience.KIDS, 1)
    assert copy.created_at == rig.harness.clock.now()


def test_duplicate_keeps_a_long_name_within_the_limit(rig: TemplateRig) -> None:
    created = rig.created(name="x" * 80)
    copy = rig.duplicate().execute(created.id)
    assert copy.name == f"{'x' * 73} (copy)"


def test_duplicate_reports_a_blank_name_and_engine_problems(rig: TemplateRig) -> None:
    rig.templates.add(template(engine=ENGINE_ID, definition={"brief": REFUSED_BRIEF}))
    with pytest.raises(ValidationFailed) as blank:
        rig.duplicate().execute("tpl-1", "  ")
    with pytest.raises(ValidationFailed) as refused:
        rig.duplicate().execute("tpl-1")
    assert (list(blank.value.fields), list(refused.value.fields)) == (
        ["name"],
        ["definition.brief"],
    )
    assert [t.id for t in rig.templates.list()] == ["tpl-1"]
    with pytest.raises(NotFound):
        rig.duplicate().execute("missing")

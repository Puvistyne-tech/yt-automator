from __future__ import annotations

import pytest

from autotube.domain.pipeline_templates import TemplateAudience, TemplateOrigin, TemplateStatus
from autotube.shared.errors import NotFound, RuleConflict, ValidationFailed
from tests.fixtures.fake_engines import BUILTIN_TYPE, ENGINE_ID, REFUSED_BRIEF
from tests.fixtures.fake_pipeline import FakePipeline
from tests.fixtures.template_records import template
from tests.fixtures.template_rig import TemplateRig, template_input


def test_delete_removes_an_unused_template(rig: TemplateRig) -> None:
    created = rig.created()
    rig.delete().execute(created.id)
    assert rig.templates.list() == []
    with pytest.raises(NotFound):
        rig.delete().execute(created.id)


def test_delete_refuses_builtins(rig: TemplateRig) -> None:
    with pytest.raises(RuleConflict) as builtin:
        rig.delete().execute(BUILTIN_TYPE)
    assert builtin.value.code == "template_builtin"


def test_a_stored_row_that_no_longer_decodes_can_be_deleted(rig: TemplateRig) -> None:
    rig.templates.undecodable["broken"] = "t_broken"
    rig.automation_using("t_broken", "Old")
    with pytest.raises(RuleConflict, match="Old"):
        rig.delete().execute("broken")
    rig.harness.automations.items.clear()
    rig.delete().execute("broken")
    assert rig.templates.type_id_of("broken") is None


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


@pytest.mark.parametrize(
    ("source", "requested", "expected"),
    [
        (TemplateAudience.KIDS, TemplateAudience.GENERAL, TemplateAudience.GENERAL),
        (TemplateAudience.KIDS, None, TemplateAudience.KIDS),
    ],
    ids=["kids-to-general", "unchanged"],
)
def test_duplicate_takes_a_new_name_and_audience(
    rig: TemplateRig,
    source: TemplateAudience,
    requested: TemplateAudience | None,
    expected: TemplateAudience,
) -> None:
    created = rig.created(audience=source)
    rig.update().execute(created.id, template_input(name="Moon", audience=source))
    copy = rig.duplicate().execute(created.id, " Moon two ", requested)
    assert (copy.name, copy.audience, copy.revision) == ("Moon two", expected, 1)
    assert copy.created_at == rig.harness.clock.now()


def test_duplicate_of_a_stored_draft_is_a_draft(rig: TemplateRig) -> None:
    created = rig.created(status=TemplateStatus.DRAFT)
    assert rig.duplicate().execute(created.id).status is TemplateStatus.DRAFT


def test_duplicate_reports_names_and_engine_problems(rig: TemplateRig) -> None:
    rig.templates.add(template(engine=ENGINE_ID, definition={"brief": REFUSED_BRIEF}))
    with pytest.raises(ValidationFailed) as blank:
        rig.duplicate().execute("tpl-1", "  ")
    with pytest.raises(ValidationFailed) as long_name:
        rig.duplicate().execute("tpl-1", "x" * 81)
    with pytest.raises(ValidationFailed) as refused:
        rig.duplicate().execute("tpl-1")
    assert [list(e.value.fields) for e in (blank, long_name, refused)] == [
        ["name", "definition.brief"],
        ["name", "definition.brief"],
        ["definition.brief"],
    ]
    assert [t.id for t in rig.templates.list()] == ["tpl-1"]
    with pytest.raises(NotFound):
        rig.duplicate().execute("missing")


def test_duplicate_when_the_engine_is_gone_names_the_engine(rig: TemplateRig) -> None:
    rig.templates.add(template(engine="retired"))
    with pytest.raises(ValidationFailed) as raised:
        rig.duplicate().execute("tpl-1")
    assert list(raised.value.fields) == ["engine"]


def test_duplicate_refuses_a_type_id_already_served(rig: TemplateRig) -> None:
    rig.harness.pipelines.pipelines["t_id-1"] = FakePipeline(type_id="t_id-1")
    with pytest.raises(RuleConflict) as raised:
        rig.duplicate().execute(BUILTIN_TYPE)
    assert raised.value.code == "template_type_taken"
    assert rig.templates.list() == []

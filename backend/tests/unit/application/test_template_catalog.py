from __future__ import annotations

import pytest

from autotube.domain.pipeline_templates import TemplateAudience, TemplateOrigin, TemplateStatus
from autotube.domain.template_inputs import TemplateInput
from autotube.shared.errors import NotFound, RuleConflict, ValidationFailed
from tests.fixtures.fake_engines import BUILTIN_TYPE, REFUSED_BRIEF, SampleDefinition
from tests.fixtures.fake_pipeline import FakePipeline
from tests.fixtures.template_rig import TemplateRig, template_input


def test_engines_list_their_definition_schema_and_blanks(rig: TemplateRig) -> None:
    [engine] = rig.list_engines().execute()
    assert (engine.engine_id, engine.name) == ("sample", "Sample engine")
    assert engine.definition_schema == SampleDefinition.model_json_schema()
    assert engine.definition_ui_schema == {"brief": {"ui:widget": "textarea"}}
    assert set(engine.blank) == set(TemplateAudience)


def test_templates_list_builtins_first_with_their_usage(rig: TemplateRig) -> None:
    created = rig.created()
    rig.automation_using(created.type_id, "Night sky")
    rig.automation_using(created.type_id, "Comets")
    listed = rig.list_templates().execute()
    assert [(t.id, t.builtin, t.automations_using) for t in listed] == [
        (BUILTIN_TYPE, True, 0),
        (created.id, False, 2),
    ]


def test_get_finds_builtins_by_type_id_and_stored_templates_by_id(rig: TemplateRig) -> None:
    created = rig.created()
    assert rig.get().execute(BUILTIN_TYPE).origin is TemplateOrigin.BUILTIN
    assert rig.get().execute(created.id) == created
    with pytest.raises(NotFound) as missing:
        rig.get().execute("missing")
    assert missing.value.code == "template_not_found"


def test_create_assigns_identity_and_stores_the_template(rig: TemplateRig) -> None:
    created = rig.created(name="  Space facts  ")
    stored = rig.templates.get("id-1")
    assert stored is not None
    assert (created.id, created.type_id, created.name, created.revision) == (
        "id-1",
        "t_id-1",
        "Space facts",
        1,
    )
    assert (created.origin, created.builtin, created.automations_using) == (
        TemplateOrigin.BLANK,
        False,
        0,
    )
    assert created.created_at == created.updated_at == rig.harness.clock.now()
    assert stored.model_dump() == created.model_dump(exclude={"builtin", "automations_using"})


def test_create_defaults_to_a_draft(rig: TemplateRig) -> None:
    data = template_input().model_dump(exclude={"status"})
    created = rig.create().execute(TemplateInput.model_validate(data))
    assert created.status is TemplateStatus.DRAFT


@pytest.mark.parametrize(
    ("changes", "fields"),
    [
        ({"name": "  ", "origin": TemplateOrigin.BUILTIN}, ["name", "origin"]),
        ({"name": "x" * 81}, ["name"]),
        (
            {"definition": {"length": "endless", "brief": REFUSED_BRIEF}},
            ["definition.brief", "definition.length"],
        ),
        ({"definition": {"unknown": 1}}, ["definition.unknown"]),
        ({"engine": "missing"}, ["engine"]),
    ],
    ids=[
        "name-and-origin",
        "81-characters",
        "engine-problems",
        "extra-definition-key",
        "unknown-engine",
    ],
)
def test_create_reports_field_errors_and_stores_nothing(
    rig: TemplateRig, changes: dict[str, object], fields: list[str]
) -> None:
    with pytest.raises(ValidationFailed) as raised:
        rig.created(**changes)
    assert sorted(raised.value.fields) == fields
    assert rig.templates.list() == []


def test_create_refuses_a_type_id_already_served(rig: TemplateRig) -> None:
    rig.harness.pipelines.pipelines["t_id-1"] = FakePipeline(type_id="t_id-1")
    with pytest.raises(RuleConflict) as raised:
        rig.created()
    assert raised.value.code == "template_type_taken"
    assert rig.templates.list() == []

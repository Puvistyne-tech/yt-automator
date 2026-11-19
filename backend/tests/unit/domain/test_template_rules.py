from __future__ import annotations

from datetime import timedelta

import pytest

from autotube.domain.pipeline_templates import (
    BUILTIN_RELEASED_AT,
    TemplateAudience,
    TemplateOrigin,
    TemplateStatus,
    builtin_template,
    user_type_id,
)
from autotube.domain.template_rules import (
    NAME_MAX_LENGTH,
    ensure_editable,
    ensure_type_id_free,
    immutable_errors,
    name_errors,
    revised,
    servable,
)
from autotube.shared.errors import RuleConflict, ValidationFailed
from tests.fixtures.fake_runtime import START
from tests.fixtures.template_records import template

LATER = START + timedelta(hours=1)


def test_user_type_ids_are_prefixed_template_ids() -> None:
    assert user_type_id("abc") == "t_abc"


def test_builtin_templates_are_ready_first_revisions() -> None:
    made = builtin_template("narrated_video", "kids_story", "Kids", "", TemplateAudience.KIDS, {})
    assert (made.id, made.type_id, made.origin, made.status) == (
        "kids_story",
        "kids_story",
        TemplateOrigin.BUILTIN,
        TemplateStatus.READY,
    )
    assert (made.revision, made.created_at, made.is_builtin, made.is_ready) == (
        1,
        BUILTIN_RELEASED_AT,
        True,
        True,
    )


def test_a_draft_user_template_is_neither_builtin_nor_ready() -> None:
    draft = template(status=TemplateStatus.DRAFT)
    assert (draft.is_builtin, draft.is_ready) == (False, False)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Facts", {}),
        ("   ", {"name": "name is required"}),
        ("x" * NAME_MAX_LENGTH, {}),
        (
            "x" * (NAME_MAX_LENGTH + 1),
            {"name": f"name must be at most {NAME_MAX_LENGTH} characters"},
        ),
    ],
)
def test_names_are_required_and_limited(name: str, expected: dict[str, str]) -> None:
    assert name_errors(name) == expected


def test_builtin_templates_are_read_only() -> None:
    with pytest.raises(RuleConflict, match="duplicate it") as raised:
        ensure_editable(template(origin=TemplateOrigin.BUILTIN))
    assert raised.value.code == "template_builtin"
    ensure_editable(template())


def test_audience_and_type_id_cannot_change() -> None:
    changed = template(audience=TemplateAudience.KIDS, type_id="t_other")
    assert sorted(immutable_errors(template(), changed)) == ["audience", "type_id"]
    assert immutable_errors(template(), template(name="Renamed")) == {}


def test_taken_type_ids_are_refused() -> None:
    with pytest.raises(RuleConflict, match="'kids_story'") as raised:
        ensure_type_id_free("kids_story", {"kids_story"})
    assert raised.value.code == "template_type_taken"
    ensure_type_id_free("t_new", {"kids_story"})


def test_only_ready_templates_with_a_free_type_id_are_served() -> None:
    assert servable(template(), {"kids_story"})
    assert not servable(template(status=TemplateStatus.DRAFT), set())
    assert not servable(template(type_id="kids_story"), {"kids_story"})


def test_a_revision_keeps_identity_and_counts_up() -> None:
    proposed = template(
        name="Renamed", revision=7, origin=TemplateOrigin.SUGGESTED, created_at=LATER
    )
    updated = revised(template(revision=2), proposed, LATER)
    assert (updated.name, updated.revision, updated.origin) == ("Renamed", 3, TemplateOrigin.BLANK)
    assert (updated.created_at, updated.updated_at) == (START, LATER)


def test_a_revision_refuses_builtins_immutable_changes_and_blank_names() -> None:
    with pytest.raises(RuleConflict):
        revised(template(origin=TemplateOrigin.BUILTIN), template(), LATER)
    with pytest.raises(ValidationFailed) as raised:
        revised(template(), template(name=" ", audience=TemplateAudience.KIDS), LATER)
    assert sorted(raised.value.fields) == ["audience", "name"]

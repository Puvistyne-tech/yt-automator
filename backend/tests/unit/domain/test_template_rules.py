from __future__ import annotations

from datetime import timedelta

import pytest

from autotube.domain.pipeline_templates import (
    BUILTIN_RELEASED_AT,
    PipelineTemplate,
    TemplateAudience,
    TemplateOrigin,
    TemplateStatus,
    builtin_template,
    user_type_id,
)
from autotube.domain.template_rules import (
    NAME_MAX_LENGTH,
    ensure_editable,
    ensure_new_id,
    ensure_type_id_free,
    ensure_type_id_owned,
    immutable_errors,
    name_errors,
    revised,
    revision_errors,
    servable,
)
from autotube.shared.errors import RuleConflict
from tests.fixtures.fake_runtime import START
from tests.fixtures.template_records import template

LATER = START + timedelta(hours=1)
TOO_LONG = "x" * (NAME_MAX_LENGTH + 1)


def kids_builtin() -> PipelineTemplate:
    return builtin_template("narrated_video", "kids_story", "Kids", "", TemplateAudience.KIDS, {})


def test_user_type_ids_are_prefixed_template_ids() -> None:
    assert user_type_id("abc") == "t_abc"


def test_builtin_templates_are_first_revisions_named_after_their_type() -> None:
    made = kids_builtin()
    assert (made.id, made.type_id, made.origin, made.revision, made.created_at) == (
        "kids_story",
        "kids_story",
        TemplateOrigin.BUILTIN,
        1,
        BUILTIN_RELEASED_AT,
    )


@pytest.mark.parametrize(
    ("made", "builtin", "ready"),
    [
        (kids_builtin(), True, True),
        (template(), False, True),
        (template(status=TemplateStatus.DRAFT), False, False),
    ],
    ids=["builtin", "ready", "draft"],
)
def test_builtin_and_ready_follow_origin_and_status(
    made: PipelineTemplate, builtin: bool, ready: bool
) -> None:
    assert (made.is_builtin, made.is_ready) == (builtin, ready)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Facts", {}),
        ("   ", {"name": "name is required"}),
        ("x" * NAME_MAX_LENGTH, {}),
        (f"  {'x' * NAME_MAX_LENGTH}  ", {}),
        (TOO_LONG, {"name": f"name must be at most {NAME_MAX_LENGTH} characters"}),
    ],
)
def test_names_are_required_and_limited_after_trimming(name: str, expected: dict[str, str]) -> None:
    assert name_errors(name) == expected


def test_builtin_templates_are_read_only() -> None:
    with pytest.raises(RuleConflict, match="duplicate it") as raised:
        ensure_editable(template(origin=TemplateOrigin.BUILTIN))
    assert raised.value.code == "template_builtin"
    ensure_editable(template())


def test_audience_engine_and_type_id_cannot_change() -> None:
    changed = template(audience=TemplateAudience.KIDS, engine="elsewhere", type_id="t_other")
    assert sorted(immutable_errors(template(), changed)) == ["audience", "engine", "type_id"]
    assert immutable_errors(template(), template(name="Renamed")) == {}


def test_taken_type_ids_are_refused() -> None:
    with pytest.raises(RuleConflict, match="'kids_story'") as raised:
        ensure_type_id_free("kids_story", {"kids_story"})
    assert raised.value.code == "template_type_taken"
    ensure_type_id_free("t_new", {"kids_story"})


def test_a_taken_id_cannot_be_added_again() -> None:
    with pytest.raises(RuleConflict, match="'tpl-1'") as raised:
        ensure_new_id("tpl-1", taken=True)
    assert raised.value.code == "template_exists"
    ensure_new_id("tpl-1", taken=False)


def test_a_type_id_held_by_another_template_is_refused() -> None:
    with pytest.raises(RuleConflict, match="'t_a'") as raised:
        ensure_type_id_owned(template("b", type_id="t_a"), "a")
    assert raised.value.code == "template_type_taken"
    ensure_type_id_owned(template("a"), "a")
    ensure_type_id_owned(template("a"), None)


def test_only_ready_templates_with_a_free_type_id_are_served() -> None:
    assert servable(template(), {"kids_story"})
    assert not servable(template(status=TemplateStatus.DRAFT), set())
    assert not servable(template(type_id="kids_story"), {"kids_story"})


def test_a_revision_keeps_identity_and_counts_up() -> None:
    proposed = template(
        "other",
        type_id="t_tpl-1",
        name="Renamed",
        revision=7,
        origin=TemplateOrigin.SUGGESTED,
        created_at=LATER,
    )
    updated = revised(template(revision=2), proposed, LATER)
    assert (updated.id, updated.engine, updated.origin) == (
        "tpl-1",
        "narrated_video",
        TemplateOrigin.BLANK,
    )
    assert (updated.name, updated.revision, updated.created_at, updated.updated_at) == (
        "Renamed",
        3,
        START,
        LATER,
    )


@pytest.mark.parametrize(
    ("proposed", "fields"),
    [
        (template(name=" ", audience=TemplateAudience.KIDS), ["audience", "name"]),
        (template(type_id="t_other"), ["type_id"]),
        (template(engine="elsewhere"), ["engine"]),
        (template(name=TOO_LONG), ["name"]),
        (template(name="Renamed", status=TemplateStatus.DRAFT), []),
    ],
    ids=["blank-name-and-audience", "type-id", "engine", "long-name", "valid"],
)
def test_revision_errors_cover_fixed_fields_and_the_name(
    proposed: PipelineTemplate, fields: list[str]
) -> None:
    assert sorted(revision_errors(template(), proposed)) == fields

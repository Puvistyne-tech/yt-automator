from __future__ import annotations

from typing import Any

import pytest

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from autotube.pipelines.narrated_video.settings.story_choices import Structure
from autotube.pipelines.narrated_video.structures.registry import structure_spec
from tests.fixtures.template_records import template
from tests.fixtures.template_settings import GENERAL, KIDS, pipeline_of

LIST_COUNT = ("story.item_count",)
QUIZ_COUNTS = ("story.quiz_questions", "story.answer_choices")
SHOWN: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = [
    ("list", LIST_COUNT, QUIZ_COUNTS),
    ("countdown", LIST_COUNT, QUIZ_COUNTS),
    ("quiz", QUIZ_COUNTS, LIST_COUNT),
]
DERIVED = (
    "story.scene_count_min",
    "story.scene_count_max",
    "story.target_duration_seconds",
    "story.duration_tolerance_seconds",
)
FOREIGN = [
    ("list", "{question_count}"),
    ("countdown", "{question_count}"),
    ("list", "{moral}"),
    ("countdown", "{takeaway}"),
    ("quiz", "{count}"),
    ("quiz", "{moral}"),
]


@pytest.mark.parametrize("audience", [KIDS, GENERAL])
@pytest.mark.parametrize(("structure", "shown", "other"), SHOWN)
def test_a_structure_shows_its_counts_and_hides_cast_derived_and_other_counts(
    audience: TemplateAudience, structure: str, shown: tuple[str, ...], other: tuple[str, ...]
) -> None:
    ui = pipeline_of(audience, structure=structure).descriptor.ui_schema
    hidden, basic = ui["ui:hidden"], ui["ui:basic"]
    assert isinstance(hidden, list) and isinstance(basic, list)
    spec = structure_spec(Structure(structure))
    assert {*spec.hidden_paths, *DERIVED, *other, "story.source", "cast"} <= set(hidden)
    assert not set(shown) & set(hidden)
    assert set(shown) <= set(basic) and not set(DERIVED) & set(basic)


@pytest.mark.parametrize(("structure", "placeholder"), FOREIGN)
def test_a_placeholder_of_another_structure_is_a_template_problem(
    structure: str, placeholder: str
) -> None:
    definition: dict[str, Any] = {
        "structure": structure,
        "title_template": {"en": f"{{title}} {placeholder}"},
    }
    found = NarratedVideoEngine().problems(template(audience=GENERAL, definition=definition))
    assert set(found) == {"definition.title_template"}
    assert placeholder in found["definition.title_template"]

from __future__ import annotations

from typing import Any

import pytest

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from tests.fixtures.template_records import template

KIDS, GENERAL = TemplateAudience.KIDS, TemplateAudience.GENERAL
TODDLER = {
    "id": "nia",
    "name": {"en": "Nia", "ta": "நியா"},
    "species": "girl",
    "visual_descriptor": "a cheerful toddler in a yellow raincoat",
}


def problems(audience: TemplateAudience = GENERAL, **definition: Any) -> dict[str, str]:
    return NarratedVideoEngine().problems(template(audience=audience, definition=definition))


@pytest.mark.parametrize("audience", [KIDS, GENERAL])
def test_a_blank_template_has_no_problems(audience: TemplateAudience) -> None:
    blank = NarratedVideoEngine().blank(audience)
    assert NarratedVideoEngine().problems(template(audience=audience, definition=blank)) == {}


def test_an_invalid_definition_reports_only_its_own_fields() -> None:
    found = problems(length="endless", structure="podcast", surprise=1, basic=["nowhere"])
    assert set(found) == {"definition.length", "definition.structure", "definition.surprise"}


def test_an_unknown_style_is_the_only_problem_reported() -> None:
    assert set(problems(visual_style="neon_noir", settings={"bogus": 1})) == {
        "definition.visual_style"
    }
    assert problems(visual_style="ink_line_art") == {}


def test_unknown_metadata_placeholders_are_reported_per_template() -> None:
    found = problems(
        title_template={"en": "{title} {nope}"},
        short_title_template={"ta": "{hook}"},
        description_template={"ta": "{zzz}"},
    )
    assert set(found) == {"definition.title_template", "definition.description_template"}
    assert "{nope}" in found["definition.title_template"]


@pytest.mark.parametrize(
    ("audience", "definition", "expected"),
    [
        (
            GENERAL,
            {"basic": ["story.tone", "story.nothing"]},
            {"definition.basic": "ui:basic path story.nothing is not a setting"},
        ),
        (
            GENERAL,
            {"basic": ["story.tone"], "hidden": ["story.tone"]},
            {"definition.hidden": "ui:basic and ui:hidden both name story.tone"},
        ),
        (
            GENERAL,
            {"basic": ["story.age_min"]},
            {"definition.hidden": "ui:basic and ui:hidden both name story.age_min"},
        ),
        (KIDS, {"basic": ["story.age_min"]}, {}),
    ],
)
def test_basic_paths_must_be_settings_and_not_hidden(
    audience: TemplateAudience, definition: dict[str, Any], expected: dict[str, str]
) -> None:
    assert problems(audience, **definition) == expected


def test_hidden_paths_must_be_settings_and_listed_once() -> None:
    found = problems(hidden=["story.tone", "story.tone", "nowhere"])
    assert "nowhere is not a setting" in found["definition.hidden"]
    assert "more than once" in found["definition.hidden"]
    assert problems(hidden=["safety.audience", "story.morals"]) == {}


def test_an_overlay_that_does_not_validate_is_reported_under_settings() -> None:
    found = problems(settings={"story": {"scene_count_min": 0}, "bogus": 1})
    assert set(found) == {"definition.settings.story.scene_count_min", "definition.settings.bogus"}


@pytest.mark.parametrize("audience", [KIDS, GENERAL])
def test_an_overlay_cannot_lift_the_age_cap(audience: TemplateAudience) -> None:
    assert set(problems(audience, settings={"story": {"age_max": 15}})) == {
        "definition.settings.story.age_max"
    }


SCREENED: list[tuple[dict[str, Any], str]] = [
    ({"brief": "Calm tales for the little ones."}, "definition.brief"),
    ({"brief": "குழந்தைகளுக்கான கதைகள்"}, "definition.brief"),
    ({"tone": "sleepy, for Toddlers"}, "definition.tone"),
    ({"topics": ["bedtime stories"]}, "definition.topics"),
    ({"music_mood": "nursery rhymes on piano"}, "definition.music_mood"),
    ({"title_template": {"en": "{title} for KIDS"}}, "definition.title_template"),
    ({"short_title_template": {"ta": "{title} குட்டீஸ்"}}, "definition.short_title_template"),
    (
        {"description_template": {"en": "Bedtime stories: {title}"}},
        "definition.description_template",
    ),
    ({"tags": {"en": ["KIDS stories"]}}, "definition.tags"),
    ({"tags": {"ta": ["குழந்தைகள் கதைகள்"]}}, "definition.tags"),
    ({"hashtags": {"en": ["#KidsStories"]}}, "definition.hashtags"),
    ({"visual_style": "anime"}, "definition.visual_style"),
    ({"settings": {"look": {"visual_style": "anime"}}}, "definition.settings.look.visual_style"),
    ({"settings": {"metadata": {"tags": {"en": ["kids"]}}}}, "definition.settings.metadata.tags"),
    (
        {"settings": {"series": {"tagline": {"en": "For kids"}}}},
        "definition.settings.series.tagline",
    ),
    (
        {"settings": {"series": {"outro_line": {"ta": "நன்றி, சின்ன நண்பர்களே!"}}}},
        "definition.settings.series.outro_line",
    ),
    (
        {"settings": {"series": {"editorial_rules": ["Talk to the little friends."]}}},
        "definition.settings.series.editorial_rules",
    ),
    (
        {"settings": {"story": {"extra_instructions": "Address the kids."}}},
        "definition.settings.story.extra_instructions",
    ),
    (
        {"settings": {"story": {"question_style": "questions for little ones"}}},
        "definition.settings.story.question_style",
    ),
    ({"settings": {"cast": [TODDLER]}}, "definition.settings.cast"),
]


@pytest.mark.parametrize(("definition", "path"), SCREENED, ids=lambda value: str(value)[:40])
def test_the_term_screen_reports_where_the_text_was_written(
    definition: dict[str, Any], path: str
) -> None:
    found = problems(**definition)
    assert set(found) == {path}
    assert found[path].startswith("never address children; remove: ")
    assert problems(KIDS, **definition) == {}


@pytest.mark.parametrize("name", ["Bedtime stories for kids", "குழந்தைகள் கதைகள்"])
def test_the_term_screen_checks_the_template_name(name: str) -> None:
    found = NarratedVideoEngine().problems(template(name=name, definition={}))
    assert set(found) == {"name"}


@pytest.mark.parametrize(
    "definition",
    [
        {"brief": "Kidney health facts for adults."},
        {"tags": {"en": ["kidney"]}},
        {"brief": "குழந்தைகளேயில்லாத ஊர்"},
        {"settings": {"safety": {"banned_words": ["kids"]}}},
    ],
)
def test_the_term_screen_matches_whole_phrases_only(definition: dict[str, Any]) -> None:
    assert problems(**definition) == {}

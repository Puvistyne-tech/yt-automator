from __future__ import annotations

from typing import Any

import pytest

from autotube.domain.pipeline_templates import TemplateAudience
from autotube.pipelines.narrated_video.engine import NarratedVideoEngine
from tests.fixtures.template_records import template

KIDS, GENERAL = TemplateAudience.KIDS, TemplateAudience.GENERAL


def problems(audience: TemplateAudience = GENERAL, **definition: Any) -> dict[str, str]:
    return NarratedVideoEngine().problems(template(audience=audience, definition=definition))


@pytest.mark.parametrize("audience", [KIDS, GENERAL])
def test_a_blank_template_has_no_problems(audience: TemplateAudience) -> None:
    blank = NarratedVideoEngine().blank(audience)
    assert NarratedVideoEngine().problems(template(audience=audience, definition=blank)) == {}


def test_an_invalid_definition_is_reported_by_field() -> None:
    found = problems(length="endless", structure="quiz", surprise=1)
    assert set(found) == {"definition.length", "definition.structure", "definition.surprise"}


def test_an_unknown_style_is_reported_once_on_its_field() -> None:
    assert set(problems(visual_style="neon_noir")) == {"definition.visual_style"}
    assert problems(visual_style="anime") == {}


def test_unknown_metadata_placeholders_are_reported_per_template() -> None:
    found = problems(
        title_template={"en": "{title} {nope}"},
        short_title_template={"ta": "{hook}"},
        description_template={"ta": "{zzz}"},
    )
    assert set(found) == {"definition.title_template", "definition.description_template"}
    assert "{nope}" in found["definition.title_template"]


def test_basic_paths_must_be_settings_and_not_hidden() -> None:
    assert problems(basic=["story.tone", "story.nothing"]) == {
        "definition.basic": "ui:basic path story.nothing is not a setting"
    }
    found = problems(basic=["story.tone"], hidden=["story.tone"])
    assert "both name story.tone" in found["definition.hidden"]


def test_general_templates_cannot_show_the_hidden_age_fields() -> None:
    found = problems(basic=["story.age_min"])
    assert found == {"definition.hidden": "ui:basic and ui:hidden both name story.age_min"}
    assert problems(KIDS, basic=["story.age_min"]) == {}


def test_hidden_paths_must_be_settings_and_listed_once() -> None:
    found = problems(hidden=["story.tone", "story.tone", "nowhere"])
    assert "nowhere is not a setting" in found["definition.hidden"]
    assert "more than once" in found["definition.hidden"]
    assert problems(hidden=["safety.audience", "story.morals"]) == {}


def test_an_overlay_that_does_not_validate_is_reported_under_settings() -> None:
    found = problems(settings={"story": {"scene_count_min": 0}, "bogus": 1})
    assert set(found) == {"definition.settings.story.scene_count_min", "definition.settings.bogus"}


def test_a_kids_overlay_cannot_lift_the_age_cap() -> None:
    assert set(problems(KIDS, settings={"story": {"age_max": 15}})) == {
        "definition.settings.story.age_max"
    }


def test_the_term_screen_flags_each_general_field_in_english() -> None:
    found = NarratedVideoEngine().problems(
        template(
            name="Bedtime stories for kids",
            definition={
                "brief": "Calm tales for the little ones.",
                "tags": {"en": ["kids stories"]},
                "hashtags": {"en": ["#KidsStories"]},
                "settings": {"series": {"intro_line": {"en": "Hello, boys and girls!"}}},
            },
        )
    )
    assert set(found) == {
        "name",
        "definition.brief",
        "definition.tags",
        "definition.hashtags",
        "definition.settings.series",
    }
    assert found["definition.hashtags"] == "never address children; remove: kidsstories"


def test_the_term_screen_flags_tamil_terms() -> None:
    found = problems(
        tags={"ta": ["குழந்தைகள் கதைகள்"]},
        settings={"series": {"outro_line": {"ta": "நன்றி, சின்ன நண்பர்களே!"}}},
    )
    assert "குழந்தைகள் கதைகள்" in found["definition.tags"]
    assert "சின்ன நண்பர்களே" in found["definition.settings.series"]


def test_the_term_screen_does_not_apply_to_kids_templates() -> None:
    assert problems(KIDS, brief="Gentle tales for kids.", tags={"en": ["kids"]}) == {}


def test_tags_are_screened_one_at_a_time() -> None:
    assert problems(tags={"en": ["little", "ones"]}) == {}

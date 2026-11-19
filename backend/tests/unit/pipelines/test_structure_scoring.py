from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from autotube.domain.quality import weighted_score
from autotube.pipelines.narrated_video.scoring.inputs import ScoreInputs
from autotube.pipelines.narrated_video.scoring.score import score_items
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.template.settings_model import kids_settings_model
from tests.fixtures.explainer_data import (
    explainer_settings,
    explainer_story,
    without_hook,
    without_hook_or_takeaway,
)
from tests.fixtures.kids_data import story
from tests.fixtures.list_data import list_settings, list_story, with_scene
from tests.fixtures.template_settings import GENERAL


def inputs_of(settings: KidsStorySettings, stories: dict[str, Story]) -> ScoreInputs:
    return ScoreInputs(settings, ("en",), (), Path(), stories, {}, None)


def scored(
    settings: KidsStorySettings, stories: dict[str, Story]
) -> dict[str, tuple[float, float]]:
    return {
        item.id: (item.score, item.weight) for item in score_items(inputs_of(settings, stories))
    }


@pytest.mark.parametrize(
    ("sample", "expected"),
    [(explainer_story, 100.0), (without_hook, 50.0), (without_hook_or_takeaway, 0.0)],
)
def test_the_explainer_item_loses_points_per_problem(
    sample: Callable[[], Story], expected: float
) -> None:
    items = scored(explainer_settings(GENERAL), {"en": sample()})
    assert items["structure"] == (expected, 1.5)
    assert not {"moral_and_refrain", "character_consistency"} & items.keys()


def test_the_explainer_item_uses_the_structure_weight() -> None:
    settings = explainer_settings(GENERAL, quality={"weights": {"structure": 3}})
    items = scored(settings, {"en": without_hook()})
    assert items == {
        "reading_level": (100.0, 1.0),
        "structure": (50.0, 3.0),
        "completeness": (0.0, 2.0),
    }
    assert weighted_score(
        score_items(inputs_of(settings, {"en": without_hook()}))
    ) == pytest.approx((100 + 150) / 6)


def test_inapplicable_items_are_left_out_and_the_score_renormalises() -> None:
    story_items = scored(kids_settings_model()(), {"en": story()})
    assert story_items == {
        "reading_level": (100.0, 1.0),
        "moral_and_refrain": (100.0, 1.5),
        "completeness": (0.0, 2.0),
    }
    assert "structure" not in story_items
    assert weighted_score(
        score_items(inputs_of(kids_settings_model()(), {"en": story()}))
    ) == pytest.approx(250 / 4.5)
    assert scored(explainer_settings(GENERAL), {}) == {"completeness": (0.0, 2.0)}


def test_the_list_item_scores_its_shape_and_skips_story_items() -> None:
    settings = list_settings(GENERAL)
    assert scored(settings, {"en": list_story()})["structure"] == (100.0, 1.5)
    items = scored(settings, {"en": with_scene(list_story(), 1, heading="")})
    assert items["structure"] == (50.0, 1.5)
    assert not {"moral_and_refrain", "character_consistency"} & items.keys()

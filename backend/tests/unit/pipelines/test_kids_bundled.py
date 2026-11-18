from __future__ import annotations

import unicodedata

import pytest

from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.story.bundled import (
    BundledChoice,
    BundledStory,
    bundled_stories,
    pick_bundled,
)
from automator.pipelines.kids_story.story.gates import story_problems
from automator.pipelines.kids_story.story.words import contains_phrase
from tests.unit.pipelines.kids_data import bundled_raw

NAMES = ("golden_mango", "leaf_boat", "lost_song")
CAST = {"kutty", "mittu", "chinnu", "aamai_thatha"}


def tamil_letter_share(text: str) -> float:
    letters = [char for char in text if unicodedata.category(char)[0] in {"L", "M"}]
    tamil = [char for char in letters if "஀" <= char <= "௿"]
    return len(tamil) / len(letters)


def test_at_least_three_bundled_stories_validate() -> None:
    stories = bundled_stories()
    assert {story.id for story in stories} >= set(NAMES)
    for story in stories:
        assert 8 <= len(story.scenes) <= 10
        assert set(story.text) == {"en", "ta"}
        assert set(story.cast) <= CAST


@pytest.mark.parametrize("name", NAMES)
def test_bundled_english_passes_every_gate(name: str) -> None:
    settings = KidsStorySettings()
    story = BundledStory.model_validate(bundled_raw(name)).to_story(
        "en", settings.series.refrain.en
    )
    assert story_problems(story, settings) == []


@pytest.mark.parametrize("name", NAMES)
def test_bundled_tamil_is_tamil_script_with_moral_and_refrain(name: str) -> None:
    settings = KidsStorySettings()
    story = BundledStory.model_validate(bundled_raw(name)).to_story(
        "ta", settings.series.refrain.ta
    )
    for scene in story.scenes:
        assert tamil_letter_share(scene.narration) > 0.95
    assert contains_phrase(story.scenes[-1].narration, story.moral)
    assert story.scenes[-1].narration.endswith(settings.series.refrain.ta)
    assert tamil_letter_share(story.title + story.hook_line + "".join(story.questions)) > 0.95


def test_refrain_slot_is_filled_from_settings() -> None:
    story = BundledStory.model_validate(bundled_raw()).to_story("en", "Hooray for friends!")
    assert story.scenes[-1].narration.endswith("Hooray for friends!")
    assert all("{refrain}" not in scene.narration for scene in story.scenes)


def choice(theme: str, recent: tuple[str, ...] = (), cast: set[str] = CAST) -> BundledChoice:
    return BundledChoice(
        cast_ids=cast, languages=("en", "ta"), theme=theme, recent=recent, avoid=3, seed="s"
    )


def test_pick_bundled_prefers_the_theme_then_avoids_recent_themes() -> None:
    assert pick_bundled(choice("Trying again")).id == "leaf_boat"
    picked = pick_bundled(choice("dancing", recent=("sharing", "trying again")))
    assert picked.id == "lost_song"


def test_pick_bundled_needs_a_compatible_cast() -> None:
    with pytest.raises(LookupError):
        pick_bundled(choice("sharing", cast={"kutty"}))


def test_bundled_structure_is_checked() -> None:
    raw = bundled_raw()
    raw["text"]["ta"]["narrations"] = raw["text"]["ta"]["narrations"][:2]
    with pytest.raises(ValueError, match="narrations"):
        BundledStory.model_validate(raw)

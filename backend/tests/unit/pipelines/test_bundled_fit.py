from __future__ import annotations

from pathlib import Path

from autotube.pipelines.narrated_video.stages.story import StoryStage
from autotube.pipelines.narrated_video.story.bundled import BundledStory, bundled_stories
from autotube.pipelines.narrated_video.story.bundled_fit import (
    LengthWish,
    bundled_seconds,
    fits,
    length_pool,
    length_wish,
    misfit_warning,
)
from tests.fixtures.kids_data import REFRAIN_EN, StageRig, quick_settings
from tests.fixtures.kids_fakes import FakeProviders, failing_writer
from tests.fixtures.mac_runs import mac_settings


def by_id(story_id: str) -> BundledStory:
    return next(story for story in bundled_stories() if story.id == story_id)


def cut(story: BundledStory, scenes: int) -> BundledStory:
    text = {
        code: entry.model_copy(update={"narrations": entry.narrations[:scenes]})
        for code, entry in story.text.items()
    }
    return story.model_copy(update={"scenes": story.scenes[:scenes], "text": text, "id": "cut"})


def test_every_bundled_story_fits_the_default_length() -> None:
    wish = length_wish(quick_settings(), "en", REFRAIN_EN)
    assert all(fits(story, wish) for story in bundled_stories())
    assert length_pool(bundled_stories(), wish) == bundled_stories()
    assert misfit_warning(by_id("leaf_boat"), wish) == ""


def test_the_fitting_stories_are_preferred() -> None:
    leaf = by_id("leaf_boat")
    seconds = bundled_seconds(leaf, length_wish(quick_settings(), "en", REFRAIN_EN))
    wish = LengthWish((8, 10), (seconds - 0.1, seconds + 0.1), 120, "en", REFRAIN_EN)
    assert length_pool(bundled_stories(), wish) == [leaf]


def test_without_a_fit_the_closest_scene_count_is_used_and_named() -> None:
    wish = length_wish(mac_settings(), "en", REFRAIN_EN)
    shorter = cut(by_id("golden_mango"), 7)
    assert length_pool([*bundled_stories(), shorter], wish) == [shorter]
    assert length_pool(bundled_stories(), wish) == bundled_stories()
    warning = misfit_warning(by_id("leaf_boat"), wish)
    assert warning.startswith('the fallback story "Chinnu and the Leaf Boat" has 9 scenes')
    assert "ignores the requested length of 4 to 6 scenes and 40 to 80 s" in warning


def test_the_stage_warns_when_the_fallback_ignores_the_length(tmp_path: Path) -> None:
    settings = mac_settings()
    rig = StageRig(tmp_path, settings=settings, providers=FakeProviders(writer=failing_writer()))
    assert rig.run(StoryStage()).provider == "bundled"
    warnings = rig.book.warnings()
    assert any("has 9 scenes" in line and "4 to 6 scenes" in line for line in warnings)


def test_a_fitting_fallback_adds_no_warning(tmp_path: Path) -> None:
    rig = StageRig(tmp_path, providers=FakeProviders(writer=failing_writer()))
    assert rig.run(StoryStage()).provider == "bundled"
    assert not any("ignores the requested length" in line for line in rig.logs)

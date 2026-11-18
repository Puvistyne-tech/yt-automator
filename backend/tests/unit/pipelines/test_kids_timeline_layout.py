from __future__ import annotations

from pathlib import Path

import pytest

from automator.pipelines.kids_story.settings.output import ShortSceneSelection, ShortSettings
from automator.pipelines.kids_story.story.model import Story
from automator.pipelines.kids_story.timeline.composition import Sources, composition, effect_clips
from automator.pipelines.kids_story.timeline.selection import short_scene_indexes
from automator.pipelines.kids_story.timeline.variants import planned
from tests.fixtures.kids_data import quick_settings, story, voices


@pytest.mark.parametrize(
    ("intro_card", "outro_card", "spoken", "first", "last"),
    [
        (True, False, ("intro", "outro"), "card-intro-en@episode", "scene-8@episode"),
        (False, True, ("intro", "outro"), "scene-0@episode", "card-outro-en@episode"),
        (True, True, (), "card-intro-en@episode", "card-outro-en@episode"),
        (False, False, (), "scene-0@episode", "scene-8@episode"),
    ],
)
def test_episode_cards_and_spoken_lines(
    intro_card: bool, outro_card: bool, spoken: tuple[str, ...], first: str, last: str
) -> None:
    settings = quick_settings(episode={"intro_card": intro_card, "outro_card": outro_card})
    segments = planned(story(), voices(story(), extra=spoken), settings, "episode")
    assert (segments[0].visual_key, segments[-1].visual_key) == (first, last)
    keys = [item.key for item in segments]
    assert ("outro" in keys) is (outro_card or "outro" in spoken)


def test_a_card_without_its_line_stays_silent_for_the_card_length() -> None:
    settings = quick_settings(episode={"card_seconds": 4.5})
    intro = planned(story(), voices(story(), extra=()), settings, "episode")[0]
    assert intro.key == "intro" and intro.narration is None and intro.duration == 4.5


@pytest.mark.parametrize(
    ("sections", "keys"),
    [({"short": {"hook_line": False}}, ("intro", "outro", "hook")), ({}, ("intro", "outro"))],
)
def test_short_without_a_hook_starts_on_a_scene(
    sections: dict[str, dict[str, object]], keys: tuple[str, ...]
) -> None:
    segments = planned(story(), voices(story(), extra=keys), quick_settings(**sections), "short")
    assert segments[0].key == "scene-0"


def test_automatic_choice_without_hints_uses_every_scene_up_to_the_cap() -> None:
    plain = [scene.model_copy(update={"hero": False}) for scene in story().scenes]
    draft = story(short_scenes=[]).model_copy(update={"scenes": plain})
    assert short_scene_indexes(draft, ShortSettings(max_scenes=3)) == [0, 1, 2]


def test_first_scenes_beyond_the_story_use_every_scene() -> None:
    settings = ShortSettings(
        scene_selection=ShortSceneSelection.FIRST_N, first_n_scenes=10, max_scenes=10
    )
    assert short_scene_indexes(story(), settings) == list(range(9))


def sources(root: Path, draft: Story, effects: dict[str, Path]) -> Sources:
    segments = [
        *planned(draft, voices(draft), quick_settings(), "episode"),
        *planned(draft, voices(draft), quick_settings(), "short"),
    ]
    return Sources(
        workspace=root,
        clips={item.visual_key: root / "clip.mp4" for item in segments},
        voices=voices(draft),
        effects=effects,
        music=None,
        subtitles=None,
    )


def test_short_composition_is_portrait_and_effects_can_be_off(tmp_path: Path) -> None:
    effects = {"birds chirping": tmp_path / "birds.wav"}
    settings = quick_settings(sound_effects={"enabled": False})
    segments = planned(story(), voices(story()), settings, "short")
    made = composition(segments, story(), sources(tmp_path, story(), effects), settings, "short")
    assert (made.width, made.height) == (720, 1280) and made.sound_effects == ()


def test_effects_without_a_sound_file_are_skipped(tmp_path: Path) -> None:
    settings = quick_settings()
    segments = planned(story(), voices(story()), settings, "episode")
    only_birds = sources(tmp_path, story(), {"birds chirping": tmp_path / "birds.wav"})
    clips = effect_clips(segments, story(), only_birds, settings)
    assert [clip.path.name for clip in clips] == ["birds.wav"]

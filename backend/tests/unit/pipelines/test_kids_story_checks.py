from __future__ import annotations

from pathlib import Path

import pytest

from autotube.pipelines.kids_story.settings.story_controls import StoryCheck
from autotube.pipelines.kids_story.stages.story import StoryStage
from autotube.pipelines.kids_story.story.casting import episode_cast
from autotube.pipelines.kids_story.story.gates import (
    ending_problems,
    story_problems,
    translation_problems,
)
from autotube.pipelines.kids_story.story.model import Story
from autotube.pipelines.kids_story.story.shaping import shaped
from tests.fixtures.kids_data import StageRig, meta_of, quick_settings, smart_writer, story
from tests.fixtures.kids_fakes import FakeProviders

LAST = "Kavin felt warm and bright inside and smiled at all of his dear friends today."
MORAL_ONLY = f"{LAST} Sharing makes everyone happier."
REFRAIN_ONLY = f"{LAST} Be kind, be brave, be you!"
REFRAIN_PROBLEM = 'say the refrain "Be kind, be brave, be you!" in the last scene'
MORAL_PROBLEM = "say the moral, word for word, in the last scene"


def ending_with(text: str) -> Story:
    scenes = list(story().scenes)
    scenes[-1] = scenes[-1].model_copy(update={"narration": text})
    return story().model_copy(update={"scenes": scenes})


@pytest.mark.parametrize(
    ("style", "text", "expected"),
    [
        ("moral_and_refrain", REFRAIN_ONLY, [MORAL_PROBLEM]),
        ("refrain_only", REFRAIN_ONLY, []),
        ("refrain_only", MORAL_ONLY, [REFRAIN_PROBLEM]),
        ("open", LAST, []),
    ],
)
def test_ending_gate_follows_the_ending_style(style: str, text: str, expected: list[str]) -> None:
    settings = quick_settings(story={"ending_style": style, "ending_scenes": 1})
    assert ending_problems(ending_with(text), settings) == expected


def test_switched_off_checks_do_not_run_but_child_safety_always_does() -> None:
    broken = ending_with(f"{LAST} a knife")
    broken = broken.model_copy(update={"scenes": broken.scenes[-3:]})
    settings = quick_settings(story={"enabled_checks": []})
    assert story_problems(broken, settings) == ["remove these words: knife"]
    assert len(story_problems(broken, quick_settings())) > 1


def test_switching_off_the_ending_check_also_skips_it_for_translations() -> None:
    no_ending = ending_with(LAST)
    kept = [check for check in StoryCheck if check is not StoryCheck.ENDING]
    assert translation_problems(no_ending, quick_settings(story={"enabled_checks": kept})) == []
    assert translation_problems(no_ending, quick_settings()) != []


def test_child_safety_checks_cannot_be_listed() -> None:
    assert {check.value for check in StoryCheck}.isdisjoint({"banned_words", "brand_names"})
    with pytest.raises(ValueError, match="enabled_checks"):
        quick_settings(story={"enabled_checks": ["banned_words"]})


def test_fixed_lead_keeps_the_cast_order_and_size() -> None:
    assert [m.id for m in episode_cast(quick_settings(), "any")] == [
        "kavin",
        "mittu",
        "chinnu",
        "aamai_thatha",
    ]
    two = quick_settings(story={"cast_per_episode": 2})
    assert [m.id for m in episode_cast(two, "any")] == ["kavin", "mittu"]
    many = quick_settings(story={"cast_per_episode": 9})
    assert len(episode_cast(many, "any")) == 4


def test_rotating_lead_varies_by_seed_and_keeps_cast_order_after_it() -> None:
    settings = quick_settings(story={"lead_mode": "rotate", "cast_per_episode": 2})
    ids = [member.id for member in quick_settings().cast]
    picks = [[m.id for m in episode_cast(settings, f"run-{n}")] for n in range(12)]
    assert len({pick[0] for pick in picks}) > 1
    assert all(ids[(ids.index(lead) + 1) % len(ids)] == second for lead, second in picks)
    assert episode_cast(settings, "run-5") == episode_cast(settings, "run-5")


def test_shaping_keeps_at_most_the_allowed_sound_cues_per_scene() -> None:
    scenes = [
        scene.model_copy(update={"sound_effects": ["a", "b", "c"]}) for scene in story().scenes
    ]
    raw = story().model_copy(update={"scenes": scenes})
    settings = quick_settings(sound_effects={"max_per_scene": 1})
    assert {tuple(scene.sound_effects) for scene in shaped(raw, settings).scenes} == {("a",)}


def test_story_stage_writes_with_the_episode_lead(tmp_path: Path) -> None:
    settings = quick_settings(story={"lead_mode": "rotate", "cast_per_episode": 1})
    writer = smart_writer()
    providers = FakeProviders(writer=writer)
    rig = StageRig(tmp_path, settings, ("en",), providers, run_id="run-4")
    rig.run(StoryStage())
    assert episode_cast(settings, "run-4")[0].id == "mittu"
    assert "mittu leads the story" in writer.requests[0].prompt


def test_bundled_stories_still_work_with_a_rotating_small_cast(tmp_path: Path) -> None:
    settings = quick_settings(
        story={"source": "bundled_only", "lead_mode": "rotate", "cast_per_episode": 1}
    )
    rig = StageRig(tmp_path, settings=settings)
    rig.run(StoryStage())
    assert {item.meta["source"] for item in meta_of(rig, "story")} == {"bundled"}

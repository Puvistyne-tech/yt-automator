from __future__ import annotations

from pathlib import Path

import pytest

from autotube.pipelines.kids_story.stages.story import StoryStage
from autotube.pipelines.kids_story.story.casting import episode_cast
from autotube.pipelines.kids_story.story.gates import ending_problems
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


def test_fixed_lead_keeps_the_cast_order_and_size() -> None:
    assert [m.id for m in episode_cast(quick_settings(), "any")] == [
        "kavin",
        "mittu",
        "chinnu",
        "aamai_thatha",
    ]
    two = quick_settings(story={"cast_per_episode": 2})
    assert [m.id for m in episode_cast(two, "any")] == ["kavin", "mittu"]
    one = quick_settings(story={"cast_per_episode": 1})
    assert [m.id for m in episode_cast(one, "any")] == ["kavin"]
    many = quick_settings(story={"cast_per_episode": 9})
    assert len(episode_cast(many, "any")) == 4


def test_per_episode_lead_varies_by_seed_and_keeps_cast_order_after_it() -> None:
    settings = quick_settings(story={"lead_mode": "per_episode", "cast_per_episode": 2})
    ids = [member.id for member in quick_settings().cast]
    picks = [[m.id for m in episode_cast(settings, f"run-{n}")] for n in range(12)]
    assert len({pick[0] for pick in picks}) > 1
    assert all(ids[(ids.index(lead) + 1) % len(ids)] == second for lead, second in picks)
    assert episode_cast(settings, "run-5") == episode_cast(settings, "run-5")


@pytest.mark.parametrize(
    ("limit", "kept"), [(0, ()), (1, ("a",)), (3, ("a", "b", "c")), (5, ("a", "b", "c"))]
)
def test_shaping_keeps_at_most_the_allowed_sound_cues_per_scene(
    limit: int, kept: tuple[str, ...]
) -> None:
    scenes = [
        scene.model_copy(update={"sound_effects": ["a", "b", "c"]}) for scene in story().scenes
    ]
    raw = story().model_copy(update={"scenes": scenes})
    settings = quick_settings(sound_effects={"max_per_scene": limit})
    assert {tuple(scene.sound_effects) for scene in shaped(raw, settings).scenes} == {kept}


def test_every_attempt_uses_the_episode_lead_and_the_cast_gate_enforces_it(
    tmp_path: Path,
) -> None:
    settings = quick_settings(story={"lead_mode": "per_episode", "cast_per_episode": 1})
    writer = smart_writer()
    providers = FakeProviders(writer=writer)
    rig = StageRig(tmp_path, settings, ("en",), providers, run_id="run-4")
    rig.run(StoryStage())
    assert episode_cast(settings, "run-4")[0].id == "mittu"
    assert len(writer.requests) == settings.story.max_attempts
    assert all("mittu leads the story" in request.prompt for request in writer.requests)
    assert "only use cast ids; unknown: aamai_thatha, chinnu, kavin" in writer.requests[1].prompt


def test_bundled_stories_still_work_with_a_per_episode_lead_and_small_cast(tmp_path: Path) -> None:
    settings = quick_settings(
        story={"source": "bundled_only", "lead_mode": "per_episode", "cast_per_episode": 1}
    )
    rig = StageRig(tmp_path, settings=settings)
    rig.run(StoryStage())
    assert {item.meta["source"] for item in meta_of(rig, "story")} == {"bundled"}


@pytest.mark.parametrize(
    ("style", "ends_with_refrain"),
    [("moral_and_refrain", True), ("refrain_only", True), ("open", False)],
)
def test_bundled_stories_follow_the_ending_refrain(
    tmp_path: Path, style: str, ends_with_refrain: bool
) -> None:
    settings = quick_settings(story={"source": "bundled_only", "ending_style": style})
    rig = StageRig(tmp_path, settings=settings, languages=("en",))
    rig.run(StoryStage())
    written = Story.model_validate_json(
        (tmp_path / meta_of(rig, "story")[0].filename).read_text(encoding="utf-8")
    )
    last = written.scenes[-1].narration
    assert last.endswith("Be kind, be brave, be you!") is ends_with_refrain
    assert last == last.strip() and "{refrain}" not in last

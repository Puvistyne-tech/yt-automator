from __future__ import annotations

from typing import Any

import pytest

from autotube.pipelines.kids_story.story import prompt_parts
from autotube.pipelines.kids_story.story.casting import episode_cast
from autotube.pipelines.kids_story.story.prompts import story_request, translation_request
from tests.fixtures.kids_data import quick_settings, story

REFRAIN = '"Be kind, be brave, be you!"'


def story_prompts(**story_settings: Any) -> tuple[str, str]:
    request = story_request(quick_settings(story=story_settings), "sharing", "en")
    return request.system or "", request.prompt


def test_tone_and_writing_style_replace_the_fixed_wording() -> None:
    system, user = story_prompts(tone="funny, lively", writing_style="Rhyme every line.")
    assert "You write funny, lively, original stories" in system
    assert "- Rhyme every line.\n" in user
    assert "warm and calm tone" not in user


def test_extra_instructions_become_one_requirement_per_line() -> None:
    _, user = story_prompts(extra_instructions="Mention the rain.\n\n  Count to three.  ")
    assert "- Mention the rain.\n- Count to three.\n- The last scene" in user


def test_avoid_topics_are_listed_in_the_system_prompt() -> None:
    settings = quick_settings(safety={"avoid_topics": ["the dark", "  ", "getting lost"]})
    system = story_request(settings, "sharing", "en").system or ""
    assert "Never write about these topics:\n- the dark\n- getting lost\n\nReading level" in system


@pytest.mark.parametrize(
    ("style", "present", "absent"),
    [
        ("moral_and_refrain", "says the moral word for word", "ends openly"),
        ("refrain_only", f"ends with this exact refrain: {REFRAIN}", "says the moral"),
        ("open", "ends openly", "refrain:"),
    ],
)
def test_ending_style_shapes_the_story_prompt(style: str, present: str, absent: str) -> None:
    _, user = story_prompts(ending_style=style)
    assert present in user and absent not in user


@pytest.mark.parametrize(
    ("style", "moral", "refrain"),
    [("moral_and_refrain", True, True), ("refrain_only", False, True), ("open", False, False)],
)
def test_ending_style_shapes_the_translation_rules(style: str, moral: bool, refrain: bool) -> None:
    settings = quick_settings(story={"ending_style": style})
    prompt = translation_request(settings, story(), "en", "ta").prompt
    assert ("The moral must appear" in prompt) is moral
    assert ("must end with this exact refrain" in prompt) is refrain
    assert "Keep exactly 2 questions." in prompt and "- Character names" in prompt


def test_question_and_hook_style_reach_the_prompt() -> None:
    settings = quick_settings(
        story={"question_style": "riddles about colours"}, short={"hook_style": "playful, bouncy"}
    )
    user = story_request(settings, "sharing", "en").prompt
    assert "holds exactly 2 riddles about colours, in English." in user
    assert '"hook_line" is one playful, bouncy sentence in English' in user


def test_translation_style_reaches_the_translation_system_prompt() -> None:
    settings = quick_settings(story={"translation_style": "playful, rhyming"})
    system = translation_request(settings, story(), "en", "ta").system or ""
    assert "into playful, rhyming Tamil that a young child" in system


@pytest.mark.parametrize(
    ("count", "wording"),
    [(0, '"sound_effects" is always an empty list.'), (3, "zero to three gentle sound cues")],
)
def test_sound_effect_limit_reaches_the_prompt(count: int, wording: str) -> None:
    settings = quick_settings(sound_effects={"max_per_scene": count})
    assert wording in story_request(settings, "sharing", "en").prompt


def test_sound_effect_limit_falls_back_to_digits_without_speech_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(prompt_parts, "speech_rules", lambda _language: None)
    assert prompt_parts.sound_effect_rule(3).startswith("lists zero to 3 gentle")


def test_cast_per_episode_lists_only_the_episode_cast() -> None:
    _, user = story_prompts(cast_per_episode=2)
    assert 'id "kavin"' in user and 'id "mittu"' in user
    assert 'id "chinnu"' not in user and "kavin leads the story" in user


@pytest.mark.parametrize("seed", ["run-1", "run-2", "run-3", "run-4"])
def test_rotating_lead_leads_the_story_written_for_its_seed(seed: str) -> None:
    settings = quick_settings(story={"lead_mode": "rotate", "cast_per_episode": 1})
    lead = episode_cast(settings, seed)[0].id
    user = story_request(settings, "sharing", "en", seed=seed).prompt
    assert f"{lead} leads the story" in user and f'"characters": ["{lead}"]' in user

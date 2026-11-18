from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from automator.domain.capabilities import TextRequest
from automator.pipelines.kids_story.resources import render_prompt
from automator.pipelines.kids_story.settings.cast import Character
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.story.model import Story, StoryScene
from automator.pipelines.kids_story.styles.resolve import resolve_style

ART_LANGUAGE = "en"
FIRST_NUMBER = re.compile(r"\d+")


def descriptor_line(member: Character) -> str:
    name = member.name.for_language(ART_LANGUAGE)
    return f"{name} the {member.species}: {member.visual_descriptor}."


def characters_text(settings: KidsStorySettings, ids: Sequence[str]) -> str:
    return " ".join(descriptor_line(member) for member in settings.characters(ids))


def scene_subject(scene: StoryScene) -> str:
    return " ".join(part for part in (scene.visual, scene.setting, scene.mood) if part)


def thumbnail_subject(story: Story) -> str:
    return story.thumbnail or scene_subject(story.scenes[0])


def scene_prompt(settings: KidsStorySettings, scene: StoryScene) -> str:
    return render_prompt(
        "image_scene.txt",
        style=resolve_style(settings).prompt,
        visual=scene.visual,
        setting=scene.setting,
        mood=scene.mood,
        characters=characters_text(settings, scene.characters),
    )


def character_prompt(settings: KidsStorySettings, member: Character) -> str:
    return render_prompt(
        "image_character.txt",
        style=resolve_style(settings).prompt,
        name=member.name.for_language(ART_LANGUAGE),
        descriptor=member.visual_descriptor,
        palette=", ".join(member.palette) or "soft pastels",
    )


def thumbnail_prompt(settings: KidsStorySettings, story: Story) -> str:
    present = sorted(story.character_ids)
    return render_prompt(
        "image_thumbnail.txt",
        style=resolve_style(settings).prompt,
        description=story.thumbnail or story.scenes[0].visual,
        characters=characters_text(settings, present),
    )


def motion_prompt(scene: StoryScene | None, feel: str = "") -> str:
    visual, mood = ("a title card", "warm") if scene is None else (scene.visual, scene.mood)
    prompt = render_prompt("motion.txt", visual=visual, mood=mood)
    return f"{prompt} Camera: {feel}." if feel else prompt


def judge_request(
    settings: KidsStorySettings, scene: StoryScene, candidates: Sequence[Path]
) -> TextRequest:
    prompt = render_prompt(
        "judge.txt",
        visual=scene.visual,
        characters=characters_text(settings, scene.characters),
        style=resolve_style(settings).prompt,
        count=len(candidates),
    )
    return TextRequest(prompt=prompt, max_tokens=8, temperature=0.0, images=tuple(candidates))


def parse_choice(raw: str, count: int) -> int:
    found = FIRST_NUMBER.search(raw)
    if found is None:
        return 0
    chosen = int(found.group(0)) - 1
    return chosen if 0 <= chosen < count else 0

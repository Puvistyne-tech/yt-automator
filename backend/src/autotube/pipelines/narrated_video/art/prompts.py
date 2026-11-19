from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from autotube.domain.capabilities import TextRequest
from autotube.pipelines.narrated_video.audience_prompts import audience_prompt
from autotube.pipelines.narrated_video.resources import render_prompt
from autotube.pipelines.narrated_video.settings.cast import Character
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.model import Story, StoryScene
from autotube.pipelines.narrated_video.styles.resolve import resolve_style
from autotube.pipelines.narrated_video.text.templates import render_template

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
        audience_prompt("image_scene.txt", settings),
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
        audience_prompt("image_thumbnail.txt", settings),
        style=resolve_style(settings).prompt,
        description=thumbnail_visual(story),
        characters=characters_text(settings, present),
    )


def scene_motion(settings: KidsStorySettings, scene: StoryScene | None) -> str:
    visual, mood = ("a title card", "warm") if scene is None else (scene.visual, scene.mood)
    values = {"visual": visual, "mood": mood}
    return render_template(settings.visuals.motion_prompt, values).strip()


def style_declaration(settings: KidsStorySettings) -> str:
    declared = resolve_style(settings).motion_prompt.strip().rstrip(".")
    return f"{declared}." if declared else ""


def motion_prompt(settings: KidsStorySettings, scene: StoryScene | None, feel: str = "") -> str:
    camera = f"Camera: {feel}." if feel else ""
    parts = (style_declaration(settings), scene_motion(settings, scene), camera)
    return " ".join(part for part in parts if part)


def picture_judge_request(
    settings: KidsStorySettings,
    visual: str,
    character_ids: Sequence[str],
    candidates: Sequence[Path],
) -> TextRequest:
    prompt = render_prompt(
        audience_prompt("judge.txt", settings),
        visual=visual,
        characters=characters_text(settings, character_ids),
        style=resolve_style(settings).prompt,
        count=len(candidates),
        criteria=settings.visuals.judge_criteria,
    )
    return TextRequest(prompt=prompt, max_tokens=8, temperature=0.0, images=tuple(candidates))


def judge_request(
    settings: KidsStorySettings, scene: StoryScene, candidates: Sequence[Path]
) -> TextRequest:
    return picture_judge_request(settings, scene.visual, scene.characters, candidates)


def thumbnail_visual(story: Story) -> str:
    return story.thumbnail or story.scenes[0].visual


def parse_choice(raw: str, count: int) -> int:
    found = FIRST_NUMBER.search(raw)
    if found is None:
        return 0
    chosen = int(found.group(0)) - 1
    return chosen if 0 <= chosen < count else 0

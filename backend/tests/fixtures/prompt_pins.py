from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from autotube.pipelines.narrated_video.art.prompts import (
    judge_request,
    motion_prompt,
    scene_prompt,
    thumbnail_prompt,
)
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.prompts import story_request, translation_request
from tests.fixtures.kids_data import story

PINNED_FOLDER = Path(__file__).parent / "prompts"
GENERAL_FOLDER = PINNED_FOLDER / "general"
PICTURES = (Path("one.png"), Path("two.png"))


def stored_settings() -> dict[str, Any]:
    raw = (PINNED_FOLDER / "stored_settings.json").read_text(encoding="utf-8")
    loaded: dict[str, Any] = json.loads(raw)
    return loaded


def rendered_prompts(settings: KidsStorySettings, sample: Story | None = None) -> dict[str, str]:
    chosen = sample or story()
    english = story_request(settings, "sharing", "en", ["fix scene 2"])
    tamil = story_request(settings, "sharing", "ta")
    translation = translation_request(settings, chosen, "en", "ta")
    scene = chosen.scenes[0]
    return {
        "story_system_en.txt": english.system or "",
        "story_user_en.txt": english.prompt,
        "story_system_ta.txt": tamil.system or "",
        "story_user_ta.txt": tamil.prompt,
        "translate_system_ta.txt": translation.system or "",
        "translate_user_ta.txt": translation.prompt,
        "motion_card.txt": motion_prompt(settings, None),
        "motion_scene.txt": motion_prompt(settings, scene, "slow drift"),
        "judge.txt": judge_request(settings, scene, PICTURES).prompt,
        "image_scene.txt": scene_prompt(settings, scene),
        "image_thumbnail.txt": thumbnail_prompt(settings, chosen),
    }


def pinned_prompt(name: str, folder: Path = PINNED_FOLDER) -> str:
    return (folder / name).read_text(encoding="utf-8")

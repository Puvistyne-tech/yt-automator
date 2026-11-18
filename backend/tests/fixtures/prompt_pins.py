from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from autotube.pipelines.kids_story.art.prompts import judge_request, motion_prompt
from autotube.pipelines.kids_story.settings.root import KidsStorySettings
from autotube.pipelines.kids_story.story.prompts import story_request, translation_request
from tests.fixtures.kids_data import story

PINNED_FOLDER = Path(__file__).parent / "prompts"
PICTURES = (Path("one.png"), Path("two.png"))


def stored_settings() -> dict[str, Any]:
    raw = (PINNED_FOLDER / "stored_settings.json").read_text(encoding="utf-8")
    loaded: dict[str, Any] = json.loads(raw)
    return loaded


def rendered_prompts(settings: KidsStorySettings) -> dict[str, str]:
    english = story_request(settings, "sharing", "en", ["fix scene 2"])
    tamil = story_request(settings, "sharing", "ta")
    translation = translation_request(settings, story(), "en", "ta")
    scene = story().scenes[0]
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
    }


def pinned_prompt(name: str) -> str:
    return (PINNED_FOLDER / name).read_text(encoding="utf-8")

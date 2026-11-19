from __future__ import annotations

from autotube.pipelines.narrated_video.resources import render_prompt
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.prompt_parts import following_bullets
from autotube.pipelines.narrated_video.structures.spec import TranslationRules

CASTLESS_DEFAULTS = "castless_defaults.json"
NO_STORY_LINES = {"ending": "", "speaker": "", "characters": ""}
LABELS_RULE = (
    'Also return "scene_labels": one entry per scene, in the same order, with its "heading", '
    '"question", "choices" and "answer" translated into the same words the narration uses. '
    "Keep an empty value empty."
)


def castless_values(prompt_file: str, **fields: object) -> dict[str, str]:
    return {**NO_STORY_LINES, "structure_rules": render_prompt(prompt_file, **fields)}


def fixed_rules(rules: tuple[str, ...]) -> TranslationRules:
    def translated(settings: KidsStorySettings, language: str) -> str:  # noqa: ARG001
        return following_bullets(rules)

    return translated

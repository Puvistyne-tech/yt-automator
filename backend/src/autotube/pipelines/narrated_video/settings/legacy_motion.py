from __future__ import annotations

from autotube.pipelines.narrated_video.settings.motion_defaults import (
    GENERAL_MOTION_PROMPT,
    MOTION_PROMPT,
)

LEGACY_MOTION_PROMPTS = {
    "Gentle, slow animation of a children's picture-book scene: {visual}. Mood: {mood}. "
    "Soft natural movement, no sudden changes.": MOTION_PROMPT,
    "Slow, natural animation of an illustrated story scene: {visual}. Mood: {mood}. "
    "Soft natural movement, no sudden changes.": GENERAL_MOTION_PROMPT,
}


def upgraded_motion_prompt(value: object) -> object:
    return LEGACY_MOTION_PROMPTS.get(value, value) if isinstance(value, str) else value

from __future__ import annotations

from automator.pipelines.kids_story.settings.look import LookSettings
from automator.pipelines.kids_story.styles.colour_names import colour_words
from automator.pipelines.kids_story.styles.modifiers import (
    BACKGROUND_PROMPTS,
    DETAIL_PROMPTS,
    LIGHTING_PROMPTS,
    MOOD_PROMPTS,
    PROPORTION_PROMPTS,
    ColourMood,
)


def mood_prompt(look: LookSettings) -> str:
    text = MOOD_PROMPTS.get(look.colour_mood, "")
    if look.colour_mood is ColourMood.CUSTOM:
        return text.format(colours=colour_words(look.mood_palette))
    return text


def modifier_prompts(look: LookSettings) -> list[str]:
    return [
        mood_prompt(look),
        LIGHTING_PROMPTS.get(look.lighting, ""),
        DETAIL_PROMPTS.get(look.detail_level, ""),
        BACKGROUND_PROMPTS.get(look.background, ""),
        PROPORTION_PROMPTS.get(look.proportions, ""),
    ]

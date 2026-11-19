from __future__ import annotations

from collections.abc import Sequence

from autotube.pipelines.narrated_video.settings.story_choices import (
    EndingStyle,
    says_moral,
    says_refrain,
)
from autotube.pipelines.narrated_video.story.normalise import speech_rules
from autotube.pipelines.narrated_video.story.numbers import number_to_words

CUE_LANGUAGE = "en"
KIDS_LISTENERS = "children"
GENERAL_LISTENERS = "viewers"
OPEN_ENDING = (
    "The story ends openly and gently, without saying the moral aloud or a refrain, "
    "so {listeners} can wonder what happens next."
)
MORAL_RULE = "The moral must appear word for word, as you translate it, inside the last narration."
NO_CUES = "is always an empty list."


def bullet_lines(items: Sequence[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def kept_lines(items: Sequence[str]) -> list[str]:
    return [item.strip() for item in items if item.strip()]


def following_bullets(items: Sequence[str]) -> str:
    return "".join(f"\n- {item}" for item in items)


def extra_requirements(text: str) -> str:
    return following_bullets(kept_lines(text.splitlines()))


def avoided_topics(topics: Sequence[str]) -> str:
    kept = kept_lines(topics)
    return f"\n\nNever write about these topics:\n{bullet_lines(kept)}" if kept else ""


def listeners(for_kids: bool) -> str:
    return KIDS_LISTENERS if for_kids else GENERAL_LISTENERS


def ending_requirement(style: EndingStyle, refrain: str, for_kids: bool) -> str:
    if style is EndingStyle.MORAL_AND_REFRAIN:
        return (
            "The last scene says the moral word for word, then ends with this exact refrain: "
            f'"{refrain}"'
        )
    if style is EndingStyle.REFRAIN_ONLY:
        return (
            f'The last scene ends with this exact refrain: "{refrain}". Do not say the moral '
            "aloud; let the story show it."
        )
    return OPEN_ENDING.format(listeners=listeners(for_kids))


def translation_ending_rules(style: EndingStyle, refrain: str) -> str:
    rules = [MORAL_RULE] if says_moral(style) else []
    if says_refrain(style):
        rules.append(f'The last narration must end with this exact refrain: "{refrain}"')
    return following_bullets(rules)


def number_word(count: int) -> str:
    rules = speech_rules(CUE_LANGUAGE)
    return number_to_words(count, rules.numbers) if rules else str(count)


def sound_effect_rule(count: int) -> str:
    if count == 0:
        return NO_CUES
    return (
        f"lists zero to {number_word(count)} gentle sound cues per scene, in English, "
        'like "birds chirping".'
    )

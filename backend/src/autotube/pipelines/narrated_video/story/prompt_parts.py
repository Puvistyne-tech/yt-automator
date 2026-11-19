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
NARROW_SCENE_SPAN = 1
KIDS_LISTENERS = "children"
GENERAL_LISTENERS = "viewers"
OPEN_ENDING = (
    "The story ends openly and gently, without saying the moral aloud or a refrain, "
    "so {listeners} can wonder what happens next."
)
MORAL_RULE = "The moral must appear word for word, as you translate it, inside the last narration."
SAY_MORAL = "The last scene says the moral word for word."
SHOW_MORAL = "Do not say the moral aloud; let the story show it."
NO_CUES = "is always an empty list."
SPEAKER_RULE = '"speaker" is "narrator", or a character id if that character says the whole scene.'
ACTION_RULE = (
    "For each scene, also write `action`: one short present-tense sentence describing the one "
    "main visible movement in the picture, with one subject doing one thing (for example: "
    "'{example}'). Do not mention the camera, dialogue, sounds, text or more than one event."
)
KIDS_ACTION_EXAMPLE = "The little fox trots along the riverbank and sniffs a paper boat."
GENERAL_ACTION_EXAMPLE = "The baker slides a tray of bread into the glowing oven."


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


def action_rule(for_kids: bool) -> str:
    return ACTION_RULE.format(example=KIDS_ACTION_EXAMPLE if for_kids else GENERAL_ACTION_EXAMPLE)


def scene_words_rule(span: tuple[int, int]) -> str:
    low, high = span
    if high - low > NARROW_SCENE_SPAN:
        return f"Each scene's narration has between {low} and {high} words"
    about = f"Write about {(low + high + 1) // 2} words in each scene's narration"
    return about if low == high else f"{about}, from {low} to {high}"


def ending_requirement(style: EndingStyle, refrain: str, for_kids: bool) -> str:
    if style is EndingStyle.OPEN:
        return OPEN_ENDING.format(listeners=listeners(for_kids))
    says = style is EndingStyle.MORAL_AND_REFRAIN
    if not refrain.strip():
        return SAY_MORAL if says else SHOW_MORAL
    if says:
        return f'{SAY_MORAL[:-1]}, then ends with this exact refrain: "{refrain}"'
    return f'The last scene ends with this exact refrain: "{refrain}". {SHOW_MORAL}'


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

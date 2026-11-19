from __future__ import annotations

from functools import partial

from autotube.pipelines.narrated_video.publishing.placeholder_values import (
    STORY_PLACEHOLDERS,
    story_values,
)
from autotube.pipelines.narrated_video.scoring.content_items import (
    character_consistency,
    moral_and_refrain,
)
from autotube.pipelines.narrated_video.settings.cast import Character
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import StoryCheck, Structure
from autotube.pipelines.narrated_video.story.casting import episode_cast
from autotube.pipelines.narrated_video.story.gates import (
    CheckedGate,
    cast_problems,
    ending_problems,
)
from autotube.pipelines.narrated_video.story.prompt_parts import (
    bullet_lines,
    translation_ending_rules,
)
from autotube.pipelines.narrated_video.structures.spec import StructureSpec

ENDING_GATE: CheckedGate = (StoryCheck.ENDING, ending_problems)


def cast_line(member: Character, language: str) -> str:
    return (
        f'id "{member.id}": {member.name.for_language(language)}, a {member.species}. '
        f"Looks: {member.visual_descriptor}. Personality: {member.personality}"
    )


def cast_values(settings: KidsStorySettings, language: str, seed: str) -> dict[str, str]:
    cast = episode_cast(settings, seed)
    return {
        "lead": cast[0].id,
        "cast": bullet_lines([cast_line(member, language) for member in cast]),
        "morals": bullet_lines(settings.story.morals),
    }


def ending_rules(settings: KidsStorySettings, language: str) -> str:
    refrain = settings.series.refrain.for_language(language)
    return translation_ending_rules(settings.story.ending_style, refrain)


def story_gates(seed: str) -> tuple[CheckedGate, ...]:
    return (ENDING_GATE, (StoryCheck.CAST, partial(cast_problems, seed=seed)))


STORY_SPEC = StructureSpec(
    id=Structure.STORY,
    title="Story with a recurring cast",
    system_prompt="story_system.txt",
    user_prompt="story_user.txt",
    prompt_values=cast_values,
    translation_rules=ending_rules,
    extra_gates=story_gates,
    translation_gates=(ENDING_GATE,),
    score_rules=(moral_and_refrain, character_consistency),
    placeholders=STORY_PLACEHOLDERS,
    placeholder_values=story_values,
    uses_bundled=True,
)

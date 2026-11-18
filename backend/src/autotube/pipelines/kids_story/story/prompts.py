from __future__ import annotations

import json
from collections.abc import Sequence

from autotube.domain.capabilities import CameraMove, TextRequest
from autotube.pipelines.kids_story.languages import language_name
from autotube.pipelines.kids_story.resources import render_prompt, resource_json
from autotube.pipelines.kids_story.settings.cast import Character
from autotube.pipelines.kids_story.settings.root import KidsStorySettings
from autotube.pipelines.kids_story.story.casting import episode_cast
from autotube.pipelines.kids_story.story.model import StoryDraft, StoryText, text_of
from autotube.pipelines.kids_story.story.prompt_parts import (
    avoided_topics,
    bullet_lines,
    ending_requirement,
    extra_requirements,
    sound_effect_rule,
    translation_ending_rules,
)


def cast_line(member: Character, language: str) -> str:
    return (
        f'id "{member.id}": {member.name.for_language(language)}, a {member.species}. '
        f"Looks: {member.visual_descriptor}. Personality: {member.personality}"
    )


def reading_level_text(settings: KidsStorySettings) -> str:
    levels = resource_json("prompts", "reading_levels.json")
    level = settings.story.reading_level.value
    return str(levels[level]) if isinstance(levels, dict) and level in levels else level


def story_system(settings: KidsStorySettings, language: str) -> str:
    return render_prompt(
        "story_system.txt",
        series=settings.series.name.for_language(language),
        tagline=settings.series.tagline.for_language(language),
        age_min=settings.story.age_min,
        age_max=settings.story.age_max,
        tone=settings.story.tone,
        rules=bullet_lines(settings.series.editorial_rules),
        avoid_topics=avoided_topics(settings.safety.avoid_topics),
        reading_level=reading_level_text(settings),
    )


def style_values(settings: KidsStorySettings, language: str) -> dict[str, str]:
    rules = settings.story
    refrain = settings.series.refrain.for_language(language)
    return {
        "writing_style": rules.writing_style,
        "extra_instructions": extra_requirements(rules.extra_instructions),
        "ending": ending_requirement(rules.ending_style, refrain),
        "sound_effects": sound_effect_rule(settings.sound_effects.max_per_scene),
        "question_style": rules.question_style,
        "hook_style": settings.short.hook_style,
    }


def story_user(settings: KidsStorySettings, theme: str, language: str, seed: str = "") -> str:
    rules = settings.story
    cast = episode_cast(settings, seed)
    return render_prompt(
        "story_user.txt",
        language=language_name(language),
        series=settings.series.name.for_language(language),
        theme=theme,
        lead=cast[0].id,
        cast=bullet_lines([cast_line(member, language) for member in cast]),
        morals=bullet_lines(rules.morals),
        scene_min=rules.scene_count_min,
        scene_max=rules.scene_count_max,
        words_min=f"{rules.words_per_scene_min.for_language(language):g}",
        words_max=f"{rules.words_per_scene_max.for_language(language):g}",
        target_seconds=rules.target_duration_seconds,
        words_per_minute=f"{rules.words_per_minute.for_language(language):g}",
        cameras=", ".join(move.value for move in CameraMove),
        hero_count=settings.visuals.hero_scene_count,
        question_count=rules.question_count,
        short_scenes=settings.short.max_scenes,
        **style_values(settings, language),
    )


def feedback_text(feedback: Sequence[str]) -> str:
    return render_prompt("story_retry.txt", feedback=bullet_lines(feedback)) if feedback else ""


def story_request(
    settings: KidsStorySettings,
    theme: str,
    language: str,
    feedback: Sequence[str] = (),
    seed: str = "",
) -> TextRequest:
    user = story_user(settings, theme, language, seed)
    retry = feedback_text(feedback)
    return TextRequest(
        prompt=f"{user}\n\n{retry}" if retry else user,
        system=story_system(settings, language),
        max_tokens=settings.story.max_tokens,
        temperature=settings.story.temperature,
        json_schema=StoryDraft.model_json_schema(),
    )


def translation_user(
    settings: KidsStorySettings, story: StoryDraft, source: str, target: str
) -> str:
    names = ", ".join(
        f"{member.name.for_language(source)} = {member.name.for_language(target)}"
        for member in settings.cast
    )
    text = text_of(story)
    refrain = settings.series.refrain.for_language(target)
    return render_prompt(
        "translate_user.txt",
        source_language=language_name(source),
        language=language_name(target),
        scene_count=len(text.narrations),
        question_count=len(text.questions),
        ending_rules=translation_ending_rules(settings.story.ending_style, refrain),
        names=names,
        story=json.dumps(text.model_dump(mode="json"), ensure_ascii=False, indent=2),
    )


def translation_request(
    settings: KidsStorySettings, story: StoryDraft, source: str, target: str
) -> TextRequest:
    system = render_prompt(
        "translate_system.txt",
        series=settings.series.name.for_language(target),
        language=language_name(target),
        translation_style=settings.story.translation_style,
    )
    return TextRequest(
        prompt=translation_user(settings, story, source, target),
        system=system,
        max_tokens=settings.story.max_tokens,
        temperature=settings.story.translation_temperature,
        json_schema=StoryText.model_json_schema(),
    )

from __future__ import annotations

from autotube.pipelines.narrated_video.resources import render_prompt
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import Structure
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.prompt_parts import following_bullets
from autotube.pipelines.narrated_video.structures.explainer_checks import (
    EXPLAINER_GATES,
    explainer_seeded_gates,
    explainer_shape,
)
from autotube.pipelines.narrated_video.structures.spec import StructureSpec

FORMAT = "explainer"
TRANSLATION_RULES = (
    "The first narration still asks the question the video answers, with a question mark.",
    'The takeaway in "moral" must appear word for word, as you translate it, inside the last '
    "narration.",
)
HIDDEN_PATHS = (
    "cast",
    "story.morals",
    "story.ending_style",
    "story.ending_scenes",
    "story.lead_mode",
    "story.cast_per_episode",
    "series.refrain",
    "visuals.character_sheets",
    "quality.weights.moral_and_refrain",
    "quality.weights.character_consistency",
)


def explainer_values(
    settings: KidsStorySettings,  # noqa: ARG001
    language: str,  # noqa: ARG001
    seed: str,  # noqa: ARG001
) -> dict[str, str]:
    return {"format": FORMAT, "structure_rules": render_prompt("explainer.txt")}


def explainer_rules(settings: KidsStorySettings, language: str) -> str:  # noqa: ARG001
    return following_bullets(TRANSLATION_RULES)


def takeaway_values(story: Story, settings: KidsStorySettings) -> dict[str, str]:  # noqa: ARG001
    return {"takeaway": story.moral}


EXPLAINER_SPEC = StructureSpec(
    id=Structure.EXPLAINER,
    title="Explainer",
    system_prompt="script_system.txt",
    user_prompt="script_user.txt",
    prompt_values=explainer_values,
    translation_rules=explainer_rules,
    extra_gates=explainer_seeded_gates,
    translation_gates=EXPLAINER_GATES,
    score_rules=(explainer_shape,),
    placeholders=("takeaway",),
    placeholder_values=takeaway_values,
    hidden_paths=HIDDEN_PATHS,
    defaults_file="explainer_defaults.json",
)

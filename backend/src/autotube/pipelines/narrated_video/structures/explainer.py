from __future__ import annotations

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import Structure
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.prompt_parts import following_bullets
from autotube.pipelines.narrated_video.structures.castless import castless_values
from autotube.pipelines.narrated_video.structures.explainer_checks import (
    explainer_problems,
    takeaway_field_problems,
    wants_takeaway,
)
from autotube.pipelines.narrated_video.structures.shape_spec import Shape, shape_spec

WORDING = {
    "format": "narrated explainer",
    "pieces": "explainer scripts",
    "piece": "explainer script",
}
HOOK_RULE = "The first narration still asks the question the video answers, with a question mark."
TAKEAWAY_RULE = (
    'The takeaway in "moral" must appear word for word, as you translate it, inside the last '
    "narration."
)
TAKEAWAY_RECAP = (
    "- The last scene is the recap: it sums up the answer and says the takeaway word for word.\n"
    '- "moral" holds the takeaway: one short sentence the viewer should remember.'
)
OPEN_RECAP = (
    "- The last scene is the recap: it sums up the answer in its own words.\n"
    '- "moral" is an empty string.'
)
EXPLAINER_PATHS = ("story.ending_style",)


def recap_rule(settings: KidsStorySettings) -> str:
    return TAKEAWAY_RECAP if wants_takeaway(settings) else OPEN_RECAP


def explainer_values(
    settings: KidsStorySettings,
    language: str,  # noqa: ARG001
    seed: str,  # noqa: ARG001
) -> dict[str, str]:
    return castless_values("explainer.txt", recap=recap_rule(settings))


def explainer_translation_rules(settings: KidsStorySettings, language: str) -> str:  # noqa: ARG001
    rules = [HOOK_RULE, TAKEAWAY_RULE] if wants_takeaway(settings) else [HOOK_RULE]
    return following_bullets(rules)


def takeaway_values(story: Story, settings: KidsStorySettings) -> dict[str, str]:  # noqa: ARG001
    return {"takeaway": story.moral}


EXPLAINER_SPEC = shape_spec(
    Shape(
        structure=Structure.EXPLAINER,
        title="Explainer",
        wording=WORDING,
        problems=explainer_problems,
        score_title="Explainer hook and takeaway",
        prompt_values=explainer_values,
        translation_rules=explainer_translation_rules,
        placeholders=("takeaway",),
        placeholder_values=takeaway_values,
        leading_gates=((None, takeaway_field_problems),),
        shown_paths=EXPLAINER_PATHS,
        moral_required=wants_takeaway,
    )
)

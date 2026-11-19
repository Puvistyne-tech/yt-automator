from __future__ import annotations

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import Structure
from autotube.pipelines.narrated_video.story.gates import MORAL_GATE
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.structures.castless import castless_values
from autotube.pipelines.narrated_video.structures.explainer_checks import explainer_problems
from autotube.pipelines.narrated_video.structures.shape_spec import Shape, shape_spec

WORDING = {
    "format": "narrated explainer",
    "pieces": "explainer scripts",
    "piece": "explainer script",
}
TRANSLATION_RULES = (
    "The first narration still asks the question the video answers, with a question mark.",
    'The takeaway in "moral" must appear word for word, as you translate it, inside the last '
    "narration.",
)


def explainer_values(
    settings: KidsStorySettings,  # noqa: ARG001
    language: str,  # noqa: ARG001
    seed: str,  # noqa: ARG001
) -> dict[str, str]:
    return castless_values("explainer.txt")


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
        translation_rules=TRANSLATION_RULES,
        placeholders=("takeaway",),
        placeholder_values=takeaway_values,
        leading_gates=(MORAL_GATE,),
    )
)

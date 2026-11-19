from __future__ import annotations

from collections.abc import Mapping
from functools import partial

from autotube.pipelines.narrated_video.languages import language_name
from autotube.pipelines.narrated_video.resources import render_prompt
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import StoryCheck, Structure
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.prompt_parts import following_bullets
from autotube.pipelines.narrated_video.structures.castless import LABELS_RULE, NO_STORY_LINES
from autotube.pipelines.narrated_video.structures.list_checks import (
    list_problems,
    list_scenes,
    numbered,
    order_text,
)
from autotube.pipelines.narrated_video.structures.paths import (
    COUNTED_HIDDEN_PATHS,
    LIST_COUNT_PATHS,
)
from autotube.pipelines.narrated_video.structures.shape_score import structure_item
from autotube.pipelines.narrated_video.structures.spec import StructureSpec, unseeded

TRANSLATION_RULES = (
    LABELS_RULE,
    "Keep every item heading different, and keep each item's number in its narration.",
)
HIDDEN_PATHS = COUNTED_HIDDEN_PATHS


def numbered_prompt_values(
    settings: KidsStorySettings,
    language: str,
    seed: str,  # noqa: ARG001
    descending: bool,
    piece: str,
) -> dict[str, str]:
    count = settings.story.item_count
    rules = render_prompt(
        "numbered_list.txt",
        piece=piece,
        count=count,
        order=order_text(count, descending),
        language=language_name(language),
    )
    return {**NO_STORY_LINES, "structure_rules": rules}


def numbered_rules(settings: KidsStorySettings, language: str) -> str:  # noqa: ARG001
    return following_bullets(TRANSLATION_RULES)


def item_values(story: Story, settings: KidsStorySettings) -> dict[str, str]:  # noqa: ARG001
    items = numbered(story)
    return {"count": str(len(items)), "items": ", ".join(scene.heading for scene in items)}


def numbered_spec(
    structure: Structure, title: str, wording: Mapping[str, str], descending: bool
) -> StructureSpec:
    gates = ((StoryCheck.STRUCTURE, partial(list_problems, descending=descending)),)
    return StructureSpec(
        id=structure,
        title=title,
        wording=wording,
        prompt_values=partial(
            numbered_prompt_values, descending=descending, piece=wording["piece"]
        ),
        translation_rules=numbered_rules,
        extra_gates=unseeded(gates),
        translation_gates=gates,
        score_rules=(structure_item(f"{title} numbering and headings", gates[0][1]),),
        placeholders=("count", "items"),
        placeholder_values=item_values,
        hidden_paths=HIDDEN_PATHS,
        shown_paths=LIST_COUNT_PATHS,
        defaults_file=f"{structure.value}_defaults.json",
        fixed_scenes=list_scenes,
    )


LIST_SPEC = numbered_spec(
    Structure.LIST,
    "List",
    {"format": "numbered list", "pieces": "list scripts", "piece": "list script"},
    descending=False,
)
COUNTDOWN_SPEC = numbered_spec(
    Structure.COUNTDOWN,
    "Countdown",
    {"format": "countdown", "pieces": "countdown scripts", "piece": "countdown script"},
    descending=True,
)

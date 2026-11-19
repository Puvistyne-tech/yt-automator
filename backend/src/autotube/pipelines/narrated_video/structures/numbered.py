from __future__ import annotations

from collections.abc import Mapping
from functools import partial

from autotube.pipelines.narrated_video.languages import language_name
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.story_choices import Structure
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.structures.castless import LABELS_RULE, castless_values
from autotube.pipelines.narrated_video.structures.list_checks import (
    list_problems,
    list_scenes,
    numbered,
    order_text,
)
from autotube.pipelines.narrated_video.structures.paths import COUNTED_PATHS, LIST_COUNT_PATHS
from autotube.pipelines.narrated_video.structures.shape_spec import Shape, shape_spec
from autotube.pipelines.narrated_video.structures.spec import StructureSpec

TRANSLATION_RULES = (
    LABELS_RULE,
    "Keep every item heading different, and keep each item's number in its narration.",
)


def numbered_prompt_values(
    settings: KidsStorySettings,
    language: str,
    seed: str,  # noqa: ARG001
    descending: bool,
    piece: str,
) -> dict[str, str]:
    count = settings.story.item_count
    return castless_values(
        "numbered_list.txt",
        piece=piece,
        count=count,
        order=order_text(count, descending),
        language=language_name(language),
    )


def item_values(story: Story, settings: KidsStorySettings) -> dict[str, str]:  # noqa: ARG001
    items = numbered(story)
    return {"count": str(len(items)), "items": ", ".join(scene.heading for scene in items)}


def numbered_spec(
    structure: Structure, title: str, wording: Mapping[str, str], descending: bool
) -> StructureSpec:
    values = partial(numbered_prompt_values, descending=descending, piece=wording["piece"])
    return shape_spec(
        Shape(
            structure=structure,
            title=title,
            wording=wording,
            problems=partial(list_problems, descending=descending),
            score_title=f"{title} numbering and headings",
            prompt_values=values,
            translation_rules=TRANSLATION_RULES,
            placeholders=("count", "items"),
            placeholder_values=item_values,
            hidden_paths=COUNTED_PATHS,
            shown_paths=LIST_COUNT_PATHS,
            fixed_scenes=list_scenes,
        )
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

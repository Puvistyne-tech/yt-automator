from __future__ import annotations

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.model import Story, StoryScene

FRAMING_SCENES = 2


def numbered(story: Story) -> list[StoryScene]:
    return [scene for scene in story.scenes if scene.number is not None]


def list_scene_range(settings: KidsStorySettings) -> tuple[int, int]:
    total = settings.story.item_count + FRAMING_SCENES
    return total, total


def expected_numbers(count: int, descending: bool) -> list[int]:
    numbers = list(range(1, count + 1))
    return numbers[::-1] if descending else numbers


def order_text(count: int, descending: bool) -> str:
    if descending:
        return f"from {count} down to 1, so the last item is number 1"
    return f"from 1 up to {count}, in that order"


def framing_problems(story: Story) -> list[str]:
    ends = (story.scenes[0], story.scenes[-1])
    if len(story.scenes) > 1 and all(scene.number is None for scene in ends):
        return []
    return ["open with an intro scene and end with a closing scene, both without a number"]


def item_count_problems(story: Story, settings: KidsStorySettings) -> list[str]:
    wanted, found = settings.story.item_count, len(numbered(story))
    return [] if found == wanted else [f"write exactly {wanted} numbered items, not {found}"]


def order_problems(story: Story, descending: bool) -> list[str]:
    numbers = [scene.number for scene in numbered(story)]
    if numbers == expected_numbers(len(numbers), descending):
        return []
    return [f"number the items {order_text(len(numbers), descending)}"]


def heading_problems(story: Story) -> list[str]:
    headings = [scene.heading.strip().casefold() for scene in numbered(story)]
    written = [heading for heading in headings if heading]
    problems = [] if len(written) == len(headings) else ["give every item a short heading"]
    if len(set(written)) < len(written):
        problems.append("give every item its own heading")
    return problems


def list_problems(story: Story, settings: KidsStorySettings, descending: bool = False) -> list[str]:
    return [
        *framing_problems(story),
        *item_count_problems(story, settings),
        *order_problems(story, descending),
        *heading_problems(story),
    ]

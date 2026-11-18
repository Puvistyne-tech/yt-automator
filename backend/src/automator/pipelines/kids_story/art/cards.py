from __future__ import annotations

import shutil
from collections.abc import Sequence
from pathlib import Path

from automator.pipelines.kids_story.art.imaging import covered_copy
from automator.pipelines.kids_story.art.lettering import Lettering, Placement, lettered
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.story.model import Story


def lettering_for(
    settings: KidsStorySettings,
    lines: Sequence[str],
    language: str,
    placement: Placement,
    size_ratio: float,
) -> Lettering:
    thumbnail = settings.thumbnail
    return Lettering(
        lines=tuple(line for line in lines if line),
        language=language,
        font_files=tuple(thumbnail.font_files.for_language(language)),
        color=thumbnail.text_color,
        outline=thumbnail.outline_color,
        size_ratio=size_ratio,
        margin_ratio=thumbnail.margin_ratio,
        outline_ratio=thumbnail.outline_ratio,
        placement=placement,
    )


def card_lines(settings: KidsStorySettings, story: Story, card: str) -> list[str]:
    series = settings.series.name.for_language(story.language)
    if card == "intro":
        return [series, story.title]
    return [settings.series.refrain.for_language(story.language), series]


def resized_or_copied(source: Path, output: Path, size: tuple[int, int]) -> Path:
    if covered_copy(source, output, size, 0.5) is None:
        shutil.copyfile(source, output)
    return output


def lettered_or_plain(source: Path, output: Path, lettering: Lettering) -> bool:
    if lettering.lines and lettered(source, output, lettering):
        return True
    if source != output:
        shutil.copyfile(source, output)
    return False

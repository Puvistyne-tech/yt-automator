from __future__ import annotations

import shutil
from collections.abc import Sequence
from pathlib import Path

from automator.domain.pipeline import StageLog
from automator.domain.run_enums import LogLevel
from automator.pipelines.kids_story.art.imaging import covered_copy
from automator.pipelines.kids_story.art.lettering import Lettering, lettered
from automator.pipelines.kids_story.settings.base import Placement
from automator.pipelines.kids_story.settings.media import VisualSettings
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.story.model import Story
from automator.pipelines.kids_story.text.scripts import script_language

CENTRED = 0.5


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
    if covered_copy(source, output, size, CENTRED) is None:
        shutil.copyfile(source, output)
    return output


def lettered_or_plain(source: Path, output: Path, lettering: Lettering) -> bool:
    if lettering.lines and lettered(source, output, lettering):
        return True
    if source != output:
        shutil.copyfile(source, output)
    return False


def wants_badge(visuals: VisualSettings) -> bool:
    return visuals.overlay_series_badge and bool(visuals.badge_text.strip())


def badged_copy(source: Path, output: Path, settings: KidsStorySettings, log: StageLog) -> Path:
    visuals = settings.visuals
    if not wants_badge(visuals):
        return source
    text = visuals.badge_text.strip()
    lettering = lettering_for(
        settings, [text], script_language(text), visuals.badge_corner, visuals.badge_size_ratio
    )
    if lettered(source, output, lettering):
        return output
    log(
        f"brand mark skipped on {source.name}: no usable font or text shaping",
        LogLevel.WARNING,
    )
    return source

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from automator.domain.font_names import safe_font_family
from automator.pipelines.kids_story.art import lettering
from automator.pipelines.kids_story.art.lettering import Font
from automator.pipelines.kids_story.settings.subtitles import SubtitleSettings
from automator.pipelines.kids_story.text.graphemes import grapheme_length


@dataclass(frozen=True)
class SubtitleFont:
    family: str
    file: Path | None
    measure: Callable[[str], float]


def estimated_width(size: int, letter_width: float) -> Callable[[str], float]:
    def measure(text: str) -> float:
        return grapheme_length(text) * size * letter_width

    return measure


def measured_width(font: Font) -> Callable[[str], float]:
    def measure(text: str) -> float:
        return float(font.getlength(text))

    return measure


def measurable_font(
    settings: SubtitleSettings, language: str, size: int
) -> tuple[Path, Font] | None:
    if not lettering.can_letter(language):
        return None
    return lettering.load_font(settings.font_files.for_language(language), size)


def subtitle_font(settings: SubtitleSettings, language: str, size: int) -> SubtitleFont:
    fallback = settings.font_family.for_language(language)
    loaded = measurable_font(settings, language, size)
    if loaded is None:
        letter_width = settings.letter_width_estimate.for_language(language)
        return SubtitleFont(family=fallback, file=None, measure=estimated_width(size, letter_width))
    file, font = loaded
    named = str(font.getname()[0])
    family = named if safe_font_family(named) else fallback
    return SubtitleFont(family=family, file=file, measure=measured_width(font))

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from autotube.domain.font_names import safe_font_family
from autotube.pipelines.kids_story.art import lettering
from autotube.pipelines.kids_story.art.lettering import Font
from autotube.pipelines.kids_story.settings.subtitles import SubtitleSettings
from autotube.pipelines.kids_story.text.graphemes import grapheme_length


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


def subtitle_font(settings: SubtitleSettings, language: str, size: int) -> SubtitleFont:
    fallback = settings.font_family.for_language(language)
    letter_width = settings.letter_width_estimate.for_language(language)
    estimate = SubtitleFont(family=fallback, file=None, measure=estimated_width(size, letter_width))
    loaded = lettering.load_font(settings.font_files.for_language(language), size)
    if loaded is None:
        return estimate
    file, font = loaded
    named = str(font.getname()[0])
    if not safe_font_family(named):
        return estimate
    shaped = lettering.can_letter(language)
    measure = measured_width(font) if shaped else estimate.measure
    return SubtitleFont(family=named, file=file, measure=measure)

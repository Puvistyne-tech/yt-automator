from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from automator.pipelines.kids_story.art.lettering import Font, load_font
from automator.pipelines.kids_story.settings.subtitles import SubtitleSettings
from automator.pipelines.kids_story.text.graphemes import grapheme_length


@dataclass(frozen=True)
class SubtitleFont:
    family: str
    file: Path | None
    measure: Callable[[str], float]


def first_font_file(files: list[str]) -> Path | None:
    return next((Path(name) for name in files if Path(name).is_file()), None)


def estimated_width(size: int, letter_width: float) -> Callable[[str], float]:
    def measure(text: str) -> float:
        return grapheme_length(text) * size * letter_width

    return measure


def measured_width(font: Font) -> Callable[[str], float]:
    def measure(text: str) -> float:
        return float(font.getlength(text))

    return measure


def subtitle_font(settings: SubtitleSettings, language: str, size: int) -> SubtitleFont:
    file = first_font_file(settings.font_files.for_language(language))
    font = load_font([str(file)], size) if file is not None else None
    if file is None or font is None:
        letter_width = settings.letter_width_estimate.for_language(language)
        family = settings.font_family.for_language(language)
        return SubtitleFont(family=family, file=None, measure=estimated_width(size, letter_width))
    return SubtitleFont(family=str(font.getname()[0]), file=file, measure=measured_width(font))

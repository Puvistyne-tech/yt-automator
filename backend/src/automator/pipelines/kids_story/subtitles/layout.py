from __future__ import annotations

from dataclasses import dataclass

from automator.pipelines.kids_story.artifacts import SHORT
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.subtitles.subtitle_font import SubtitleFont, subtitle_font


@dataclass(frozen=True)
class SubtitleLayout:
    font: SubtitleFont
    font_size: int
    width: int
    side_margin: int
    bottom_margin: int
    max_chars: int
    max_lines: int

    @property
    def line_width(self) -> int:
        return max(1, self.width - 2 * self.side_margin)


def subtitle_layout(settings: KidsStorySettings, language: str, variant: str) -> SubtitleLayout:
    subtitles = settings.subtitles
    short = variant == SHORT
    width, height = settings.video_size(variant)
    size = subtitles.short_font_size if short else subtitles.font_size
    bottom = subtitles.short_bottom_margin_share if short else subtitles.bottom_margin_share
    return SubtitleLayout(
        font=subtitle_font(subtitles, language, size),
        font_size=size,
        width=width,
        side_margin=round(width * subtitles.side_margin_share),
        bottom_margin=round(height * bottom),
        max_chars=subtitles.short_max_chars_per_line if short else subtitles.max_chars_per_line,
        max_lines=subtitles.short_max_lines if short else subtitles.max_lines,
    )

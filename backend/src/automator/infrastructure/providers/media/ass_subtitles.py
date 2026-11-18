from __future__ import annotations

from pathlib import Path

from automator.domain.capabilities import VideoComposition
from automator.domain.srt import parse_srt
from automator.infrastructure.providers.media.ass_document import ass_document
from automator.infrastructure.providers.media.subtitle_filter import ASS_SUFFIX


def with_ass_subtitles(
    composition: VideoComposition, size: tuple[int, int], output: Path, outline: float
) -> VideoComposition:
    subtitles = composition.subtitles
    burned = composition.subtitle_style.burn_in
    if subtitles is None or not burned or subtitles.suffix.lower() == ASS_SUFFIX:
        return composition
    entries = parse_srt(subtitles.read_text(encoding="utf-8"))
    document = ass_document(entries, composition.subtitle_style, size, outline)
    target = output.with_suffix(ASS_SUFFIX)
    target.write_text(document, encoding="utf-8")
    return composition.model_copy(update={"subtitles": target})

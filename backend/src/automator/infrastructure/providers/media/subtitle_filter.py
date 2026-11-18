from __future__ import annotations

from pathlib import Path

from automator.domain.capabilities import SubtitleStyle, VideoComposition
from automator.domain.srt import parse_srt
from automator.infrastructure.providers.media.ass_document import ass_document

OPTION_SPECIALS = ("\\", "'", ":")
GRAPH_SPECIALS = ("\\", "'", "[", "]", ",", ";")
ASS_SUFFIX = ".ass"


def escaped(value: str, specials: tuple[str, ...]) -> str:
    for special in specials:
        value = value.replace(special, f"\\{special}")
    return value


def filter_path(path: Path) -> str:
    return escaped(escaped(str(path), OPTION_SPECIALS), GRAPH_SPECIALS)


def fonts_folder(style: SubtitleStyle, configured: str) -> str:
    return str(style.font_file.parent) if style.font_file is not None else configured


def subtitle_filter(subtitles: Path, style: SubtitleStyle, fonts_dir: str) -> str:
    rendered = f"ass=filename={filter_path(subtitles)}:shaping=complex"
    folder = fonts_folder(style, fonts_dir)
    if folder:
        rendered += f":fontsdir={filter_path(Path(folder))}"
    return rendered


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

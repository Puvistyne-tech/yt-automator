from __future__ import annotations

from pathlib import Path

from automator.domain.capabilities import SubtitleStyle
from automator.shared.errors import UpstreamFailure

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
    if subtitles.suffix.lower() != ASS_SUFFIX:
        raise UpstreamFailure(f"burned-in subtitles must be an ASS file, not {subtitles.name}")
    rendered = f"ass=filename={filter_path(subtitles)}:shaping=complex"
    folder = fonts_folder(style, fonts_dir)
    if folder:
        rendered += f":fontsdir={filter_path(Path(folder))}"
    return rendered

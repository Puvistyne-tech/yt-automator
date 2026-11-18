from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from autotube.domain.capabilities import WordTiming
from autotube.domain.font_names import safe_font_family
from autotube.domain.srt import SrtEntry
from autotube.domain.video_look import SubtitlePosition, SubtitleStyle
from autotube.infrastructure.providers.media.ass_karaoke import karaoke_events
from autotube.infrastructure.providers.media.ass_text import ass_color, ass_text, ass_time
from autotube.shared.errors import UpstreamFailure

NO_WRAPPING = 2
SMART_WRAPPING = 0
OUTLINE_BORDER = "1"
BOX_BORDER = "3"
ASS_TRUE = "-1"
ASS_FALSE = "0"
SHADOW_COLOUR = "&H00000000"
DEFAULT_STYLE = "Default"
SPOKEN_STYLE = "Spoken"
TEXT_LAYER = 0
SPOKEN_LAYER = 1
ALIGNMENTS = {SubtitlePosition.BOTTOM: "2", SubtitlePosition.MIDDLE: "5", SubtitlePosition.TOP: "8"}
STYLE_FORMAT = (
    "Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
    "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
    "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"
)
EVENT_FORMAT = "Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"


@dataclass(frozen=True)
class Edge:
    colour: str
    border: str
    width: str
    shadow: str


def font_name(family: str) -> str:
    if safe_font_family(family):
        return family
    raise UpstreamFailure(
        f"subtitle font {family!r} may only use letters, digits, spaces, '-' and '_'"
    )


def style_entry(name: str, style: SubtitleStyle, primary: str, edge: Edge) -> str:
    fields = [
        name,
        font_name(style.font_family),
        str(style.font_size),
        primary,
        ass_color(style.highlight_color),
        edge.colour,
        SHADOW_COLOUR,
        ASS_TRUE if style.bold else ASS_FALSE,
        *("0", "0", "0", "100", "100", "0", "0"),
        edge.border,
        edge.width,
        edge.shadow,
        ALIGNMENTS[style.position],
        *(str(style.margin_sides),) * 2,
        str(style.margin_bottom),
        "1",
    ]
    return "Style: " + ",".join(fields)


def text_edge(style: SubtitleStyle, outline: float) -> Edge:
    width = f"{outline if style.outline_width is None else style.outline_width:g}"
    if style.box:
        return Edge(
            ass_color(style.box_color, style.box_opacity), BOX_BORDER, width, f"{style.shadow:g}"
        )
    return Edge(ass_color(style.outline_color), OUTLINE_BORDER, width, f"{style.shadow:g}")


def style_line(style: SubtitleStyle, outline: float) -> str:
    return style_entry(
        DEFAULT_STYLE, style, ass_color(style.primary_color), text_edge(style, outline)
    )


def spoken_style_line(style: SubtitleStyle) -> str:
    bare = Edge(ass_color(style.outline_color), OUTLINE_BORDER, "0", "0")
    return style_entry(SPOKEN_STYLE, style, ass_color(style.highlight_color), bare)


def dialogue(layer: int, start: float, end: float, style: str, text: str) -> str:
    return f"Dialogue: {layer},{ass_time(start)},{ass_time(end)},{style},,0,0,0,,{text}"


def entry_dialogues(
    entry: SrtEntry, style: SubtitleStyle, words: Sequence[WordTiming]
) -> list[str]:
    lines = [dialogue(TEXT_LAYER, entry.start, entry.end, DEFAULT_STYLE, ass_text(entry.lines))]
    if style.karaoke:
        lines += [
            dialogue(SPOKEN_LAYER, start, end, SPOKEN_STYLE, text)
            for start, end, text in karaoke_events(entry, words)
        ]
    return lines


def ass_document(
    entries: Sequence[SrtEntry],
    style: SubtitleStyle,
    size: tuple[int, int],
    outline: float,
    words: Sequence[WordTiming] = (),
) -> str:
    width, height = size
    styles = [style_line(style, outline), *([spoken_style_line(style)] if style.karaoke else [])]
    header = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        f"WrapStyle: {SMART_WRAPPING if style.wrap_lines else NO_WRAPPING}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        f"Format: {STYLE_FORMAT}",
        *styles,
        "",
        "[Events]",
        f"Format: {EVENT_FORMAT}",
    ]
    events = [line for entry in entries for line in entry_dialogues(entry, style, words)]
    return "\n".join([*header, *events]) + "\n"

from __future__ import annotations

from pathlib import Path

import pytest

from autotube.domain.capabilities import WordTiming
from autotube.domain.srt import SrtEntry
from autotube.domain.video_look import SubtitlePosition, SubtitleStyle
from autotube.infrastructure.providers.media.ass_document import (
    ass_document,
    spoken_style_line,
    style_line,
)
from autotube.infrastructure.providers.media.ass_karaoke import karaoke_events
from autotube.infrastructure.providers.media.ass_subtitles import with_ass_subtitles
from tests.unit.infrastructure.providers.media_fixtures import composition

STYLE = SubtitleStyle(font_size=40, margin_bottom=50, margin_sides=10)
ENTRY = SrtEntry(start=1.0, end=2.0, lines=("Hello", "friends"))
HELLO = WordTiming(word="Hello", start_seconds=1.0, end_seconds=1.4)
FRIENDS = WordTiming(word="friends", start_seconds=1.5, end_seconds=1.9)
HIDDEN = "{\\alpha&HFF&}"
SHOWN = "{\\alpha&H00&}"


def fields(line: str) -> list[str]:
    return line.split(": ", 1)[1].split(",")


def test_default_style_keeps_todays_fields() -> None:
    assert fields(style_line(STYLE, 3.0))[7:] == [
        *("0", "0", "0", "0", "100", "100", "0", "0", "1", "3", "0", "2"),
        *("10", "10", "50", "1"),
    ]


@pytest.mark.parametrize(
    ("position", "alignment"),
    [(SubtitlePosition.BOTTOM, "2"), (SubtitlePosition.MIDDLE, "5"), (SubtitlePosition.TOP, "8")],
)
def test_position_sets_the_alignment(position: SubtitlePosition, alignment: str) -> None:
    assert fields(style_line(STYLE.model_copy(update={"position": position}), 3.0))[18] == alignment


def test_bold_shadow_and_outline_width_override_the_provider() -> None:
    styled = STYLE.model_copy(update={"bold": True, "shadow": 2.5, "outline_width": 1.0})
    drawn = fields(style_line(styled, 3.0))
    assert (drawn[7], drawn[16], drawn[17]) == ("-1", "1", "2.5")


def test_a_box_uses_its_colour_and_opacity_behind_the_text() -> None:
    boxed = STYLE.model_copy(update={"box": True, "box_color": "#102030", "box_opacity": 0.6})
    drawn = fields(style_line(boxed, 3.0))
    assert (drawn[5], drawn[15]) == ("&H66302010", "3")


def test_the_spoken_style_draws_bare_letters_in_the_highlight_colour() -> None:
    boxed = STYLE.model_copy(update={"box": True, "bold": True, "position": SubtitlePosition.TOP})
    drawn = fields(spoken_style_line(boxed))
    assert (drawn[0], drawn[3], drawn[7]) == ("Spoken", "&H004AD5FF", "-1")
    assert drawn[15:19] == ["1", "0", "0", "8"]


def test_karaoke_shows_each_word_while_it_is_spoken() -> None:
    assert karaoke_events(ENTRY, (HELLO, FRIENDS)) == [
        (1.0, 1.5, f"{HIDDEN}{SHOWN}Hello{HIDDEN}\\Nfriends"),
        (1.5, 2.0, f"{HIDDEN}Hello\\N{SHOWN}friends{HIDDEN}"),
    ]


@pytest.mark.parametrize(
    "words",
    [
        (),
        (HELLO,),
        (HELLO, FRIENDS.model_copy(update={"word": "friend"})),
        (HELLO, FRIENDS.model_copy(update={"start_seconds": 2.0})),
    ],
)
def test_karaoke_skips_entries_whose_words_do_not_match(words: tuple[WordTiming, ...]) -> None:
    assert karaoke_events(ENTRY, words) == []


def test_words_spoken_at_the_same_moment_show_only_the_later_one() -> None:
    together = FRIENDS.model_copy(update={"start_seconds": 1.0})
    assert karaoke_events(ENTRY, (HELLO, together)) == [
        (1.0, 2.0, f"{HIDDEN}Hello\\N{SHOWN}friends{HIDDEN}")
    ]


def test_karaoke_text_cannot_carry_override_tags() -> None:
    entry = SrtEntry(start=0.0, end=1.0, lines=("{b}",))
    word = WordTiming(word="{b}", start_seconds=0.0, end_seconds=1.0)
    assert karaoke_events(entry, (word,)) == [(0.0, 1.0, f"{HIDDEN}{SHOWN}(b){HIDDEN}")]


def test_the_document_layers_karaoke_only_when_switched_on() -> None:
    words = (HELLO, FRIENDS)
    plain = ass_document([ENTRY], STYLE, (320, 180), 3.0, words)
    sung = ass_document([ENTRY], STYLE.model_copy(update={"karaoke": True}), (320, 180), 3.0, words)
    assert plain.count("Dialogue:") == 1 and "Spoken" not in plain
    assert "\nStyle: Spoken," in sung
    assert "Dialogue: 0,0:00:01.00,0:00:02.00,Default,,0,0,0,,Hello\\Nfriends" in sung
    assert f"Dialogue: 1,0:00:01.50,0:00:02.00,Spoken,,0,0,0,,{HIDDEN}Hello\\N{SHOWN}" in sung
    assert sung.count("Dialogue: 1,") == 2


def test_karaoke_words_travel_from_the_composition(tmp_path: Path) -> None:
    srt = tmp_path / "en.srt"
    srt.write_text("1\n00:00:01,000 --> 00:00:02,000\nHello\nfriends\n", encoding="utf-8")
    style = composition().subtitle_style.model_copy(update={"karaoke": True})
    sung = composition(subtitles=srt, subtitle_style=style, subtitle_words=(HELLO, FRIENDS))
    burned = with_ass_subtitles(sung, (320, 180), tmp_path / "v.mp4", 2.0)
    assert burned.subtitles is not None
    assert burned.subtitles.read_text(encoding="utf-8").count(SHOWN) == 2

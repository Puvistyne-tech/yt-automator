from __future__ import annotations

from pathlib import Path

import pytest

from automator.domain.capabilities import WordTiming
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.subtitles.cues import CueRules, segment_cues
from automator.pipelines.kids_story.subtitles.layout import SubtitleLayout, subtitle_layout
from automator.pipelines.kids_story.subtitles.subtitle_font import subtitle_font
from automator.pipelines.kids_story.subtitles.timeline_cues import cue_rules
from tests.fixtures.kids_data import quick_settings
from tests.fixtures.kids_fakes import embedded_font

NARRATION = {
    "en": "Kutty the little elephant lifted his long trunk high into the warm morning air and "
    "reached for the biggest, sweetest, most wonderfully golden mango on the whole tree.",
    "ta": "குட்டி தன் தும்பிக்கையை உயர்த்தி, மிகப் பெரிய, மிக இனிப்பான மாம்பழத்தைப் பறித்தான். "
    "மிட்டு கிளி மகிழ்ச்சியுடன் பாட்டுப் பாடியது, சின்னு அணில் கைதட்டிச் சிரித்தது.",
}
VARIANTS = ("episode", "short")


def timed(text: str) -> list[WordTiming]:
    return [
        WordTiming(word=word, start_seconds=index * 0.2, end_seconds=index * 0.2 + 0.15)
        for index, word in enumerate(text.split())
    ]


def settings_with(fonts: list[str]) -> KidsStorySettings:
    return quick_settings(subtitles={"font_files": {"en": fonts, "ta": fonts}})


def rules_for(settings: KidsStorySettings, language: str, variant: str) -> CueRules:
    return cue_rules(settings.subtitles, subtitle_layout(settings, language, variant))


@pytest.mark.parametrize("language", sorted(NARRATION))
@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("measured", [True, False])
def test_cues_stay_within_their_lines_and_the_usable_width(
    language: str, variant: str, measured: bool, tmp_path: Path
) -> None:
    settings = settings_with([str(embedded_font(tmp_path))] if measured else [])
    layout = subtitle_layout(settings, language, variant)
    rules = rules_for(settings, language, variant)
    cues = segment_cues(timed(NARRATION[language]), 0.0, 60.0, rules)
    assert (layout.font.file is not None) is measured
    assert " ".join(cue.text for cue in cues) == NARRATION[language]
    for cue in cues:
        assert 1 <= len(cue.lines) <= layout.max_lines
        assert all(layout.font.measure(line) <= layout.line_width for line in cue.lines)


def test_a_cue_with_more_lines_than_allowed_becomes_consecutive_cues() -> None:
    rules = CueRules(max_chars=6, max_lines=2, max_seconds=60, min_seconds=0)
    word = WordTiming(word="b" * 30, start_seconds=0.0, end_seconds=10.0)
    cues = segment_cues([word], 0.0, 20.0, rules)
    assert [len(cue.lines) for cue in cues] == [2, 2, 1]
    assert [(cue.start, cue.end) for cue in cues] == [(0.0, 4.0), (4.0, 8.0), (8.0, 10.0)]


def test_layout_reserves_the_side_margins() -> None:
    layout = subtitle_layout(quick_settings(), "ta", "short")
    assert isinstance(layout, SubtitleLayout)
    assert (layout.width, layout.side_margin, layout.line_width) == (720, 29, 662)


def test_estimated_widths_grow_with_letters_and_language() -> None:
    settings = settings_with([])
    english = subtitle_font(settings.subtitles, "en", 50)
    tamil = subtitle_font(settings.subtitles, "ta", 50)
    assert english.measure("abcd") == pytest.approx(4 * 50 * 0.6)
    assert tamil.measure("குட்டி") == pytest.approx(3 * 50 * 1.15)
    assert (english.family, tamil.family) == ("Noto Sans", "Noto Sans Tamil")


def test_an_unreadable_font_file_falls_back_to_the_estimate(tmp_path: Path) -> None:
    broken = tmp_path / "broken.ttf"
    broken.write_bytes(b"not a font")
    font = subtitle_font(settings_with([str(broken)]).subtitles, "en", 40)
    assert font.file is None and font.measure("ab") == pytest.approx(2 * 40 * 0.6)

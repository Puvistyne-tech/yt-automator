from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from autotube.domain.machine_local import portable_settings
from autotube.domain.video_look import SubtitlePosition, Transition, VideoQuality
from autotube.pipelines.narrated_video.plugin import KidsStoryPipeline
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.settings.video_look import EpisodeLookSettings
from tests.fixtures.look_rig import STORED_SETTINGS


def test_stored_settings_load_with_todays_look() -> None:
    settings = KidsStorySettings.model_validate(STORED_SETTINGS)
    subtitles, episode, short = settings.subtitles, settings.episode, settings.short
    assert (subtitles.karaoke, subtitles.position, subtitles.bold) == (
        False,
        SubtitlePosition.BOTTOM,
        False,
    )
    assert (subtitles.shadow, subtitles.box_background, subtitles.outline_override()) == (
        0.0,
        False,
        None,
    )
    assert (episode.transition, episode.overlap_seconds()) == (Transition.CUT, 0.0)
    assert (episode.intro_card_text.en, episode.outro_card_text.ta) == (
        "{series}\n{title}",
        "{refrain}\n{series}",
    )
    assert (short.fps, settings.video_fps("short"), settings.video_quality("short")) == (
        0,
        30,
        VideoQuality.STANDARD,
    )
    assert (settings.thumbnail.text_template.en, settings.thumbnail.candidates) == ("{title}", 1)
    assert settings.visuals.logo_file == ""


def test_the_short_can_run_at_its_own_rate_and_quality() -> None:
    settings = KidsStorySettings.model_validate(
        {"short": {"fps": 24, "video_quality": "high"}, "episode": {"video_quality": "draft"}}
    )
    assert (settings.video_fps("short"), settings.video_fps("episode")) == (24, 30)
    assert settings.video_quality("short") is VideoQuality.HIGH
    assert settings.video_quality("episode") is VideoQuality.DRAFT


def test_an_outline_of_zero_is_kept_rather_than_following_the_provider() -> None:
    settings = KidsStorySettings.model_validate({"subtitles": {"outline_width": 0}})
    assert settings.subtitles.outline_override() == 0.0


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("thumbnail", "text_template", {"en": "{title} {oops}"}),
        ("episode", "intro_card_text", {"ta": "{tagline} {theme}"}),
        ("episode", "outro_card_text", {"en": "{refrain}\n{nope}"}),
    ],
)
def test_unknown_placeholders_are_refused_naming_the_field(
    section: str, field: str, value: dict[str, str]
) -> None:
    with pytest.raises(ValidationError) as raised:
        KidsStorySettings.model_validate({section: {field: value}})
    error = raised.value.errors()[0]
    assert error["loc"] == (section, field)
    assert f"{section}.{field} has unknown placeholders" in error["msg"]


@pytest.mark.parametrize(
    "sections",
    [
        {"short": {"fps": 5}},
        {"visuals": {"logo_file": "/logos/brand.gif"}},
        {"subtitles": {"outline_width": -0.5}},
        {"episode": {"transition": "wipe"}},
    ],
)
def test_out_of_range_look_values_are_refused(sections: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        KidsStorySettings.model_validate(sections)


def test_the_logo_path_is_trimmed() -> None:
    settings = KidsStorySettings.model_validate({"visuals": {"logo_file": " /a/logo.PNG "}})
    assert settings.visuals.logo_file == "/a/logo.PNG"


def test_an_export_leaves_logo_and_font_paths_on_this_machine() -> None:
    descriptor = KidsStoryPipeline().descriptor
    fonts = {"en": ["/mine/a.ttf"], "ta": ["/mine/b.ttf"]}
    local = {
        "visuals": {"logo_file": "/mine/logo.png", "logo_opacity": 0.4},
        "subtitles": {"font_files": fonts},
        "thumbnail": {"font_files": fonts},
    }
    stored = KidsStorySettings.model_validate(local).model_dump(mode="json")
    exported: Any = portable_settings(stored, descriptor)
    defaults: Any = descriptor.default_settings
    assert exported["visuals"]["logo_file"] == defaults["visuals"]["logo_file"] == ""
    assert exported["visuals"]["logo_opacity"] == 0.4
    for section in ("subtitles", "thumbnail"):
        assert exported[section]["font_files"] == defaults[section]["font_files"] != fonts


@pytest.mark.parametrize("field", ["intro_card_text", "outro_card_text"])
def test_card_text_says_its_placeholders_depend_on_the_format(field: str) -> None:
    description = EpisodeLookSettings.model_fields[field].description or ""
    assert "depend on the format" in description
    assert "{moral} and {refrain}" in description

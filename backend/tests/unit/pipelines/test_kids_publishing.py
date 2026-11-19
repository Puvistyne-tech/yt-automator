from __future__ import annotations

import pytest

from autotube.domain.upload_details import DESCRIPTION_MAX_BYTES, utf8_length
from autotube.pipelines.narrated_video.publishing.limits import (
    TAGS_MAX,
    TITLE_MAX,
    cleaned,
    tags_length,
    tags_within,
    truncated,
    truncated_bytes,
)
from autotube.pipelines.narrated_video.publishing.metadata import upload_metadata
from autotube.pipelines.narrated_video.publishing.templates import template_values
from autotube.pipelines.narrated_video.text.graphemes import grapheme_clusters
from autotube.pipelines.narrated_video.text.templates import render_template
from tests.fixtures.kids_data import quick_settings, story

TAMIL_WORD = "கொண்டாட்டம்"


def test_render_template_fills_known_and_keeps_unknown_placeholders() -> None:
    assert render_template("{title} - {nope} {", {"title": "Hi"}) == "Hi - {nope} {"


def test_template_values_are_localised() -> None:
    values = template_values(story("ta"), quick_settings())
    assert values["series"] == "கதை நேரம்"
    assert values["questions"].startswith("• ")
    assert "#MoralStories" in values["hashtags"]
    assert values["characters"].startswith("கவின்")


@pytest.mark.parametrize(("length", "kept"), [(99, True), (100, True), (101, False)])
def test_truncated_keeps_text_up_to_the_limit(length: int, kept: bool) -> None:
    text = "a " * (length // 2) + "a" * (length % 2)
    result = truncated(text, TITLE_MAX)
    assert (result == text) is kept
    assert len(result) <= TITLE_MAX and (kept or result.endswith("…"))


def test_a_limit_too_small_for_any_letter_leaves_only_the_ellipsis() -> None:
    assert truncated("abc", 1) == "…"


def test_truncated_prefers_a_word_boundary_and_cuts_long_words() -> None:
    assert truncated("hello wonderful world", 18) == "hello wonderful…"
    assert truncated("x" * 150, TITLE_MAX) == "x" * 99 + "…"


def test_truncation_never_splits_a_tamil_letter() -> None:
    text = TAMIL_WORD * 20
    for limit in range(5, 40):
        cut = truncated(text, limit)
        assert len(cut) <= limit
        assert set(grapheme_clusters(cut[:-1])) <= set(grapheme_clusters(TAMIL_WORD))


def test_descriptions_are_limited_in_utf8_bytes() -> None:
    tamil = (TAMIL_WORD + " ") * 200
    assert len(tamil) <= 5000 < utf8_length(tamil)
    cut = truncated_bytes(tamil, DESCRIPTION_MAX_BYTES)
    assert utf8_length(cut) <= DESCRIPTION_MAX_BYTES and cut.endswith(TAMIL_WORD + "…")
    exact = "a" * DESCRIPTION_MAX_BYTES
    assert truncated_bytes(exact, DESCRIPTION_MAX_BYTES) == exact
    over = truncated_bytes(exact + "a", DESCRIPTION_MAX_BYTES)
    assert utf8_length(over) <= DESCRIPTION_MAX_BYTES and over.endswith("…")


def test_tags_are_cleaned_deduplicated_and_skipped_when_too_long() -> None:
    assert cleaned(" <b>Hi</b> ") == "bHi/b"
    assert tags_length(["a b", "c"]) == 7
    assert tags_within(["a", "A", "b,c", "", "  ", "<>"]) == ["a", "b c"]
    assert tags_within(["short", "x" * 20, "tiny"], limit=12) == ["short", "tiny"]
    many = tags_within([f"tag number {index}" for index in range(100)])
    assert tags_length(many) <= TAGS_MAX


def test_upload_metadata_uses_templates_per_variant() -> None:
    settings = quick_settings(
        metadata={
            "title_template": {"en": "{series}: {title}", "ta": "{title}"},
            "description_template": {"en": "Moral: {moral}\n{questions}", "ta": "{moral}"},
            "category": "27",
        }
    )
    episode = upload_metadata(story(), settings, "episode")
    assert episode.title == "Story Time: Kavin and the Golden Mango"
    assert episode.description.startswith("Moral: Sharing makes everyone happier.")
    assert episode.category_id == "27"
    assert episode.default_language == "en" and episode.playlist_title == "Story Time"
    short = upload_metadata(story(), settings, "short")
    assert short.title == "Kavin and the Golden Mango #Shorts"


@pytest.mark.parametrize(
    ("language", "playlist", "expected"),
    [
        ("en", {}, "Story Time"),
        ("ta", {}, "இரவுக் கதைகள்"),
        ("en", {"en": "", "ta": ""}, ""),
        ("en", {"en": "Bedtime picks", "ta": ""}, "Bedtime picks"),
        ("ta", {"en": "", "ta": "{series} - {nope}"}, "இரவுக் கதைகள் - {nope}"),
    ],
)
def test_playlist_title_fills_in_the_series_name(
    language: str, playlist: dict[str, str], expected: str
) -> None:
    metadata = {"playlist_title": playlist} if playlist else {}
    settings = quick_settings(
        series={"name": {"en": "Story Time", "ta": "இரவுக் கதைகள்"}}, metadata=metadata
    )
    assert upload_metadata(story(language), settings, "episode").playlist_title == expected


@pytest.mark.parametrize("language", ["en", "ta"])
@pytest.mark.parametrize("variant", ["episode", "short"])
def test_upload_metadata_respects_youtube_limits(language: str, variant: str) -> None:
    long_tags = ["kids stories"] + [f"tag {n}" for n in range(200)]
    settings = quick_settings(
        metadata={
            "title_template": {"en": "{title} " * 20, "ta": "{title} " * 20},
            "short_title_template": {"en": "{title} " * 20, "ta": "{title} " * 20},
            "description_template": {"en": "{moral} " * 400, "ta": "{moral} " * 400},
            "tags": {"en": long_tags, "ta": long_tags},
        }
    )
    made = upload_metadata(story(language), settings, variant)
    assert len(made.title) <= TITLE_MAX and made.title.endswith("…")
    assert utf8_length(made.description) <= DESCRIPTION_MAX_BYTES
    assert made.description.endswith("…")
    assert tags_length(made.tags) <= TAGS_MAX
    assert made.made_for_kids is True

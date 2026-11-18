from __future__ import annotations

import pytest
from pydantic import JsonValue

from automator.domain.artifact_selection import VideoMetadata, language_code, video_metadata
from automator.domain.channels import ChannelDefaults
from automator.domain.run_enums import ArtifactKind
from automator.domain.run_parts import Artifact
from automator.domain.upload_details import (
    DESCRIPTION_MAX_BYTES,
    HASHTAGS_MAX,
    upload_details,
    utf8_length,
    with_hashtags,
)

DEFAULTS = ChannelDefaults(category_id="22", default_language="en")
TAMIL_TAG = "#கதை"


def metadata_artifact(**meta: JsonValue) -> Artifact:
    return Artifact(
        id="m",
        kind=ArtifactKind.METADATA,
        stage_id="package",
        language="ta",
        variant="episode",
        filename="m.json",
        media_type="application/json",
        size_bytes=1,
        meta={"title": "Kavin", **meta},
    )


def test_video_metadata_reads_category_language_hashtags_and_playlist() -> None:
    found = metadata_artifact(
        category_id="27",
        default_language="ta",
        hashtags=["#Kavin", "#Tamil"],
        playlist_title="Bedtime tales",
    )
    read = video_metadata([found], "ta", "episode", "fallback")
    assert (read.category_id, read.default_language) == ("27", "ta")
    assert read.hashtags == ("#Kavin", "#Tamil") and read.playlist_title == "Bedtime tales"
    bare = video_metadata([metadata_artifact(category_id=5)], "ta", "episode", "fallback")
    assert bare.category_id is None and bare.default_language is None and bare.hashtags == ()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("ta", "ta"),
        ("en-GB", "en-GB"),
        ("yue-Hant-HK", "yue-Hant-HK"),
        ("English", None),
        ("e", None),
        ("en_GB", None),
        ("ta ", None),
        (7, None),
        (None, None),
    ],
)
def test_only_language_codes_are_kept(value: JsonValue, expected: str | None) -> None:
    assert language_code(value) == expected


def test_an_invalid_metadata_language_falls_back_to_the_target_language() -> None:
    read = video_metadata([metadata_artifact(default_language="Tamil")], "ta", "episode", "f")
    assert upload_details(read, DEFAULTS, "ta").default_language == "ta"


def test_metadata_wins_over_channel_defaults_and_the_target_language() -> None:
    metadata = VideoMetadata(title="t", category_id="27", default_language="ta")
    details = upload_details(metadata, DEFAULTS, "en")
    assert (details.category_id, details.default_language) == ("27", "ta")
    plain = upload_details(VideoMetadata(title="t"), DEFAULTS, "ta")
    assert (plain.category_id, plain.default_language) == ("22", "ta")


def exactly(size: int, tag: str) -> str:
    return "a" * (size - utf8_length(tag) - 2)


@pytest.mark.parametrize(
    ("description", "hashtags", "expected"),
    [
        ("A story", ("#Kids", "#Tamil"), "A story\n\n#Kids #Tamil"),
        ("A story", (), "A story"),
        ("", ("#Kids",), "#Kids"),
        ("A story #kids", ("#Kids", "#Tamil"), "A story #kids\n\n#Tamil"),
        ("A story #Kidsworld", ("#Kids",), "A story #Kidsworld\n\n#Kids"),
        ("A story", ("#Kids", "#Kids"), "A story\n\n#Kids"),
        ("A story", ("#Kids", "#kids"), "A story\n\n#Kids"),
        ("A story", ("Kids", "#two words", "#", " #Kids "), "A story\n\n#Kids"),
        ("x#Kids", ("#Kids",), "x#Kids\n\n#Kids"),
        (exactly(DESCRIPTION_MAX_BYTES, "#Kids"), ("#Kids",), None),
        (exactly(DESCRIPTION_MAX_BYTES + 1, "#Kids"), ("#Kids",), "unchanged"),
        (exactly(DESCRIPTION_MAX_BYTES, TAMIL_TAG), (TAMIL_TAG,), None),
        (exactly(DESCRIPTION_MAX_BYTES + 1, TAMIL_TAG), (TAMIL_TAG,), "unchanged"),
        ("a" * (DESCRIPTION_MAX_BYTES + 1), ("#Kids",), "unchanged"),
    ],
)
def test_hashtags_are_appended_once_and_within_the_byte_limit(
    description: str, hashtags: tuple[str, ...], expected: str | None
) -> None:
    result = with_hashtags(description, hashtags)
    if expected is None:
        assert result == f"{description}\n\n{hashtags[0]}"
        assert utf8_length(result) == DESCRIPTION_MAX_BYTES
    elif expected == "unchanged":
        assert result == description
    else:
        assert result == expected


def test_hashtags_stop_at_sixty_in_total() -> None:
    existing = " ".join(f"#t{index}" for index in range(HASHTAGS_MAX - 1))
    result = with_hashtags(existing, ("#one", "#two"))
    assert result == f"{existing}\n\n#one"
    assert with_hashtags(f"{existing} #last", ("#more",)) == f"{existing} #last"

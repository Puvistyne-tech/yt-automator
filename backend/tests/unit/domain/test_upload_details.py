from __future__ import annotations

from automator.domain.artifact_selection import VideoMetadata, video_metadata
from automator.domain.channels import ChannelDefaults
from automator.domain.run_enums import ArtifactKind
from automator.domain.run_parts import Artifact
from automator.domain.upload_details import (
    DESCRIPTION_MAX_BYTES,
    upload_details,
    with_hashtags,
)

DEFAULTS = ChannelDefaults(category_id="22", default_language="en")


def metadata_artifact(**meta: object) -> Artifact:
    return Artifact(
        id="m",
        kind=ArtifactKind.METADATA,
        stage_id="package",
        language="ta",
        variant="episode",
        filename="m.json",
        media_type="application/json",
        size_bytes=1,
        meta={"title": "Kutty", **meta},
    )


def test_video_metadata_reads_category_language_hashtags_and_playlist() -> None:
    found = metadata_artifact(
        category_id="27",
        default_language="ta",
        hashtags=["#Kutty", "#Tamil"],
        playlist_title="Kutty Stories",
    )
    read = video_metadata([found], "ta", "episode", "fallback")
    assert (read.category_id, read.default_language) == ("27", "ta")
    assert read.hashtags == ("#Kutty", "#Tamil") and read.playlist_title == "Kutty Stories"
    bare = video_metadata([metadata_artifact(category_id=5)], "ta", "episode", "fallback")
    assert bare.category_id is None and bare.default_language is None and bare.hashtags == ()


def test_metadata_wins_over_channel_defaults_and_the_target_language() -> None:
    metadata = VideoMetadata(title="t", category_id="27", default_language="ta")
    details = upload_details(metadata, DEFAULTS, "en")
    assert (details.category_id, details.default_language) == ("27", "ta")
    plain = upload_details(VideoMetadata(title="t"), DEFAULTS, "ta")
    assert (plain.category_id, plain.default_language) == ("22", "ta")


def test_hashtags_are_appended_once_and_within_the_byte_limit() -> None:
    assert with_hashtags("A story", ("#Kids", "#Tamil")) == "A story\n\n#Kids #Tamil"
    assert with_hashtags("A story #kids", ("#Kids", "#Tamil")) == "A story #kids\n\n#Tamil"
    assert with_hashtags("A story", ()) == "A story"
    assert with_hashtags("", ("#Kids",)) == "#Kids"
    full = "க" * (DESCRIPTION_MAX_BYTES // 3 - 1)
    assert with_hashtags(full, ("#Kids",)) == full
    near = "a" * (DESCRIPTION_MAX_BYTES - 9)
    assert with_hashtags(near, ("#Kids", "#Tamil")) == near + "\n\n#Kids"

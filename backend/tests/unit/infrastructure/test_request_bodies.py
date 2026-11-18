from __future__ import annotations

from pathlib import Path

from automator.domain.artifact_selection import VideoMetadata
from automator.domain.channels import ChannelDefaults, Privacy
from automator.domain.upload_details import upload_details
from automator.domain.youtube import VideoUpload
from automator.infrastructure.youtube.request_bodies import video_body


def test_kids_metadata_reaches_the_video_body() -> None:
    metadata = VideoMetadata(
        title="குட்டி",
        description="ஒரு கதை",
        tags=("kids",),
        category_id="27",
        default_language="ta",
        hashtags=("#KuttyStories", "#TamilKids"),
        playlist_title="Kutty Stories",
    )
    details = upload_details(metadata, ChannelDefaults(category_id="22"), "en")
    video = VideoUpload(
        path=Path("v.mp4"),
        title=metadata.title,
        description=details.description,
        tags=metadata.tags,
        category_id=details.category_id,
        default_language=details.default_language,
        privacy=Privacy.PRIVATE,
        made_for_kids=True,
        notify_subscribers=False,
    )
    snippet = video_body(video)["snippet"]
    assert snippet["categoryId"] == "27"
    assert snippet["defaultLanguage"] == snippet["defaultAudioLanguage"] == "ta"
    assert snippet["description"] == "ஒரு கதை\n\n#KuttyStories #TamilKids"
    assert "playlist" not in str(snippet).casefold()
    assert video_body(video)["status"]["selfDeclaredMadeForKids"] is True

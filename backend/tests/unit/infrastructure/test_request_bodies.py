from __future__ import annotations

from pathlib import Path

from automator.domain.channels import Privacy
from automator.domain.youtube import VideoUpload
from automator.infrastructure.youtube.request_bodies import video_body


def test_the_video_language_is_both_the_metadata_and_the_audio_language() -> None:
    video = VideoUpload(
        path=Path("v.mp4"),
        title="குட்டி",
        description="ஒரு கதை\n\n#KuttyStories",
        category_id="27",
        default_language="ta",
        privacy=Privacy.PRIVATE,
        made_for_kids=True,
        notify_subscribers=False,
    )
    snippet = video_body(video)["snippet"]
    assert (snippet["categoryId"], snippet["description"]) == ("27", "ஒரு கதை\n\n#KuttyStories")
    assert snippet["defaultLanguage"] == snippet["defaultAudioLanguage"] == "ta"

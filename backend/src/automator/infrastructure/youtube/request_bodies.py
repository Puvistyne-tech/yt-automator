from __future__ import annotations

from typing import Any

from automator.domain.channels import Privacy
from automator.domain.youtube import ChannelProfile, VideoUpload
from automator.shared.clock import to_utc
from automator.shared.errors import UpstreamFailure

THUMBNAIL_SIZES = ("high", "medium", "default")


def video_status(video: VideoUpload) -> dict[str, Any]:
    status: dict[str, Any] = {
        "privacyStatus": video.privacy.value,
        "selfDeclaredMadeForKids": video.made_for_kids,
    }
    if video.publish_at is not None:
        status["privacyStatus"] = Privacy.PRIVATE.value
        status["publishAt"] = to_utc(video.publish_at).strftime("%Y-%m-%dT%H:%M:%SZ")
    return status


def video_body(video: VideoUpload) -> dict[str, Any]:
    return {
        "snippet": {
            "title": video.title,
            "description": video.description,
            "tags": list(video.tags),
            "categoryId": video.category_id,
            "defaultLanguage": video.default_language,
            "defaultAudioLanguage": video.default_language,
        },
        "status": video_status(video),
    }


def caption_body(video_id: str, language: str, name: str) -> dict[str, Any]:
    return {"snippet": {"videoId": video_id, "language": language, "name": name, "isDraft": False}}


def playlist_item_body(video_id: str, playlist_id: str) -> dict[str, Any]:
    return {
        "snippet": {
            "playlistId": playlist_id,
            "resourceId": {"kind": "youtube#video", "videoId": video_id},
        }
    }


def thumbnail_url(snippet: dict[str, Any]) -> str:
    thumbnails = snippet.get("thumbnails", {})
    for size in THUMBNAIL_SIZES:
        if size in thumbnails:
            return str(thumbnails[size].get("url", ""))
    return ""


def channel_profile(response: dict[str, Any]) -> ChannelProfile:
    items = response.get("items", [])
    if not items:
        raise UpstreamFailure("the Google account has no YouTube channel", "youtube_no_channel")
    item = items[0]
    snippet = item.get("snippet", {})
    return ChannelProfile(
        youtube_channel_id=str(item["id"]),
        title=str(snippet.get("title", "")),
        thumbnail_url=thumbnail_url(snippet),
    )

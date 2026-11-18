from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from autotube.infrastructure.config import RuntimeConfig

UPLOAD_SCOPE = "https://www.googleapis.com/auth/youtube.upload"
READONLY_SCOPE = "https://www.googleapis.com/auth/youtube.readonly"
FORCE_SSL_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"


def default_redirect_uri() -> str:
    return RuntimeConfig().oauth_redirect_uri


class YouTubeSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    redirect_uri: str = Field(
        default_factory=default_redirect_uri, description="OAuth redirect URI"
    )
    scopes: tuple[str, ...] = Field(
        default=(UPLOAD_SCOPE, READONLY_SCOPE, FORCE_SSL_SCOPE), description="OAuth scopes"
    )
    auth_uri: str = Field(default="https://accounts.google.com/o/oauth2/auth")
    token_uri: str = Field(default="https://oauth2.googleapis.com/token")
    upload_chunk_bytes: int = Field(default=8 * 1024 * 1024, ge=256 * 1024)
    playlist_page_size: int = Field(default=50, ge=1, le=50)
    caption_track_name: str = Field(default="", description="Name shown for uploaded captions")
    watch_url_prefix: str = Field(default="https://youtu.be/")


def youtube_settings(config: RuntimeConfig) -> YouTubeSettings:
    return YouTubeSettings(
        redirect_uri=config.oauth_redirect_uri,
        upload_chunk_bytes=config.upload_chunk_bytes,
        caption_track_name=config.youtube_caption_track_name,
        playlist_page_size=config.youtube_playlist_page_size,
    )

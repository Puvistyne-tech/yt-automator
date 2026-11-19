from __future__ import annotations

from autotube.domain.ports import AppSettingsRepository
from autotube.infrastructure.config import RuntimeConfig
from autotube.infrastructure.youtube.gateway import GoogleYouTubeGateway
from autotube.infrastructure.youtube.settings import youtube_settings


def youtube_gateway(
    config: RuntimeConfig, settings: AppSettingsRepository | None = None
) -> GoogleYouTubeGateway:
    name = (lambda: settings.get().caption_track_name) if settings is not None else None
    return GoogleYouTubeGateway(youtube_settings(config), caption_name=name)

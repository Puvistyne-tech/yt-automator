from __future__ import annotations

import shutil

from autotube.infrastructure.providers.ffmpeg_filters import ffmpeg_filter_names

LISTING_TIMEOUT_SECONDS = 30.0


def ffmpeg_has(*filters: str) -> bool:
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        return False
    names = ffmpeg_filter_names("ffmpeg", LISTING_TIMEOUT_SECONDS)
    return all(name in names for name in filters)

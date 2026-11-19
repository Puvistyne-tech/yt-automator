from __future__ import annotations

from pathlib import PurePosixPath

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings

GENERAL_SUFFIX = "_general"


def audience_prompt(name: str, settings: KidsStorySettings) -> str:
    if settings.safety.for_kids:
        return name
    path = PurePosixPath(name)
    return f"{path.stem}{GENERAL_SUFFIX}{path.suffix}"

from __future__ import annotations

from typing import Any

from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from tests.fixtures.kids_data import quick_settings

MAC_STORY: dict[str, Any] = {
    "target_duration_seconds": 60,
    "duration_tolerance_seconds": 20,
    "scene_count_min": 4,
    "scene_count_max": 6,
}


def mac_settings(**story: Any) -> KidsStorySettings:
    return quick_settings(story={**MAC_STORY, **story})

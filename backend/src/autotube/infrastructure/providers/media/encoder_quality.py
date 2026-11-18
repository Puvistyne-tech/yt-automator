from __future__ import annotations

from autotube.domain.video_look import VideoQuality

CRF_SHIFT = {
    VideoQuality.DRAFT: 8,
    VideoQuality.STANDARD: 0,
    VideoQuality.HIGH: -4,
    VideoQuality.BEST: -8,
}
LOWEST_CRF = 0
HIGHEST_CRF = 51


def quality_crf(configured: int, quality: VideoQuality) -> int:
    return min(HIGHEST_CRF, max(LOWEST_CRF, configured + CRF_SHIFT[quality]))

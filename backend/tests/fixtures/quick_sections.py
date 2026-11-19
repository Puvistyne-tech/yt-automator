from __future__ import annotations

from typing import Any

NO_FONTS: dict[str, list[str]] = {"en": [], "ta": []}
QUICK_SECTIONS: dict[str, Any] = {
    "episode": {"resolution": "1280x720"},
    "short": {"resolution": "720x1280"},
    "thumbnail": {"width": 640, "height": 360, "font_files": NO_FONTS},
    "subtitles": {"font_files": NO_FONTS},
    "visuals": {"image_candidates": 1, "hero_candidates": 2, "sheet_size": 256},
}

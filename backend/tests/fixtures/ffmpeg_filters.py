from __future__ import annotations

import shutil
import subprocess


def ffmpeg_has(*filters: str) -> bool:
    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        return False
    listed = subprocess.run(
        ["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True, check=False
    ).stdout
    names = {line.split()[1] for line in listed.splitlines() if len(line.split()) > 2}
    return all(name in names for name in filters)

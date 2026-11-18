from __future__ import annotations

import os
import platform
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from automator.domain.diagnostics import SystemFacts
from automator.infrastructure.config import RuntimeConfig
from automator.infrastructure.db.migration_state import migration_state
from automator.infrastructure.providers.media.ffmpeg_options import FfmpegOptions

VersionReader = Callable[[str, float], str]
COPYRIGHT_MARKER = " Copyright"


def tool_version(binary: str, timeout_seconds: float) -> str:
    try:
        completed = subprocess.run(
            [binary, "-version"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    lines = completed.stdout.strip().splitlines()
    if completed.returncode != 0 or not lines:
        return ""
    return lines[0].split(COPYRIGHT_MARKER)[0].strip()


def nearest_existing(path: Path) -> Path:
    return next(candidate for candidate in (path, *path.parents) if candidate.exists())


def writable_dir(path: Path) -> bool:
    existing = nearest_existing(path)
    return existing.is_dir() and os.access(existing, os.W_OK | os.X_OK)


def free_space(path: Path) -> int | None:
    try:
        return shutil.disk_usage(nearest_existing(path)).free
    except OSError:
        return None


@dataclass(frozen=True)
class InspectorSettings:
    data_dir: Path
    database_path: Path
    web_dist_dir: Path
    ffmpeg_binary: str
    ffprobe_binary: str
    tool_timeout_seconds: float


class LocalSystemInspector:
    def __init__(
        self,
        settings: InspectorSettings,
        read_version: VersionReader = tool_version,
        python_version: str = platform.python_version(),
    ) -> None:
        self.settings = settings
        self.read_version = read_version
        self.python_version = python_version

    def version_of(self, binary: str) -> str:
        return self.read_version(binary, self.settings.tool_timeout_seconds)

    def facts(self) -> SystemFacts:
        settings = self.settings
        database = migration_state(settings.database_path)
        return SystemFacts(
            python_version=self.python_version,
            data_dir=str(settings.data_dir),
            data_dir_writable=writable_dir(settings.data_dir),
            free_bytes=free_space(settings.data_dir),
            ffmpeg_version=self.version_of(settings.ffmpeg_binary),
            ffprobe_version=self.version_of(settings.ffprobe_binary),
            database_path=str(settings.database_path),
            database_revision=database.revision,
            database_head=database.head,
            database_revision_known=database.known,
            database_error=database.error,
            web_dist_dir=str(settings.web_dist_dir),
            ui_built=(settings.web_dist_dir / "index.html").is_file(),
        )


def build_system_inspector(config: RuntimeConfig) -> LocalSystemInspector:
    media = FfmpegOptions()
    settings = InspectorSettings(
        data_dir=config.data_dir,
        database_path=config.database_path,
        web_dist_dir=config.web_dist_dir,
        ffmpeg_binary=media.ffmpeg_binary,
        ffprobe_binary=media.ffprobe_binary,
        tool_timeout_seconds=config.doctor_tool_timeout_seconds,
    )
    return LocalSystemInspector(settings)

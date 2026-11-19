from __future__ import annotations

import importlib.util
import os.path
import platform
import shutil
from collections.abc import Callable
from dataclasses import dataclass

from autotube.infrastructure.providers.ffmpeg_filters import ffmpeg_filter_names


def module_installed(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


@dataclass(frozen=True)
class HostProbe:
    which: Callable[[str], str | None] = shutil.which
    has_module: Callable[[str], bool] = module_installed
    has_path: Callable[[str], bool] = os.path.exists
    system: str = platform.system()
    machine: str = platform.machine()
    ffmpeg_filters: Callable[[str, float], frozenset[str]] = ffmpeg_filter_names

    def missing_binary(self, name: str) -> str | None:
        return None if self.which(name) else f"{name} is not installed or not on PATH"

    def missing_path(self, path: str, title: str) -> str | None:
        return None if self.has_path(path) else f"{title} not found at {path}"

    def missing_module(self, module: str, extra: str) -> str | None:
        if self.has_module(module):
            return None
        return f"Python package {module!r} is not installed (uv sync --extra {extra})"

    def missing_ffmpeg_filter(self, binary: str, name: str, timeout_seconds: float) -> str | None:
        if name in self.ffmpeg_filters(binary, timeout_seconds):
            return None
        return f"{binary} has no {name!r} filter"

    def not_apple_silicon(self) -> str | None:
        if self.system == "Darwin" and self.machine == "arm64":
            return None
        return f"needs an Apple-silicon Mac, this host is {self.system} {self.machine}"


def first_reason(*reasons: str | None) -> str | None:
    return next((reason for reason in reasons if reason), None)

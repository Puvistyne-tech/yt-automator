from __future__ import annotations

import importlib.util
import platform
import shutil
from collections.abc import Callable
from dataclasses import dataclass


def module_installed(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


@dataclass(frozen=True)
class HostProbe:
    which: Callable[[str], str | None] = shutil.which
    has_module: Callable[[str], bool] = module_installed
    system: str = platform.system()
    machine: str = platform.machine()

    def missing_binary(self, name: str) -> str | None:
        return None if self.which(name) else f"{name} is not installed or not on PATH"

    def missing_module(self, module: str, extra: str) -> str | None:
        if self.has_module(module):
            return None
        return f"Python package {module!r} is not installed (uv sync --extra {extra})"

    def not_apple_silicon(self) -> str | None:
        if self.system == "Darwin" and self.machine == "arm64":
            return None
        return f"needs an Apple-silicon Mac, this host is {self.system} {self.machine}"


def first_reason(*reasons: str | None) -> str | None:
    return next((reason for reason in reasons if reason), None)

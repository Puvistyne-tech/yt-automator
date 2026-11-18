from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from autotube.shared.errors import UpstreamFailure


@dataclass(frozen=True)
class ProcessResult:
    stdout: str
    stderr: str


class ProcessRunner(Protocol):
    def run(
        self,
        command: Sequence[str],
        timeout_seconds: float,
        stdin: str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> ProcessResult: ...


def tail(text: str, limit: int) -> str:
    return text.strip()[-limit:]


class SubprocessRunner:
    def __init__(self, stderr_tail_chars: int = 1500) -> None:
        self.stderr_tail_chars = stderr_tail_chars

    def run(
        self,
        command: Sequence[str],
        timeout_seconds: float,
        stdin: str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> ProcessResult:
        program = Path(command[0]).name
        try:
            completed = subprocess.run(
                list(command),
                input=stdin,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=timeout_seconds,
                env={**os.environ, **env} if env else None,
                check=False,
            )
        except FileNotFoundError as error:
            raise UpstreamFailure(f"{program} is not installed", "tool_missing") from error
        except subprocess.TimeoutExpired as error:
            message = f"{program} timed out after {timeout_seconds:g}s"
            raise UpstreamFailure(message, "tool_timeout") from error
        if completed.returncode != 0:
            stderr = tail(completed.stderr, self.stderr_tail_chars)
            message = f"{program} exited with {completed.returncode}: {stderr}"
            raise UpstreamFailure(message, "tool_failed")
        return ProcessResult(stdout=completed.stdout, stderr=completed.stderr)

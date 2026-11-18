from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from automator.domain.port_runtime import SecretStore
from automator.infrastructure.providers.host import HostProbe
from automator.infrastructure.providers.process import ProcessRunner, SubprocessRunner

HttpClientFactory = Callable[[float], httpx.Client]


def default_http_client(timeout_seconds: float) -> httpx.Client:
    return httpx.Client(timeout=timeout_seconds)


@dataclass(frozen=True)
class ProviderContext:
    secrets: SecretStore
    data_dir: Path
    host: HostProbe = field(default_factory=HostProbe)
    runner: ProcessRunner = field(default_factory=SubprocessRunner)
    http: HttpClientFactory = default_http_client
    sleep: Callable[[float], None] = time.sleep

    def missing_secret(self, name: str, title: str) -> str | None:
        return None if self.secrets.has(name) else f"set the {title} secret ({name})"

    def secret(self, name: str) -> str:
        return self.secrets.get(name) or ""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import numpy as np

from automator.infrastructure.providers.context import ProviderContext
from automator.infrastructure.providers.host import HostProbe
from automator.infrastructure.providers.process import ProcessResult
from automator.infrastructure.providers.wav_io import write_wav
from automator.shared.errors import UpstreamFailure
from tests.fixtures.fake_runtime import InMemorySecrets


@dataclass
class Call:
    command: list[str]
    timeout_seconds: float
    stdin: str | None
    env: dict[str, str] | None


@dataclass
class RecordingRunner:
    results: list[ProcessResult] = field(default_factory=list)
    effect: Callable[[list[str]], None] | None = None
    fail_with: str = ""
    calls: list[Call] = field(default_factory=list)

    def run(
        self,
        command: Sequence[str],
        timeout_seconds: float,
        stdin: str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> ProcessResult:
        self.calls.append(Call(list(command), timeout_seconds, stdin, dict(env) if env else None))
        if self.fail_with:
            raise UpstreamFailure(self.fail_with)
        if self.effect is not None:
            self.effect(list(command))
        return self.results.pop(0) if self.results else ProcessResult(stdout="", stderr="")

    @property
    def commands(self) -> list[list[str]]:
        return [call.command for call in self.calls]


def host(
    binaries: frozenset[str] = frozenset(),
    modules: frozenset[str] = frozenset(),
    system: str = "Linux",
    machine: str = "x86_64",
) -> HostProbe:
    return HostProbe(
        which=lambda name: f"/usr/bin/{name}" if name in binaries else None,
        has_module=lambda name: name in modules,
        system=system,
        machine=machine,
    )


def unreachable(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("no network in tests", request=request)


def make_context(
    tmp_path: Path,
    runner: RecordingRunner | None = None,
    probe: HostProbe | None = None,
    handler: Callable[[httpx.Request], httpx.Response] = unreachable,
    secrets: Mapping[str, str] | None = None,
    sleeps: list[float] | None = None,
) -> ProviderContext:
    store = InMemorySecrets()
    for name, value in (secrets or {}).items():
        store.set(name, value)
    recorded: list[float] = [] if sleeps is None else sleeps
    return ProviderContext(
        secrets=store,
        data_dir=tmp_path,
        host=probe or host(),
        runner=runner or RecordingRunner(),
        http=lambda timeout: httpx.Client(transport=httpx.MockTransport(handler), timeout=timeout),
        sleep=recorded.append,
    )


def write_tone(path: Path, seconds: float, rate: int = 16000) -> None:
    clock = np.arange(round(seconds * rate)) / rate
    write_wav(path, 0.2 * np.sin(2 * np.pi * 220 * clock), rate)


def writes_last_argument_as_wav(seconds: float) -> Callable[[list[str]], None]:
    def effect(command: list[str]) -> None:
        write_tone(Path(command[-1]), seconds)

    return effect


def writes_wav_after(flag: str, seconds: float) -> Callable[[list[str]], None]:
    def effect(command: list[str]) -> None:
        write_tone(Path(command[command.index(flag) + 1]), seconds)

    return effect

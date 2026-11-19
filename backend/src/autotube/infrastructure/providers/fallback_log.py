from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from autotube.domain.port_runtime import SecretStore
from autotube.domain.provider_fallbacks import ProviderFallback, without_secrets

FallbackRecorder = Callable[[ProviderFallback], None]


def ignore_fallback(_: ProviderFallback) -> None:
    return None


@dataclass
class FallbackLog:
    secrets: SecretStore
    secret_names: Sequence[str]
    entries: list[ProviderFallback] = field(default_factory=list)

    def record(self, fallback: ProviderFallback) -> None:
        reason = without_secrets(fallback.reason, self.secret_values())
        self.entries.append(fallback.model_copy(update={"reason": reason}))

    def secret_values(self) -> list[str]:
        return [self.secrets.get(name) or "" for name in self.secret_names]

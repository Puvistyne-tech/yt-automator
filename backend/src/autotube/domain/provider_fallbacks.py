from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence

from autotube.domain.capabilities import Capability
from autotube.domain.model_base import DomainModel

SECRET_MASK = "[secret]"
NO_REASON = "no reason given"
ELLIPSIS = "…"


class ProviderFallback(DomainModel):
    capability: Capability
    failed: str
    used: str
    reason: str


def without_secrets(text: str, secrets: Iterable[str]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, SECRET_MASK)
    return text


def short_reason(reason: str, limit: int) -> str:
    line = next((line.strip() for line in reason.splitlines() if line.strip()), NO_REASON)
    return line if len(line) <= limit else line[: limit - 1] + ELLIPSIS


def fallback_warning(fallback: ProviderFallback, calls: int, reason_chars: int) -> str:
    reason = short_reason(fallback.reason, reason_chars)
    repeated = f" for {calls} calls" if calls > 1 else ""
    return (
        f"{fallback.capability.value} provider {fallback.failed} failed ({reason}); "
        f"used {fallback.used} instead{repeated}"
    )


def fallback_warnings(fallbacks: Sequence[ProviderFallback], reason_chars: int) -> list[str]:
    calls = Counter((f.capability, f.failed, f.used) for f in fallbacks)
    first = {(f.capability, f.failed, f.used): f for f in reversed(fallbacks)}
    return [fallback_warning(first[key], count, reason_chars) for key, count in calls.items()]


def stand_in_sources(
    fallbacks: Sequence[ProviderFallback], capability: Capability, provider_id: str
) -> list[str]:
    return sorted(
        {f.failed for f in fallbacks if f.capability is capability and f.used == provider_id}
    )

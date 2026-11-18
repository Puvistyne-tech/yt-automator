from __future__ import annotations

from collections.abc import Iterable, Sequence

from autotube.domain.capabilities import Capability
from autotube.domain.diagnostics import (
    CheckStatus,
    DoctorPolicy,
    HealthCheck,
    ProviderHealth,
    SystemFacts,
)
from autotube.domain.providers import ProviderDescriptor

GIB = 1024**3


def ok(name: str, detail: str) -> HealthCheck:
    return HealthCheck(name=name, status=CheckStatus.OK, detail=detail)


def warning(name: str, detail: str) -> HealthCheck:
    return HealthCheck(name=name, status=CheckStatus.WARNING, detail=detail)


def error(name: str, detail: str) -> HealthCheck:
    return HealthCheck(name=name, status=CheckStatus.ERROR, detail=detail)


def version_tuple(version: str) -> tuple[int, ...] | None:
    try:
        return tuple(int(part) for part in version.split(".")[:2])
    except ValueError:
        return None


def python_check(version: str, policy: DoctorPolicy) -> HealthCheck:
    needed = ".".join(str(part) for part in policy.min_python)
    parsed = version_tuple(version)
    if parsed is None or parsed < policy.min_python:
        return error("python", f"Python {version} is too old, {needed} or newer is required")
    return ok("python", f"Python {version}")


def data_dir_check(facts: SystemFacts) -> HealthCheck:
    if facts.data_dir_writable:
        return ok("data_dir", facts.data_dir)
    return error("data_dir", f"cannot create or write {facts.data_dir}")


def disk_check(free_bytes: int | None, policy: DoctorPolicy) -> HealthCheck:
    if free_bytes is None:
        return warning("disk_space", "free space is unknown")
    free = f"{free_bytes / GIB:.1f} GB free"
    if free_bytes < policy.min_free_gb * GIB:
        return warning("disk_space", f"{free}, at least {policy.min_free_gb:g} GB is recommended")
    return ok("disk_space", free)


def tool_check(name: str, version: str) -> HealthCheck:
    if version:
        return ok(name, version)
    return warning(name, f"{name} not found: video rendering needs it (brew install ffmpeg)")


def database_check(facts: SystemFacts) -> HealthCheck:
    current, head = facts.database_revision, facts.database_head
    if facts.database_error:
        return error("database", f"cannot read {facts.database_path}: {facts.database_error}")
    if current is None:
        return ok("database", f"{facts.database_path} is created on first start")
    if not facts.database_revision_known:
        return error("database", f"revision {current} is newer than this app: update the app")
    if current == head:
        return ok("database", f"up to date at {current}")
    return ok("database", f"migrates from {current} to {head} on start")


def ui_check(facts: SystemFacts) -> HealthCheck:
    if facts.ui_built:
        return ok("web_ui", facts.web_dist_dir)
    return warning("web_ui", f"no build in {facts.web_dist_dir}: run pnpm build in web/")


def system_checks(facts: SystemFacts, policy: DoctorPolicy) -> list[HealthCheck]:
    return [
        python_check(facts.python_version, policy),
        data_dir_check(facts),
        disk_check(facts.free_bytes, policy),
        tool_check("ffmpeg", facts.ffmpeg_version),
        tool_check("ffprobe", facts.ffprobe_version),
        database_check(facts),
        ui_check(facts),
    ]


def provider_health(descriptors: Iterable[ProviderDescriptor]) -> list[ProviderHealth]:
    return [
        ProviderHealth(
            provider_id=descriptor.provider_id,
            capability=descriptor.capability,
            name=descriptor.name,
            available=descriptor.available,
            reason=descriptor.unavailable_reason,
        )
        for descriptor in descriptors
    ]


def capability_check(capability: Capability, providers: Sequence[ProviderHealth]) -> HealthCheck:
    offered = [health for health in providers if health.capability is capability]
    ready = [health.provider_id for health in offered if health.available]
    if ready:
        return ok(capability.value, ", ".join(ready))
    if not offered:
        return warning(capability.value, "no provider is registered")
    reasons = "; ".join(f"{health.provider_id}: {health.reason}" for health in offered)
    return warning(capability.value, f"no provider is available: {reasons}")


def capability_checks(providers: Sequence[ProviderHealth]) -> list[HealthCheck]:
    return [capability_check(capability, providers) for capability in Capability]


def is_startable(checks: Iterable[HealthCheck]) -> bool:
    return all(check.status is not CheckStatus.ERROR for check in checks)

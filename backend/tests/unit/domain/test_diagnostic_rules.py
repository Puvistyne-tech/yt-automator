from __future__ import annotations

from typing import Any

import pytest

from autotube.domain.capabilities import Capability
from autotube.domain.diagnostic_rules import (
    GIB,
    capability_checks,
    database_check,
    disk_check,
    is_startable,
    provider_health,
    python_check,
    system_checks,
    tool_check,
)
from autotube.domain.diagnostics import CheckStatus, DoctorPolicy, HealthCheck
from autotube.domain.providers import ProviderDescriptor
from tests.fixtures.fake_diagnostics import system_facts as facts

POLICY = DoctorPolicy(min_free_gb=5.0)


def statuses(checks: list[HealthCheck]) -> dict[str, CheckStatus]:
    return {check.name: check.status for check in checks}


def test_healthy_facts_pass_every_check() -> None:
    checks = system_checks(facts(), POLICY)
    assert set(statuses(checks).values()) == {CheckStatus.OK}
    assert list(statuses(checks)) == [
        "python",
        "data_dir",
        "disk_space",
        "ffmpeg",
        "ffprobe",
        "database",
        "web_ui",
    ]
    assert is_startable(checks)


@pytest.mark.parametrize(
    ("version", "status"),
    [("3.11.9", "error"), ("3.12", "ok"), ("3.12.0", "ok"), ("3.13.0", "ok")],
)
def test_python_is_compared_with_the_minimum(version: str, status: str) -> None:
    assert python_check(version, POLICY).status == status


def test_unparseable_python_version_is_an_error() -> None:
    assert python_check("unknown", POLICY).status is CheckStatus.ERROR


def test_unwritable_data_dir_stops_the_app() -> None:
    checks = system_checks(facts(data_dir_writable=False), POLICY)
    assert statuses(checks)["data_dir"] is CheckStatus.ERROR
    assert not is_startable(checks)


@pytest.mark.parametrize(
    ("free", "status", "fragment"),
    [
        (50 * GIB, CheckStatus.OK, "50.0 GB free"),
        (1 * GIB, CheckStatus.WARNING, "at least 5 GB"),
        (5 * GIB, CheckStatus.OK, "5.0 GB free"),
        (5 * GIB - 1, CheckStatus.WARNING, "at least 5 GB"),
        (None, CheckStatus.WARNING, "unknown"),
    ],
)
def test_disk_space(free: int | None, status: CheckStatus, fragment: str) -> None:
    check = disk_check(free, POLICY)
    assert check.status is status
    assert fragment in check.detail


def test_missing_tool_is_a_warning_with_a_hint() -> None:
    check = tool_check("ffmpeg", "")
    assert check.status is CheckStatus.WARNING
    assert "brew install ffmpeg" in check.detail


def test_present_tool_reports_its_version() -> None:
    assert tool_check("ffprobe", "ffprobe version 7.1").detail == "ffprobe version 7.1"


@pytest.mark.parametrize("tool", ["ffmpeg", "ffprobe"])
def test_each_missing_tool_warns_on_its_own(tool: str) -> None:
    checks = system_checks(facts(**{f"{tool}_version": ""}), POLICY)
    warned = {name for name, status in statuses(checks).items() if status is CheckStatus.WARNING}
    assert warned == {tool}
    assert is_startable(checks)


@pytest.mark.parametrize(
    ("changes", "status", "fragment"),
    [
        ({"database_revision": None}, CheckStatus.OK, "created on first start"),
        ({}, CheckStatus.OK, "up to date at 0001"),
        ({"database_head": "0002"}, CheckStatus.OK, "migrates from 0001 to 0002"),
        ({"database_revision_known": False}, CheckStatus.ERROR, "newer than this app"),
        ({"database_error": "file is not a database"}, CheckStatus.ERROR, "not a database"),
    ],
)
def test_database_state(changes: dict[str, Any], status: CheckStatus, fragment: str) -> None:
    check = database_check(facts(**changes))
    assert check.status is status
    assert fragment in check.detail


def test_missing_ui_build_is_a_warning_only() -> None:
    checks = system_checks(facts(ui_built=False), POLICY)
    assert statuses(checks)["web_ui"] is CheckStatus.WARNING
    assert is_startable(checks)


def descriptor(provider_id: str, capability: Capability, reason: str = "") -> ProviderDescriptor:
    return ProviderDescriptor(
        provider_id=provider_id,
        capability=capability,
        name=provider_id.title(),
        available=not reason,
        unavailable_reason=reason,
    )


def test_capability_checks_cover_every_capability() -> None:
    providers = provider_health(
        [
            descriptor("groq", Capability.LLM, "set the Groq API key secret"),
            descriptor("ollama", Capability.LLM),
            descriptor("offline", Capability.LLM),
            descriptor("mflux", Capability.IMAGE, "needs an Apple-silicon Mac"),
        ]
    )
    checks = capability_checks(providers)
    assert [check.name for check in checks] == [capability.value for capability in Capability]
    by_name = {check.name: check for check in checks}
    assert by_name["llm"].status is CheckStatus.OK
    assert by_name["llm"].detail == "ollama, offline"
    assert by_name["image"].status is CheckStatus.WARNING
    assert "mflux: needs an Apple-silicon Mac" in by_name["image"].detail
    assert by_name["music"].detail == "no provider is registered"
    assert is_startable(checks)


def test_provider_health_keeps_the_reason() -> None:
    [health] = provider_health([descriptor("mflux", Capability.IMAGE, "needs a Mac")])
    assert (health.provider_id, health.available, health.reason) == ("mflux", False, "needs a Mac")

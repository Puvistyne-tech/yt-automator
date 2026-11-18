from __future__ import annotations

from automator.application.run_doctor import RunDoctor
from automator.domain.diagnostics import CheckStatus, DoctorPolicy
from automator.domain.ports import SecretStore
from tests.fixtures.fake_diagnostics import FakeInspector, UnreadableSecrets, system_facts
from tests.fixtures.fake_providers import FakeProviderCatalog
from tests.fixtures.fake_runtime import InMemorySecrets


def doctor(inspector: FakeInspector, secrets: SecretStore | None = None) -> RunDoctor:
    return RunDoctor(
        catalog=FakeProviderCatalog(),
        secrets=secrets or InMemorySecrets(),
        inspector=inspector,
        policy=DoctorPolicy(),
    )


def test_healthy_system_can_start_and_lists_providers() -> None:
    report = doctor(FakeInspector()).execute()
    assert report.can_start
    assert [health.provider_id for health in report.providers] == [
        "fake-llm",
        "cloud-llm",
        "fake-image",
    ]
    assert {check.name for check in report.checks} >= {"python", "database", "web_ui"}
    assert {check.name: check.status for check in report.capabilities}["llm"] is CheckStatus.OK


def test_missing_secrets_are_listed() -> None:
    report = doctor(FakeInspector()).execute()
    assert [secret.name for secret in report.missing_secrets] == ["cloud_api_key"]


def test_set_secrets_are_not_listed() -> None:
    secrets = InMemorySecrets()
    secrets.set("cloud_api_key", "value")
    assert doctor(FakeInspector(), secrets).execute().missing_secrets == ()


def test_a_system_error_means_the_app_cannot_start() -> None:
    report = doctor(FakeInspector(system_facts(data_dir_writable=False))).execute()
    assert not report.can_start


def test_missing_providers_are_only_warnings() -> None:
    report = doctor(FakeInspector()).execute()
    music = {check.name: check for check in report.capabilities}["music"]
    assert music.status is CheckStatus.WARNING
    assert report.can_start


def test_unreadable_secrets_become_a_warning() -> None:
    report = doctor(FakeInspector(), UnreadableSecrets()).execute()
    secrets_check = {check.name: check for check in report.checks}["secrets"]
    assert secrets_check.status is CheckStatus.WARNING
    assert "cannot read" in secrets_check.detail
    assert report.missing_secrets == ()
    assert report.can_start

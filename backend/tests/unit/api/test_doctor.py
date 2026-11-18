from __future__ import annotations

from fastapi.testclient import TestClient

from automator.infrastructure.config import RuntimeConfig
from automator.main import Overrides
from tests.fixtures.fake_diagnostics import FakeInspector, system_facts
from tests.fixtures.fake_runtime import InMemorySecrets
from tests.unit.api.client import ok, wired


def test_doctor_report_has_the_spec_shape(client: TestClient) -> None:
    report = ok(client.get("/api/doctor"))
    assert set(report) == {"can_start", "checks", "capabilities", "providers", "missing_secrets"}
    assert set(report["checks"][0]) == {"name", "status", "detail"}
    assert set(report["providers"][0]) == {
        "provider_id",
        "capability",
        "name",
        "available",
        "reason",
    }
    assert set(report["missing_secrets"][0]) == {"name", "title", "description"}
    assert report["can_start"] is True


def test_doctor_never_returns_secret_values(client: TestClient, secrets: InMemorySecrets) -> None:
    secrets.set("cloud_api_key", "s3cret-value")
    response = client.get("/api/doctor")
    assert ok(response)["missing_secrets"] == []
    assert "s3cret-value" not in response.text


def test_doctor_reports_when_the_app_cannot_start(
    config: RuntimeConfig, overrides: Overrides
) -> None:
    broken = FakeInspector(system_facts(data_dir_writable=False))
    with wired(config, overrides, inspector=broken) as client:
        report = ok(client.get("/api/doctor"))
    assert report["can_start"] is False
    assert {check["name"]: check["status"] for check in report["checks"]}["data_dir"] == "error"

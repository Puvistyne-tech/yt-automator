from __future__ import annotations

from fastapi.testclient import TestClient

from tests.unit.api.client import ok


def test_doctor_reports_checks_providers_and_missing_secrets(client: TestClient) -> None:
    report = ok(client.get("/api/doctor"))
    assert report["can_start"] is True
    checks = {check["name"]: check for check in report["checks"]}
    assert checks["database"]["detail"] == "up to date at 0001"
    assert checks["web_ui"]["status"] == "warning"
    assert [provider["provider_id"] for provider in report["providers"]] == [
        "fake-llm",
        "cloud-llm",
        "fake-image",
    ]
    assert [secret["name"] for secret in report["missing_secrets"]] == ["cloud_api_key"]
    assert {check["name"] for check in report["capabilities"]} >= {"llm", "media"}

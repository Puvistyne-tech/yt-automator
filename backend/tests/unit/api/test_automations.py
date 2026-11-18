from __future__ import annotations

from typing import Any

import pytest

from tests.unit.api.client import Api, automation_body, error_of, ok, send


def test_automation_crud(api: Api) -> None:
    client = api.client
    channel_id = api.channel()
    created = api.automation(channel_id)
    automation_id = created["id"]
    assert created["targets"][0]["id"]
    assert (created["next_run_at"], created["last_run"]) == (None, None)
    assert created["schedule"] == {
        "kind": "manual",
        "every_hours": None,
        "cron": None,
        "timezone": "UTC",
        "skip_if_unfinished": True,
        "max_runs_per_day": None,
        "active_from": None,
        "active_until": None,
    }
    assert created["review_policy"] == {
        "mode": "always",
        "min_score": 85.0,
        "reject_below": None,
        "auto_publish": False,
    }
    assert created["retry_policy"] == {"auto_retry_count": 0, "retry_delay_minutes": 10}
    assert [item["id"] for item in ok(client.get("/api/automations"))] == [automation_id]
    assert ok(client.get(f"/api/automations/{automation_id}"))["name"] == "Bedtime"
    schedule = {"kind": "interval", "every_hours": 6}
    body = automation_body(channel_id, name="Morning", schedule=schedule)
    updated = ok(client.put(f"/api/automations/{automation_id}", json=body))
    assert (updated["name"], updated["next_run_at"] is not None) == ("Morning", True)
    disabled = ok(client.patch(f"/api/automations/{automation_id}", json={"enabled": False}))
    assert (disabled["enabled"], disabled["next_run_at"]) == (False, None)
    copy = ok(client.post(f"/api/automations/{automation_id}/duplicate"), 201)
    assert copy["id"] != automation_id
    assert copy["name"].startswith("Morning")
    ok(client.delete(f"/api/automations/{automation_id}"), 204)
    assert [item["id"] for item in ok(client.get("/api/automations"))] == [copy["id"]]


@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"pipeline_type": "unknown"}, "pipeline_type"),
        ({"languages": ["xx"]}, "languages.0"),
        ({"settings": {"topic": ""}}, "settings.topic"),
        ({"schedule": {"kind": "interval", "every_hours": 0}}, "schedule.every_hours"),
        ({"schedule": {"kind": "cron", "cron": "bad"}}, "schedule.cron"),
        ({"name": ""}, "name"),
        ({"languages": []}, "languages"),
    ],
)
def test_invalid_automations_report_field_paths(
    api: Api, changes: dict[str, Any], field: str
) -> None:
    channel_id = api.channel()
    body = automation_body(channel_id, **changes)
    existing = api.automation(channel_id)
    for method, path in (
        ("post", "/api/automations"),
        ("put", f"/api/automations/{existing['id']}"),
    ):
        error = error_of(send(api.client, method, path, body), 400)
        assert error["code"] == "validation_failed"
        assert field in error["fields"], error["fields"]


@pytest.mark.parametrize("body", [{}, {"enabled": "x"}])
def test_enabling_needs_a_boolean(api: Api, body: dict[str, Any]) -> None:
    automation = api.automation(api.channel())
    response = api.client.patch(f"/api/automations/{automation['id']}", json=body)
    assert "enabled" in error_of(response, 400)["fields"]


def test_unknown_target_channel_is_rejected(api: Api) -> None:
    error = error_of(api.client.post("/api/automations", json=automation_body("nope")), 400)
    assert any(path.startswith("targets.0") for path in error["fields"])


@pytest.mark.parametrize(
    ("method", "suffix", "body"),
    [
        ("get", "", None),
        ("put", "", "valid"),
        ("patch", "", {"enabled": True}),
        ("delete", "", None),
        ("post", "/duplicate", None),
        ("post", "/runs", None),
    ],
)
def test_missing_automation_is_not_found(api: Api, method: str, suffix: str, body: Any) -> None:
    payload = automation_body(api.channel()) if body == "valid" else body
    response = send(api.client, method, f"/api/automations/missing{suffix}", payload)
    assert error_of(response, 404)["code"] == "automation_not_found"

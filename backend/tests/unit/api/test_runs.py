from __future__ import annotations

from typing import Any

import pytest

from tests.fixtures.fake_pipeline import FakePipelineRegistry
from tests.fixtures.fake_youtube import FakeYouTube
from tests.unit.api.client import Api, error_of, ok, send


def test_runs_list_filters_and_limits(api: Api) -> None:
    client = api.client
    first = api.finished_run()
    automation_id = first["automation_id"]
    second = api.wait_for(api.start(automation_id)["id"], "awaiting_review")
    listed = ok(client.get("/api/runs"))
    assert [run["id"] for run in listed] == [second["id"], first["id"]]
    assert len(ok(client.get("/api/runs", params={"limit": 1}))) == 1
    assert len(ok(client.get("/api/runs", params={"limit": 100}))) == 2
    filtered = ok(client.get("/api/runs", params={"automation_id": "other"}))
    assert filtered == []
    by_status = ok(client.get("/api/runs", params={"status": "awaiting_review"}))
    assert len(by_status) == 2


@pytest.mark.parametrize(
    ("params", "field"),
    [({"limit": 0}, "limit"), ({"limit": 101}, "limit"), ({"status": "nope"}, "status")],
)
def test_runs_list_rejects_bad_queries(api: Api, params: dict[str, Any], field: str) -> None:
    assert field in error_of(api.client.get("/api/runs", params=params), 400)["fields"]


def test_review_reject_retry_and_delete(api: Api) -> None:
    client = api.client
    run = api.finished_run()
    run_id = run["id"]
    rejected = ok(client.post(f"/api/runs/{run_id}/review", json={"decision": "rejected"}))
    assert rejected["review"]["decision"] == "rejected"
    error_of(client.post(f"/api/runs/{run_id}/publish"), 409)
    retried = ok(client.post(f"/api/runs/{run_id}/retry", json={"from_stage": "render"}))
    assert retried["status"] == "queued"
    api.wait_for(run_id, "awaiting_review")
    ok(client.post(f"/api/runs/{run_id}/retry"))
    api.wait_for(run_id, "awaiting_review")
    cancelled = ok(client.post(f"/api/runs/{run_id}/cancel"))
    assert cancelled["status"] == "cancelled"
    ok(client.delete(f"/api/runs/{run_id}"), 204)
    error_of(client.get(f"/api/runs/{run_id}"), 404)
    assert not (api.runtime.config.data_dir / "runs" / run_id).exists()


def test_run_rule_conflicts(api: Api) -> None:
    client = api.client
    run_id = api.finished_run()["id"]
    error_of(client.post(f"/api/runs/{run_id}/retry", json={"from_stage": "nope"}), 400)
    ok(client.post(f"/api/runs/{run_id}/review", json={"decision": "approved"}))
    error_of(client.post(f"/api/runs/{run_id}/review", json={"decision": "approved"}), 409)
    error_of(client.post(f"/api/runs/{run_id}/review", json={"decision": "maybe"}), 400)


def test_failed_stage_fails_the_run(api: Api) -> None:
    run = api.finished_run(settings={"topic": "owls", "fail_stage": "render"})
    assert run["status"] == "failed"
    assert "render" in run["error"]


def test_publish_upstream_failure_keeps_run_approved(api: Api, youtube: FakeYouTube) -> None:
    run = api.approved_run()
    youtube.failing_videos.add("en-landscape.mp4")
    published = ok(api.client.post(f"/api/runs/{run['id']}/publish"))
    assert published["status"] == "approved"
    assert published["uploads"][0]["status"] == "failed"


def test_artifacts_are_served_whole_with_their_media_type(api: Api) -> None:
    run = api.finished_run()
    srt = next(item for item in run["artifacts"] if item["kind"] == "subtitle")
    response = api.client.get(f"/api/runs/{run['id']}/artifacts/{srt['id']}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-subrip")
    assert response.headers["accept-ranges"] == "bytes"
    assert response.content.startswith(b"1\n00:00:00,000")
    error_of(api.client.get(f"/api/runs/{run['id']}/artifacts/missing"), 404)


@pytest.mark.parametrize(
    ("method", "suffix", "body"),
    [
        ("get", "", None),
        ("post", "/retry", {}),
        ("post", "/cancel", None),
        ("post", "/review", {"decision": "approved"}),
        ("post", "/publish", None),
        ("delete", "", None),
        ("get", "/artifacts/a", None),
    ],
)
def test_missing_run_is_not_found(api: Api, method: str, suffix: str, body: Any) -> None:
    response = send(api.client, method, f"/api/runs/missing{suffix}", body)
    assert error_of(response, 404)["code"] == "run_not_found"


def video_of(run: dict[str, Any]) -> dict[str, Any]:
    return next(item for item in run["artifacts"] if item["kind"] == "video")


@pytest.mark.parametrize(
    "path",
    [
        "/api/runs/{run}/artifacts/%2e%2e%2fsecret",
        "/api/runs/..%2fx/artifacts/{artifact}",
        "/api/runs/{run}/artifacts/%2e%2e",
        "/api/runs/%2e%2e/artifacts/{artifact}",
    ],
)
def test_traversal_ids_get_the_error_envelope(api: Api, path: str) -> None:
    run = api.finished_run()
    response = api.client.get(path.format(run=run["id"], artifact=video_of(run)["id"]))
    assert response.status_code in (400, 404)
    error_of(response, response.status_code)


def test_unsatisfiable_ranges_and_deleted_files(api: Api) -> None:
    run = api.finished_run()
    video = video_of(run)
    url = f"/api/runs/{run['id']}/artifacts/{video['id']}"
    assert api.client.get(url, headers={"Range": "bytes=100-200"}).status_code == 416
    stored = api.runtime.config.data_dir / "runs" / run["id"] / "artifacts" / video["id"]
    for file in stored.iterdir():
        file.unlink()
    assert error_of(api.client.get(url), 404)["code"] == "artifact_file_not_found"


def test_publish_conflicts(api: Api) -> None:
    client = api.client
    waiting = api.finished_run()
    error = error_of(client.post(f"/api/runs/{waiting['id']}/publish"), 409)
    assert error["code"] == "invalid_run_transition"
    poor = api.credential(daily_quota_units=1)
    automation = api.automation(api.connect(poor["id"]))
    run_id = api.wait_for(api.start(automation["id"])["id"], "awaiting_review")["id"]
    ok(client.post(f"/api/runs/{run_id}/review", json={"decision": "approved"}))
    assert error_of(client.post(f"/api/runs/{run_id}/publish"), 409)["code"] == "quota_exceeded"


def test_publishing_without_a_reachable_target_is_a_conflict(api: Api) -> None:
    run = api.approved_run()
    automation_id, channel_id = run["automation_id"], ok(api.client.get("/api/channels"))[0]["id"]
    ok(api.client.patch(f"/api/automations/{automation_id}", json={"enabled": False}))
    ok(api.client.delete(f"/api/channels/{channel_id}"), 204)
    error = error_of(api.client.post(f"/api/runs/{run['id']}/publish"), 409)
    assert error["code"] == "nothing_to_publish"


def test_finished_runs_refuse_retry_and_repeat_cancel(api: Api) -> None:
    client = api.client
    run = api.approved_run()
    published = ok(client.post(f"/api/runs/{run['id']}/publish"))
    assert published["status"] == "published"
    error_of(client.post(f"/api/runs/{run['id']}/retry"), 409)
    other = api.finished_run()
    ok(client.post(f"/api/runs/{other['id']}/cancel"))
    error_of(client.post(f"/api/runs/{other['id']}/cancel"), 409)


def test_starting_a_run_of_an_uninstalled_pipeline_is_a_conflict(api: Api) -> None:
    automation = api.automation(api.channel())
    registry = api.runtime.ports.pipelines
    assert isinstance(registry, FakePipelineRegistry)
    registry.pipelines.pop("fake")
    response = api.client.post(f"/api/automations/{automation['id']}/runs")
    assert error_of(response, 409)["code"] == "pipeline_unavailable"

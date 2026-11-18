from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from autotube.infrastructure.config import RuntimeConfig
from autotube.main import Overrides, Runtime
from tests.fixtures.fake_runtime import FakeClock
from tests.unit.api.client import Api, error_of, ok, wired


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def timed(config: RuntimeConfig, overrides: Overrides, clock: FakeClock) -> Iterator[Api]:
    with wired(config, overrides, clock=clock) as client:
        yield Api(client, client.app.state.runtime)  # type: ignore[attr-defined]


def run_dir(api: Api, run_id: str) -> Path:
    runtime: Runtime = api.runtime
    return runtime.config.data_dir / "runs" / run_id


def reviewed(api: Api, decision: str) -> dict[str, Any]:
    run = api.finished_run()
    body = {"decision": decision}
    done: dict[str, Any] = ok(api.client.post(f"/api/runs/{run['id']}/review", json=body))
    return done


def published(api: Api) -> dict[str, Any]:
    approved = reviewed(api, "approved")
    ok(api.client.post(f"/api/runs/{approved['id']}/publish"))
    return api.wait_for(approved["id"], "published")


def actions(client: TestClient, method: str) -> dict[str, str]:
    report = ok(client.request(method, "/api/storage/cleanup"))
    return {item["run_id"]: item["action"] for item in report["items"]}


def test_retention_flow_through_the_app(timed: Api, clock: FakeClock) -> None:
    client = timed.client
    ok(client.put("/api/settings", json={"keep_runs_days": 30, "keep_intermediate_days": 7}))
    rejected, done = reviewed(timed, "rejected"), published(timed)
    waiting, approved = timed.finished_run(), reviewed(timed, "approved")
    stray = run_dir(timed, "stray-1") / "workspace"
    stray.mkdir(parents=True)
    (stray / "left.bin").write_bytes(b"12345")

    clock.advance(days=8)
    expected = {
        rejected["id"]: "remove_intermediate",
        done["id"]: "remove_intermediate",
        "stray-1": "remove_orphan",
    }
    assert actions(client, "GET") == expected
    assert run_dir(timed, "stray-1").exists()
    assert actions(client, "POST") == expected
    trimmed = ok(client.get(f"/api/runs/{rejected['id']}"))
    assert {a["kind"] for a in trimmed["artifacts"]} == {
        "video",
        "thumbnail",
        "subtitle",
        "metadata",
    }
    assert trimmed["intermediate_removed_at"] is not None
    assert not (run_dir(timed, rejected["id"]) / "workspace").exists()
    assert not run_dir(timed, "stray-1").exists()
    refused = client.post(f"/api/runs/{rejected['id']}/retry", json={"from_stage": "render"})
    assert error_of(refused, 409)["code"] == "intermediate_files_removed"

    clock.advance(days=23)
    assert actions(client, "POST") == {rejected["id"]: "delete_run", done["id"]: "delete_run"}
    for gone in (rejected, done):
        assert error_of(client.get(f"/api/runs/{gone['id']}"), 404)["code"] == "run_not_found"
        assert not run_dir(timed, gone["id"]).exists()
    for kept in (waiting, approved):
        assert ok(client.get(f"/api/runs/{kept['id']}"))["artifacts"]
        assert run_dir(timed, kept["id"]).exists()
    assert actions(client, "POST") == {}


def test_storage_reports_disk_use_per_automation(timed: Api) -> None:
    run = timed.finished_run()
    report = ok(timed.client.get("/api/storage"))
    assert report["data_dir"] == str(timed.runtime.config.data_dir)
    assert report["final_bytes"] > 0 and report["intermediate_bytes"] > 0
    assert report["data_dir_bytes"] >= report["final_bytes"] + report["intermediate_bytes"]
    assert [u["automation_name"] for u in report["automations"]] == [run["automation_name"]]
    assert report["automations"][0]["runs"] == 1 and report["orphan_bytes"] == 0


def test_the_preview_echoes_the_retention_settings(timed: Api) -> None:
    ok(timed.client.put("/api/settings", json={"keep_runs_days": 0, "keep_intermediate_days": 3}))
    report = ok(timed.client.get("/api/storage/cleanup"))
    assert report == {
        "dry_run": True,
        "keep_runs_days": 0,
        "keep_intermediate_days": 3,
        "items": [],
        "total_bytes": 0,
    }


def test_the_scheduler_cleans_up_only_once_switched_on(timed: Api, clock: FakeClock) -> None:
    ok(timed.client.put("/api/settings", json={"keep_runs_days": 1}))
    run = reviewed(timed, "rejected")
    clock.advance(days=2)
    timed.runtime.scheduler.tick_once()
    ok(timed.client.get(f"/api/runs/{run['id']}"))
    ok(timed.client.put("/api/settings", json={"auto_cleanup_enabled": True}))
    timed.runtime.scheduler.tick_once()
    assert error_of(timed.client.get(f"/api/runs/{run['id']}"), 404)["code"] == "run_not_found"

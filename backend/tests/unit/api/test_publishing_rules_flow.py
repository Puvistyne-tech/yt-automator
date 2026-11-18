from __future__ import annotations

import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest

from automator.domain.pipeline import StageContext
from automator.domain.pipeline_descriptors import StageDescriptor
from automator.infrastructure.config import RuntimeConfig
from automator.main import Overrides
from tests.fixtures.fake_pipeline import (
    FakePipeline,
    FakePipelineRegistry,
    FakeStage,
    kids_pipeline,
)
from tests.fixtures.fake_runtime import FakeClock
from tests.fixtures.fake_youtube import FakeYouTube
from tests.unit.api.client import Api, ok, wired


@dataclass
class StageControl:
    failures_left: int = 0
    gate: threading.Event = field(default_factory=threading.Event)

    def __post_init__(self) -> None:
        self.gate.set()

    def hook(self, _: StageContext) -> None:
        self.gate.wait(10)
        if self.failures_left > 0:
            self.failures_left -= 1
            raise RuntimeError("render flaked")


def controlled_pipeline(control: StageControl) -> FakePipeline:
    stages = tuple(
        FakeStage(
            StageDescriptor(id=stage_id, title=stage_id.title()),
            hook=control.hook if stage_id == "render" else None,
        )
        for stage_id in ("script", "render", "package")
    )
    return FakePipeline(stage_list=stages)


@dataclass
class Rig:
    api: Api
    clock: FakeClock
    youtube: FakeYouTube
    control: StageControl

    def tick(self, **delta: float) -> None:
        self.clock.advance(**delta)
        self.api.runtime.use_cases.automations.scheduler.execute(self.clock.now())

    def run_of(self, automation_id: str) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = ok(
            self.api.client.get("/api/runs", params={"automation_id": automation_id})
        )
        return found


@pytest.fixture
def rig(config: RuntimeConfig, overrides: Overrides, youtube: FakeYouTube) -> Iterator[Rig]:
    clock = FakeClock()
    control = StageControl()
    pipelines = FakePipelineRegistry([controlled_pipeline(control), kids_pipeline()])
    with wired(config, overrides, clock=clock, pipelines=pipelines) as client:
        yield Rig(Api(client, client.app.state.runtime), clock, youtube, control)  # type: ignore[attr-defined]
        control.gate.set()


def messages(run: dict[str, Any]) -> list[str]:
    return [log["message"] for log in run["logs"]]


def test_a_low_score_is_rejected_automatically(rig: Rig) -> None:
    policy = {"mode": "always", "min_score": 85, "reject_below": 50}
    automation = rig.api.automation(rig.api.channel(), settings={"score": 30}, review_policy=policy)
    run = rig.api.wait_for(rig.api.start(automation["id"])["id"], "rejected")
    assert run["status"] == "rejected" and run["review"]["decision"] == "rejected"


def test_approving_by_hand_publishes_automatically(rig: Rig) -> None:
    policy = {"mode": "always", "min_score": 85, "auto_publish": True}
    run = rig.api.finished_run(review_policy=policy)
    assert run["status"] == "awaiting_review"
    ok(rig.api.client.post(f"/api/runs/{run['id']}/review", json={"decision": "approved"}))
    published = rig.api.wait_for(run["id"], "published")
    assert published["uploads"][0]["status"] == "done"
    assert published["uploads"][0]["privacy"] == "private"
    assert "Publishing automatically after approval" in messages(published)
    assert len(rig.youtube.uploads) == 1


def test_a_public_target_publishes_at_its_time_of_day(rig: Rig) -> None:
    target: dict[str, Any] = {"privacy": "public", "publish_time_of_day": "18:00"}
    target |= {"publish_timezone": "Asia/Kolkata", "language": "en", "variants": ["landscape"]}
    policy = {"mode": "auto_when_score_at_least", "min_score": 80, "auto_publish": True}
    channel_id = rig.api.channel()
    automation = rig.api.automation(
        channel_id, targets=[{**target, "channel_id": channel_id}], review_policy=policy
    )
    run = rig.api.wait_for(rig.api.start(automation["id"])["id"], "published")
    expected = datetime(2026, 1, 5, 12, 30, tzinfo=UTC)
    assert run["uploads"][0]["publish_at"] == "2026-01-05T12:30:00Z"
    assert rig.youtube.uploads[0].publish_at == expected


def test_a_failed_run_retries_on_its_own_and_succeeds(rig: Rig) -> None:
    rig.control.failures_left = 1
    retry = {"auto_retry_count": 2, "retry_delay_minutes": 5}
    failed = rig.api.finished_run(retry_policy=retry)
    assert failed["status"] == "failed" and failed["retry_at"] == "2026-01-05T10:05:00Z"
    rig.tick(minutes=5)
    finished = rig.api.wait_for(failed["id"], "awaiting_review")
    assert finished["auto_retries"] == 1 and finished["retry_at"] is None


def test_a_scheduled_start_is_skipped_while_the_last_run_works(rig: Rig) -> None:
    schedule = {"kind": "interval", "every_hours": 1}
    automation = rig.api.automation(rig.api.channel(), schedule=schedule)
    rig.control.gate.clear()
    rig.tick(hours=1)
    [first] = rig.run_of(automation["id"])
    rig.api.wait_for(first["id"], "running")
    rig.tick(hours=1)
    assert len(rig.run_of(automation["id"])) == 1
    blocked = ok(rig.api.client.get(f"/api/runs/{first['id']}"))
    assert blocked["skipped_start_at"] == "2026-01-05T12:00:00Z"
    listed = ok(rig.api.client.get(f"/api/automations/{automation['id']}"))
    assert listed["next_run_at"] == "2026-01-05T13:00:00Z"
    rig.control.gate.set()
    rig.api.wait_for(first["id"], "awaiting_review")

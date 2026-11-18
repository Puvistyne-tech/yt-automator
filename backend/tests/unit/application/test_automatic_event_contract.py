from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from autotube.application.auto_publish import STARTING, stopped_message
from autotube.application.retry_due_runs import retry_message
from autotube.application.run_due_automations import skip_message
from autotube.domain.quality import ReviewPolicy, auto_rejection
from autotube.domain.retries import RetryPolicy
from autotube.domain.run_enums import RunStatus
from autotube.domain.schedules import Schedule, ScheduleKind
from tests.fixtures.builders import add_automation, finished_run, started_run
from tests.fixtures.harness import Harness

SAMPLES_PATH = Path(__file__).resolve().parents[4] / "docs" / "spec" / "automatic-events.json"


@pytest.fixture
def samples() -> dict[str, dict[str, Any]]:
    loaded: dict[str, dict[str, Any]] = json.loads(SAMPLES_PATH.read_text())
    return loaded


def test_auto_reject_matches_the_shared_sample(samples: dict[str, dict[str, Any]]) -> None:
    sample = samples["auto_reject"]
    policy = ReviewPolicy(reject_below=sample["threshold"])
    assert auto_rejection(policy, sample["score"]) == sample["message"]


def test_auto_publish_messages_match_the_shared_samples(
    samples: dict[str, dict[str, Any]],
) -> None:
    assert samples["auto_publish_started"]["message"] == STARTING
    stopped = samples["auto_publish_stopped"]
    assert stopped_message(stopped["reason"]) == stopped["message"]


def test_automatic_retry_matches_the_shared_sample(
    harness: Harness, samples: dict[str, dict[str, Any]]
) -> None:
    sample = samples["automatic_retry"]
    policy = RetryPolicy(auto_retry_count=sample["count"])
    failed = finished_run(harness, settings={"fail_stage": sample["stage"]}, retry_policy=policy)
    queued = failed.model_copy(update={"auto_retries": sample["attempt"]})
    assert retry_message(queued, sample["failure"]) == sample["message"]


def test_skipped_start_matches_the_shared_sample(
    harness: Harness, samples: dict[str, dict[str, Any]]
) -> None:
    sample = samples["skipped_start"]
    schedule = Schedule(kind=ScheduleKind.INTERVAL, every_hours=1, timezone=sample["timezone"])
    automation = add_automation(harness, schedule=schedule)
    blocker = started_run(harness).model_copy(
        update={"id": sample["run_id"], "status": RunStatus(sample["state"])}
    )
    slot = datetime.fromisoformat(sample["slot"])
    assert skip_message(automation, slot, blocker) == sample["message"]

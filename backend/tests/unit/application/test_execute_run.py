from __future__ import annotations

from dataclasses import replace

import pytest

from automator.domain.pipeline import StageContext
from automator.domain.quality import ReviewMode, ReviewPolicy
from automator.domain.run_enums import (
    ArtifactKind,
    RunEventKind,
    RunStatus,
    RunTrigger,
    StageStatus,
)
from automator.domain.run_state import transition
from automator.shared.errors import NotFound, RuleConflict
from tests.fixtures.builders import add_automation, execute_run, finished_run, started_run
from tests.fixtures.fake_pipeline import FakePipelineRegistry
from tests.fixtures.harness import Harness

AUTO = ReviewPolicy(mode=ReviewMode.AUTO_WHEN_SCORE_AT_LEAST, min_score=85)


def test_start_run_snapshots_and_enqueues(harness: Harness) -> None:
    run = started_run(harness, languages=("en", "ta"))
    assert run.status is RunStatus.QUEUED and run.trigger is RunTrigger.MANUAL
    assert run.languages == ("en", "ta") and run.settings_snapshot["topic"] == "owls"
    assert [s.stage_id for s in run.stages] == ["script", "render", "package"]
    assert all(s.status is StageStatus.PENDING for s in run.stages)
    assert harness.queue.enqueued == [run.id]
    assert harness.events.published[-1].kind is RunEventKind.STATUS


def test_start_run_errors(harness: Harness) -> None:
    with pytest.raises(NotFound):
        harness.start_run.execute("missing")
    automation = add_automation(harness)
    harness.pipelines = FakePipelineRegistry([])
    with pytest.raises(RuleConflict) as raised:
        harness.start_run.execute(automation.id)
    assert raised.value.code == "pipeline_unavailable"


def test_execute_runs_every_stage_and_awaits_review(harness: Harness) -> None:
    run = finished_run(harness, languages=("en", "ta"))
    assert run.status is RunStatus.AWAITING_REVIEW and run.score == 90.0
    assert [s.status for s in run.stages] == [StageStatus.DONE] * 3
    assert all(s.provider == "fake" and s.started_at and s.finished_at for s in run.stages)
    kinds = [a.kind for a in run.artifacts]
    assert kinds.count(ArtifactKind.VIDEO) == 4 and kinds.count(ArtifactKind.METADATA) == 2
    assert {a.stage_id for a in run.artifacts} == {"script", "render", "package"}
    assert harness.runs.get(run.id) == run
    assert run.started_at is not None and run.finished_at is not None
    assert harness.catalog.text.requests[0].prompt == "owls"


def test_execute_publishes_progress_events(harness: Harness) -> None:
    run = finished_run(harness)
    events = [e for e in harness.events.published if e.run_id == run.id]
    kinds = {e.kind for e in events}
    assert kinds == {
        RunEventKind.STATUS,
        RunEventKind.STAGE,
        RunEventKind.LOG,
        RunEventKind.ARTIFACT,
    }
    statuses = [e.payload["status"] for e in events if e.kind is RunEventKind.STATUS]
    assert statuses == ["queued", "running", "awaiting_review"]
    assert {"message": "render running"} in [e.payload for e in events]


@pytest.mark.parametrize(
    ("score", "status"), [(85.0, RunStatus.APPROVED), (84.0, RunStatus.AWAITING_REVIEW)]
)
def test_auto_review_policy(harness: Harness, score: float, status: RunStatus) -> None:
    run = finished_run(harness, review_policy=AUTO, settings={"score": score})
    assert run.status is status


def test_deleted_automation_falls_back_to_manual_review(harness: Harness) -> None:
    run = started_run(harness, review_policy=AUTO)
    harness.automations.delete(run.automation_id)
    assert execute_run(harness).execute(run.id).status is RunStatus.AWAITING_REVIEW


def test_stage_failure_fails_run_and_skips_later_stages(harness: Harness) -> None:
    run = finished_run(harness, settings={"fail_stage": "render"})
    assert run.status is RunStatus.FAILED
    assert run.error == "stage render failed: render exploded"
    assert [s.status for s in run.stages] == [
        StageStatus.DONE,
        StageStatus.FAILED,
        StageStatus.PENDING,
    ]
    assert run.stages[1].message == "render exploded"
    assert {a.stage_id for a in run.artifacts} == {"script"}
    assert harness.pipeline.stage_list[2].calls == []


def test_scoring_failure_fails_run(harness: Harness) -> None:
    harness.pipelines = FakePipelineRegistry([replace(harness.pipeline, raise_on_score=True)])
    run = finished_run(harness)
    assert run.status is RunStatus.FAILED and run.error == "scoring failed: scorer offline"


def test_missing_pipeline_or_invalid_snapshot_fails_run(harness: Harness) -> None:
    run = started_run(harness)
    harness.runs.save(run.model_copy(update={"settings_snapshot": {"score": "high"}}))
    failed = execute_run(harness).execute(run.id)
    assert failed.status is RunStatus.FAILED and "settings are invalid" in (failed.error or "")
    other = harness.start_run.execute(run.automation_id)
    harness.pipelines = FakePipelineRegistry([])
    missing = execute_run(harness).execute(other.id)
    assert missing.status is RunStatus.FAILED and "not installed" in (missing.error or "")


@pytest.mark.parametrize("status", [RunStatus.CANCELLED, RunStatus.AWAITING_REVIEW])
def test_execute_ignores_runs_that_are_not_queued(harness: Harness, status: RunStatus) -> None:
    run = started_run(harness).model_copy(update={"status": status})
    harness.runs.save(run)
    assert execute_run(harness).execute(run.id) == run
    assert harness.pipeline.stage_list[0].calls == []


def test_cancellation_during_a_stage_stops_the_run(harness: Harness) -> None:
    run = started_run(harness)

    def cancel_midway(context: StageContext) -> None:
        stored = harness.runs.get(context.run_id)
        assert stored is not None
        harness.runs.save(transition(stored, RunStatus.CANCELLED, harness.clock.now()))

    first, *rest = harness.pipeline.stage_list
    stages = (replace(first, hook=cancel_midway), *rest)
    harness.pipelines = FakePipelineRegistry([replace(harness.pipeline, stage_list=stages)])
    result = execute_run(harness).execute(run.id)
    assert result.status is RunStatus.CANCELLED
    assert harness.runs.get(run.id) == result
    assert result.stages[0].status is StageStatus.DONE
    assert result.stages[1].status is StageStatus.PENDING
    assert rest[0].calls == []


def test_execute_unknown_run(harness: Harness) -> None:
    with pytest.raises(NotFound):
        execute_run(harness).execute("missing")


def test_stages_missing_from_the_run_record_are_added(harness: Harness) -> None:
    run = started_run(harness)
    harness.runs.save(run.model_copy(update={"stages": ()}))
    result = execute_run(harness).execute(run.id)
    assert [s.stage_id for s in result.stages] == ["script", "render", "package"]
    assert result.status is RunStatus.AWAITING_REVIEW

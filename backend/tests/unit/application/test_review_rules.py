from __future__ import annotations

from datetime import UTC, datetime

from autotube.domain.channels import Privacy
from autotube.domain.quality import ReviewMode, ReviewPolicy
from autotube.domain.run_enums import LogLevel, ReviewDecision, RunStatus, UploadStatus
from autotube.domain.runs import Run
from tests.fixtures.builders import execute_run, finished_run, started_run, target_input
from tests.fixtures.harness import Harness
from tests.fixtures.use_cases import review_run
from tests.unit.application.test_run_races import cancels, scoring_with

AUTO_PUBLISH = ReviewPolicy(mode=ReviewMode.AUTO_WHEN_SCORE_AT_LEAST, auto_publish=True)
HAND_THEN_PUBLISH = ReviewPolicy(auto_publish=True)
REJECT_UNDER_50 = ReviewPolicy(reject_below=50)
TWO_TARGETS = (target_input(variants=("landscape",)), target_input(variants=("short",)))


def messages(run: Run, level: LogLevel | None = None) -> list[str]:
    return [log.message for log in run.logs if level is None or log.level is level]


def test_a_low_score_is_rejected_automatically_with_the_reason(harness: Harness) -> None:
    run = finished_run(harness, settings={"score": 40}, review_policy=REJECT_UNDER_50)
    reason = "Rejected automatically: the score 40.0 is below the auto-reject threshold 50"
    assert run.status is RunStatus.REJECTED and run.score == 40.0
    assert run.review is not None and run.review.decision is ReviewDecision.REJECTED
    assert run.review.notes == reason and run.review.decided_at == harness.clock.now()
    assert run.finished_at == harness.clock.now()
    assert messages(run, LogLevel.WARNING) == [reason]


def test_a_score_at_the_threshold_still_waits_for_review(harness: Harness) -> None:
    run = finished_run(harness, settings={"score": 50}, review_policy=REJECT_UNDER_50)
    assert run.status is RunStatus.AWAITING_REVIEW and run.review is None


def test_a_run_approved_by_score_publishes_at_once(harness: Harness) -> None:
    run = finished_run(harness, review_policy=AUTO_PUBLISH)
    assert run.status is RunStatus.PUBLISHED
    assert [upload.status for upload in run.uploads] == [UploadStatus.DONE]
    assert run.uploads[0].privacy is Privacy.PRIVATE
    assert "Publishing automatically after approval" in messages(run)
    assert len(harness.youtube.uploads) == 1


def test_auto_publish_keeps_kids_content_made_for_kids(harness: Harness) -> None:
    targets = (target_input(made_for_kids=None),)
    run = finished_run(
        harness, pipeline_type="fake_kids", targets=targets, review_policy=AUTO_PUBLISH
    )
    assert run.status is RunStatus.PUBLISHED and run.uploads[0].made_for_kids is True
    assert harness.youtube.uploads[0].made_for_kids is True


def test_approving_by_hand_queues_the_run_for_publishing(harness: Harness) -> None:
    run = finished_run(harness, review_policy=HAND_THEN_PUBLISH)
    assert run.status is RunStatus.AWAITING_REVIEW
    harness.queue.enqueued.clear()
    approved = review_run(harness).execute(run.id, ReviewDecision.APPROVED)
    assert approved.status is RunStatus.APPROVED and harness.queue.enqueued == [run.id]
    published = execute_run(harness).execute(run.id)
    assert published.status is RunStatus.PUBLISHED and harness.youtube.uploads


def test_rejecting_by_hand_never_publishes(harness: Harness) -> None:
    run = finished_run(harness, review_policy=HAND_THEN_PUBLISH)
    harness.queue.enqueued.clear()
    rejected = review_run(harness).execute(run.id, ReviewDecision.REJECTED)
    assert rejected.status is RunStatus.REJECTED and harness.queue.enqueued == []
    assert execute_run(harness).execute(run.id).status is RunStatus.REJECTED


def test_without_auto_publish_approval_does_not_publish(harness: Harness) -> None:
    run = finished_run(harness)
    harness.queue.enqueued.clear()
    review_run(harness).execute(run.id, ReviewDecision.APPROVED)
    assert harness.queue.enqueued == []
    assert execute_run(harness).execute(run.id).status is RunStatus.APPROVED
    assert harness.youtube.uploads == []


def test_an_auto_publish_that_cannot_start_leaves_the_run_approved(harness: Harness) -> None:
    run = finished_run(harness, targets=(), review_policy=AUTO_PUBLISH)
    assert run.status is RunStatus.APPROVED
    assert messages(run, LogLevel.WARNING) == [
        f"Auto-publish stopped: run {run.id} has no publishable target"
    ]


def test_an_auto_publish_for_a_deleted_run_returns_the_last_known_run(harness: Harness) -> None:
    run = started_run(harness, review_policy=AUTO_PUBLISH)
    approved = run.model_copy(update={"status": RunStatus.APPROVED})
    harness.runs.delete(run.id)
    assert harness.auto_publish.after_approval(approved) == approved


def test_approving_by_hand_publishes_at_the_target_time_of_day(harness: Harness) -> None:
    timed = target_input(privacy=Privacy.PUBLIC, publish_time_of_day="18:00")
    run = finished_run(harness, targets=(timed,), review_policy=HAND_THEN_PUBLISH)
    review_run(harness).execute(run.id, ReviewDecision.APPROVED)
    published = execute_run(harness).execute(run.id)
    six_pm = datetime(2026, 1, 5, 18, tzinfo=UTC)
    assert published.status is RunStatus.PUBLISHED and published.uploads[0].publish_at == six_pm
    assert harness.youtube.uploads[0].publish_at == six_pm


def test_auto_publish_with_one_failing_target_still_publishes(harness: Harness) -> None:
    harness.youtube.failing_videos = {"en-short.mp4"}
    run = finished_run(harness, targets=TWO_TARGETS, review_policy=AUTO_PUBLISH)
    assert run.status is RunStatus.PUBLISHED
    assert [upload.status for upload in run.uploads] == [UploadStatus.DONE, UploadStatus.FAILED]


def test_auto_publish_with_every_target_failing_stays_approved(harness: Harness) -> None:
    harness.youtube.failing_videos = {"en-landscape.mp4", "en-short.mp4"}
    run = finished_run(harness, targets=TWO_TARGETS, review_policy=AUTO_PUBLISH)
    assert run.status is RunStatus.APPROVED
    assert messages(run, LogLevel.WARNING)[-1] == "Auto-publish stopped: no upload succeeded"


def test_an_auto_rejected_run_never_auto_publishes(harness: Harness) -> None:
    policy = ReviewPolicy(reject_below=50, auto_publish=True)
    run = finished_run(harness, settings={"score": 40}, review_policy=policy)
    assert run.status is RunStatus.REJECTED and run.uploads == ()
    assert harness.youtube.uploads == []


def test_a_run_cancelled_while_scoring_is_not_rejected(harness: Harness) -> None:
    scoring_with(harness, cancels(harness))
    run = finished_run(harness, settings={"score": 40}, review_policy=REJECT_UNDER_50)
    assert run.status is RunStatus.CANCELLED and run.review is None
    assert messages(run, LogLevel.WARNING) == []

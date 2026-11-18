from __future__ import annotations

from typing import Any

from automator.application.cancel_run import CancelRun
from automator.application.clean_up_storage import CleanUpStorage
from automator.application.cleanup_planner import CleanupPlanner
from automator.application.complete_channel_connect import CompleteChannelConnect
from automator.application.delete_channel import DeleteChannel
from automator.application.delete_credential import DeleteCredential
from automator.application.delete_run import DeleteRun
from automator.application.get_dashboard import GetDashboard
from automator.application.get_storage import GetStorage
from automator.application.list_channel_playlists import ListChannelPlaylists
from automator.application.preview_cleanup import PreviewCleanup
from automator.application.publish_run import PublishRun
from automator.application.recover_interrupted_runs import RecoverInterruptedRuns
from automator.application.retry_run import RetryRun
from automator.application.review_run import ReviewRun
from automator.application.run_due_automations import RunDueAutomations
from automator.application.start_channel_connect import StartChannelConnect
from automator.application.update_automation import UpdateAutomation
from automator.domain.run_enums import ReviewDecision
from automator.domain.runs import Run
from tests.fixtures.builders import finished_run
from tests.fixtures.harness import Harness


def start_connect(h: Harness) -> StartChannelConnect:
    return StartChannelConnect(h.credentials, h.authorizer, h.youtube, h.ids, h.clock)


def complete_connect(h: Harness) -> CompleteChannelConnect:
    return CompleteChannelConnect(
        h.credentials, h.channels, h.authorizer, h.secrets, h.youtube, h.ids, h.clock
    )


def retry_run(h: Harness) -> RetryRun:
    return RetryRun(h.runs, h.store, h.progress, h.queue)


def recover_runs(h: Harness) -> RecoverInterruptedRuns:
    return RecoverInterruptedRuns(h.runs, h.recorder, h.progress, h.queue, h.clock)


def cancel_run(h: Harness) -> CancelRun:
    return CancelRun(h.runs, h.progress, h.queue)


def review_run(h: Harness) -> ReviewRun:
    return ReviewRun(h.runs, h.progress, h.clock)


def delete_run(h: Harness) -> DeleteRun:
    return DeleteRun(h.runs, h.store)


def publish_run(h: Harness) -> PublishRun:
    return PublishRun(
        h.runs,
        h.automations,
        h.channels,
        h.credentials,
        h.pipelines,
        h.quota_report,
        h.performer,
        h.recorder,
        h.progress,
        h.clock,
    )


def get_dashboard(h: Harness) -> GetDashboard:
    return GetDashboard(
        h.automations, h.channels, h.credentials, h.runs, h.app_settings, h.quota_report, h.clock
    )


def run_due(h: Harness) -> RunDueAutomations:
    return RunDueAutomations(h.automations, h.presenter, h.start_run)


def update_automation(h: Harness) -> UpdateAutomation:
    return UpdateAutomation(h.automations, h.builder, h.presenter, h.clock)


def delete_channel(h: Harness) -> DeleteChannel:
    return DeleteChannel(h.channels, h.automations, h.secrets)


def delete_credential(h: Harness) -> DeleteCredential:
    return DeleteCredential(h.credentials, h.channels, h.secrets)


def list_playlists(h: Harness) -> ListChannelPlaylists:
    return ListChannelPlaylists(h.channels, h.authorizer, h.youtube, h.expiry)


def approved_run(h: Harness, **overrides: Any) -> Run:
    run = finished_run(h, **overrides)
    return review_run(h).execute(run.id, ReviewDecision.APPROVED)


def failed_at_render(h: Harness) -> Run:
    return finished_run(h, settings={"fail_stage": "render"})


def cleanup_planner(h: Harness) -> CleanupPlanner:
    return CleanupPlanner(h.runs, h.files, h.app_settings, h.clock, h.automations)


def clean_up(h: Harness) -> CleanUpStorage:
    return CleanUpStorage(cleanup_planner(h), h.runs, h.files, h.recorder)


def preview_cleanup(h: Harness) -> PreviewCleanup:
    return PreviewCleanup(cleanup_planner(h))


def get_storage(h: Harness) -> GetStorage:
    return GetStorage(cleanup_planner(h), h.files)

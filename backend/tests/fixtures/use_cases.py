from __future__ import annotations

from automator.application.cancel_run import CancelRun
from automator.application.complete_channel_connect import CompleteChannelConnect
from automator.application.delete_run import DeleteRun
from automator.application.get_dashboard import GetDashboard
from automator.application.publish_run import PublishRun
from automator.application.retry_run import RetryRun
from automator.application.review_run import ReviewRun
from automator.application.run_due_automations import RunDueAutomations
from automator.application.start_channel_connect import StartChannelConnect
from tests.fixtures.harness import Harness


def start_connect(h: Harness) -> StartChannelConnect:
    return StartChannelConnect(h.credentials, h.authorizer, h.youtube, h.ids, h.clock)


def complete_connect(h: Harness) -> CompleteChannelConnect:
    return CompleteChannelConnect(
        h.credentials, h.channels, h.authorizer, h.secrets, h.youtube, h.ids, h.clock
    )


def retry_run(h: Harness) -> RetryRun:
    return RetryRun(h.runs, h.store, h.progress, h.queue)


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

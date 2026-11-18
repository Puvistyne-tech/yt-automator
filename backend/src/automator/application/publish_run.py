from __future__ import annotations

from dataclasses import dataclass

from automator.application.lookups import descriptor_of, require_credential, require_run
from automator.application.quota_report import QuotaReport
from automator.application.run_progress import RunProgress
from automator.application.run_recorder import RunRecorder
from automator.application.upload_performer import UploadPerformer
from automator.domain.automations import Automation
from automator.domain.ports import (
    AutomationRepository,
    ChannelRepository,
    Clock,
    CredentialRepository,
    PipelineRegistry,
    RunRepository,
)
from automator.domain.publish_plan import UploadPlan, plan_uploads, quota_needed
from automator.domain.quota import quota_shortfalls
from automator.domain.run_enums import RunStatus, UploadStatus
from automator.domain.run_state import ensure_transition
from automator.domain.runs import Run
from automator.shared.errors import RuleConflict


@dataclass(frozen=True)
class PublishRun:
    runs: RunRepository
    automations: AutomationRepository
    channels: ChannelRepository
    credentials: CredentialRepository
    pipelines: PipelineRegistry
    quota_report: QuotaReport
    performer: UploadPerformer
    recorder: RunRecorder
    progress: RunProgress
    clock: Clock

    def execute(self, run_id: str) -> Run:
        run = require_run(self.runs, run_id)
        ensure_transition(run, RunStatus.PUBLISHING)
        plans = self.plans(run)
        self.ensure_quota(plans)
        uploads = tuple(plan.initial_upload() for plan in plans)
        run = self.progress.move(run.model_copy(update={"uploads": uploads}), RunStatus.PUBLISHING)
        for index, plan in enumerate(plans):
            if plan.skip_reason is None:
                uploading = run.uploads[index].model_copy(update={"status": UploadStatus.UPLOADING})
                run = self.recorder.upload(run, index, uploading)
                run = self.recorder.upload(run, index, self.performer.perform(run.id, plan))
        return self.concluded(run)

    def automation(self, run: Run) -> Automation:
        automation = self.automations.get(run.automation_id)
        if automation is None:
            raise RuleConflict(
                "automation_deleted", f"automation {run.automation_id} no longer exists"
            )
        return automation

    def plans(self, run: Run) -> list[UploadPlan]:
        automation = self.automation(run)
        descriptor = descriptor_of(self.pipelines.get(run.pipeline_type))
        channels = {channel.id: channel for channel in self.channels.list()}
        plans = plan_uploads(run, automation.targets, channels, descriptor, self.clock.now())
        if not any(plan.skip_reason is None for plan in plans):
            raise RuleConflict("nothing_to_publish", f"run {run.id} has no publishable target")
        return plans

    def ensure_quota(self, plans: list[UploadPlan]) -> None:
        needed = quota_needed(plans, self.quota_report.policy)
        usage = {
            credential_id: self.quota_report.usage(
                require_credential(self.credentials, credential_id)
            )
            for credential_id in needed
        }
        shortfalls = quota_shortfalls(needed, usage)
        if shortfalls:
            detail = ", ".join(
                f"{s.credential_id} needs {s.needed} units, {s.remaining} left" for s in shortfalls
            )
            raise RuleConflict("quota_exceeded", f"daily quota too low: {detail}")

    def concluded(self, run: Run) -> Run:
        statuses = [upload.status for upload in run.uploads]
        done = UploadStatus.DONE in statuses
        pending = any(s in (UploadStatus.PENDING, UploadStatus.UPLOADING) for s in statuses)
        if done and not pending:
            return self.progress.move(run, RunStatus.PUBLISHED)
        return self.progress.move(run, RunStatus.APPROVED, "no upload succeeded")

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

from automator.application.lookups import require_automation
from automator.application.run_recorder import RunRecorder
from automator.domain.automations import Automation
from automator.domain.pipeline import pipeline_not_installed
from automator.domain.ports import (
    AutomationRepository,
    Clock,
    IdGenerator,
    PipelineRegistry,
    RunQueue,
)
from automator.domain.run_enums import RunTrigger
from automator.domain.run_parts import StageRun
from automator.domain.runs import Run
from automator.shared.errors import RuleConflict


@dataclass(frozen=True)
class StartRun:
    automations: AutomationRepository
    pipelines: PipelineRegistry
    recorder: RunRecorder
    queue: RunQueue
    ids: IdGenerator
    clock: Clock

    def execute(self, automation_id: str, trigger: RunTrigger = RunTrigger.MANUAL) -> Run:
        automation = require_automation(self.automations, automation_id)
        run = self.recorder.created(self.new_run(automation, trigger))
        self.queue.enqueue(run.id)
        return run

    def new_run(self, automation: Automation, trigger: RunTrigger) -> Run:
        pipeline = self.pipelines.get(automation.pipeline_type)
        if pipeline is None:
            raise RuleConflict(
                "pipeline_unavailable", pipeline_not_installed(automation.pipeline_type)
            )
        stages = tuple(
            StageRun(stage_id=stage.descriptor.id, title=stage.descriptor.title)
            for stage in pipeline.stages()
        )
        return Run(
            id=self.ids.new(),
            automation_id=automation.id,
            automation_name=automation.name,
            pipeline_type=automation.pipeline_type,
            trigger=trigger,
            languages=automation.languages,
            settings_snapshot=deepcopy(automation.settings),
            review_policy=automation.review_policy,
            stages=stages,
            created_at=self.clock.now(),
        )

from __future__ import annotations

from dataclasses import dataclass
from functools import partial

from pydantic import BaseModel

from automator.application.lookups import require
from automator.application.run_progress import RunProgress
from automator.application.run_recorder import RunRecorder
from automator.application.stage_runner import ContextFactory, StageRunner
from automator.domain.pipeline import Pipeline, ProviderResolver, StageContext
from automator.domain.ports import (
    ArtifactStore,
    AutomationRepository,
    PipelineRegistry,
    ProviderCatalog,
    ProviderConfigRepository,
    RunRepository,
)
from automator.domain.quality import ReviewPolicy, status_after_scoring, weighted_score
from automator.domain.run_enums import RunStatus
from automator.domain.runs import Run
from automator.domain.validation import validated_settings


@dataclass(frozen=True)
class ExecuteRun:
    runs: RunRepository
    automations: AutomationRepository
    pipelines: PipelineRegistry
    provider_configs: ProviderConfigRepository
    catalog: ProviderCatalog
    store: ArtifactStore
    recorder: RunRecorder
    progress: RunProgress
    stage_runner: StageRunner

    def execute(self, run_id: str) -> Run:
        run = require(self.runs.get(run_id), "run", run_id)
        if run.status is not RunStatus.QUEUED:
            return run
        pipeline = self.pipelines.get(run.pipeline_type)
        if pipeline is None:
            return self.progress.fail(run, f"pipeline {run.pipeline_type!r} is not installed")
        settings, errors = validated_settings(pipeline.settings_model, run.settings_snapshot)
        if settings is None:
            return self.progress.fail(run, f"settings are invalid: {errors}")
        run = self.progress.move(run, RunStatus.RUNNING)
        providers = self.catalog.resolver(self.provider_configs.list())
        return self.run_stages(run, pipeline, partial(self.context, settings, providers))

    def context(self, settings: BaseModel, providers: ProviderResolver, run: Run) -> StageContext:
        return StageContext(
            run_id=run.id,
            settings=settings,
            languages=run.languages,
            workspace=self.store.workspace(run.id),
            artifacts=run.artifacts,
            providers=providers,
            log=partial(self.recorder.log, run.id),
        )

    def run_stages(self, run: Run, pipeline: Pipeline, context_for: ContextFactory) -> Run:
        for stage in pipeline.stages():
            run = self.progress.synced(run)
            if run.status is not RunStatus.RUNNING:
                return run
            run = self.stage_runner.run(run, stage, context_for)
        run = self.progress.synced(run)
        if run.status is not RunStatus.RUNNING:
            return run
        return self.scored(run, pipeline, context_for(run))

    def scored(self, run: Run, pipeline: Pipeline, context: StageContext) -> Run:
        try:
            items = tuple(pipeline.score(context))
        except Exception as error:
            return self.progress.fail(run, f"scoring failed: {error}")
        score = weighted_score(items)
        run = run.model_copy(update={"score": score, "score_details": items})
        return self.progress.move(run, status_after_scoring(self.review_policy(run), score))

    def review_policy(self, run: Run) -> ReviewPolicy:
        automation = self.automations.get(run.automation_id)
        return automation.review_policy if automation is not None else ReviewPolicy()

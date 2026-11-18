from __future__ import annotations

from dataclasses import dataclass
from functools import partial

from pydantic import BaseModel

from automator.application.lookups import require_run
from automator.application.run_progress import RunProgress
from automator.application.run_recorder import RunRecorder
from automator.application.stage_runner import ContextFactory, StageRunner
from automator.domain.pipeline import (
    Pipeline,
    ProviderResolver,
    StageContext,
    pipeline_not_installed,
)
from automator.domain.ports import (
    ArtifactStore,
    PipelineRegistry,
    ProviderCatalog,
    ProviderConfigRepository,
    RunRepository,
)
from automator.domain.quality import status_after_scoring, weighted_score
from automator.domain.run_enums import RunStatus
from automator.domain.runs import Run
from automator.domain.validation import validated_settings
from automator.shared.errors import describe_error


@dataclass(frozen=True)
class ExecuteRun:
    runs: RunRepository
    pipelines: PipelineRegistry
    provider_configs: ProviderConfigRepository
    catalog: ProviderCatalog
    store: ArtifactStore
    recorder: RunRecorder
    progress: RunProgress
    stage_runner: StageRunner

    def execute(self, run_id: str) -> Run:
        run = require_run(self.runs, run_id)
        if run.status is not RunStatus.QUEUED:
            return run
        pipeline = self.pipelines.get(run.pipeline_type)
        if pipeline is None:
            return self.settled(
                run, self.progress.fail(run, pipeline_not_installed(run.pipeline_type))
            )
        settings, errors = validated_settings(pipeline.settings_model, run.settings_snapshot)
        if settings is None:
            return self.settled(run, self.progress.fail(run, f"settings are invalid: {errors}"))
        running = self.progress.advance(run, RunStatus.RUNNING)
        if running is None:
            return self.progress.synced(run)
        run = running
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
            failure = f"scoring failed: {describe_error(error)}"
            return self.settled(run, self.progress.fail(run, failure))
        score = weighted_score(items)
        status = status_after_scoring(run.review_policy, score)
        scores = {"score": score, "score_details": items}
        return self.settled(run, self.progress.advance(run, status, updates=scores))

    def settled(self, run: Run, result: Run | None) -> Run:
        return result if result is not None else self.progress.synced(run)

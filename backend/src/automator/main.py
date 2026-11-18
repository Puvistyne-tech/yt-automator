from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from automator.api.app import build_api
from automator.api.container import ApiOptions, UseCases
from automator.api.spa import mount_web_ui
from automator.application.run_doctor import RunDoctor
from automator.composition.ports import Ports
from automator.composition.use_cases import build_use_cases
from automator.domain.ports import (
    Clock,
    IdGenerator,
    PipelineRegistry,
    ProviderCatalog,
    RunEvents,
    SecretStore,
    YouTubeGateway,
)
from automator.domain.run_parts import RunLogPolicy
from automator.infrastructure.config import RuntimeConfig, load_config
from automator.infrastructure.db.database import Database
from automator.infrastructure.db.entity_repositories import (
    SqlAutomationRepository,
    SqlChannelRepository,
    SqlCredentialRepository,
)
from automator.infrastructure.db.run_repository import SqlRunRepository
from automator.infrastructure.db.settings_repositories import (
    SqlAppSettingsRepository,
    SqlProviderConfigRepository,
    SqlQuotaLedger,
)
from automator.infrastructure.diagnostics.system_inspector import build_system_inspector
from automator.infrastructure.providers.catalog import build_provider_catalog
from automator.infrastructure.runtime.events import InProcessRunEvents
from automator.infrastructure.runtime.scheduler import SchedulerTicker
from automator.infrastructure.runtime.system import RandomIds, SystemClock, package_version
from automator.infrastructure.runtime.worker_pool import WorkerPoolQueue
from automator.infrastructure.scheduling.schedule_calculator import StandardScheduleCalculator
from automator.infrastructure.secrets.selection import build_secret_store
from automator.infrastructure.storage.artifact_store import FileArtifactStore
from automator.infrastructure.youtube.gateway import GoogleYouTubeGateway
from automator.infrastructure.youtube.settings import youtube_settings
from automator.pipelines.registry import build_pipeline_registry

logger = logging.getLogger("automator")


@dataclass(frozen=True)
class Overrides:
    youtube: YouTubeGateway | None = None
    catalog: ProviderCatalog | None = None
    pipelines: PipelineRegistry | None = None
    secrets: SecretStore | None = None
    clock: Clock | None = None
    ids: IdGenerator | None = None
    events: RunEvents | None = None


@dataclass(frozen=True)
class Runtime:
    config: RuntimeConfig
    database: Database
    ports: Ports
    queue: WorkerPoolQueue
    scheduler: SchedulerTicker
    use_cases: UseCases

    def start(self) -> None:
        report = self.use_cases.runs.recover.execute()
        if report.total():
            logger.info("recovered %d interrupted runs", report.total())
        self.queue.start(self.use_cases.runs.execute.execute)
        self.scheduler.start()

    def stop(self) -> None:
        self.scheduler.stop(self.config.shutdown_timeout_seconds)
        if not self.queue.stop(self.config.shutdown_timeout_seconds):
            logger.warning("some runs were still working at shutdown")
        self.database.dispose()


def youtube_gateway(config: RuntimeConfig) -> GoogleYouTubeGateway:
    return GoogleYouTubeGateway(youtube_settings(config))


def secret_store(config: RuntimeConfig) -> SecretStore:
    return build_secret_store(config.secret_backend, config.data_dir, config.keyring_service)


def build_doctor(environ: Mapping[str, str]) -> RunDoctor:
    config = load_config(environ)
    secrets = secret_store(config)
    catalog = build_provider_catalog(secrets, config.data_dir)
    return RunDoctor(catalog, secrets, build_system_inspector(config), config.doctor_policy)


def build_ports(
    config: RuntimeConfig, database: Database, queue: WorkerPoolQueue, overrides: Overrides
) -> Ports:
    secrets = overrides.secrets or secret_store(config)
    return Ports(
        credentials=SqlCredentialRepository(database),
        channels=SqlChannelRepository(database),
        automations=SqlAutomationRepository(database),
        runs=SqlRunRepository(database),
        provider_configs=SqlProviderConfigRepository(database),
        app_settings=SqlAppSettingsRepository(database, str(config.data_dir)),
        ledger=SqlQuotaLedger(database),
        secrets=secrets,
        clock=overrides.clock or SystemClock(),
        ids=overrides.ids or RandomIds(),
        schedules=StandardScheduleCalculator(),
        store=FileArtifactStore(config.data_dir),
        queue=queue,
        events=overrides.events or InProcessRunEvents(config.event_queue_size),
        pipelines=overrides.pipelines or build_pipeline_registry(),
        catalog=overrides.catalog or build_provider_catalog(secrets, config.data_dir),
        youtube=overrides.youtube or youtube_gateway(config),
        inspector=build_system_inspector(config),
        run_logs=RunLogPolicy(max_entries=config.max_run_log_entries),
        doctor_policy=config.doctor_policy,
    )


def build_runtime(config: RuntimeConfig, overrides: Overrides) -> Runtime:
    database = Database(config.database_path, config.database_busy_timeout_ms)
    database.migrate()
    settings = SqlAppSettingsRepository(database, str(config.data_dir))
    queue = WorkerPoolQueue(lambda: settings.get().max_parallel_runs, config.worker_poll_seconds)
    ports = build_ports(config, database, queue, overrides)
    use_cases = build_use_cases(ports)
    scheduler = SchedulerTicker(
        use_cases.automations.run_due.execute, ports.clock, config.scheduler_tick_seconds
    )
    return Runtime(config, database, ports, queue, scheduler, use_cases)


def create_app(config: RuntimeConfig, overrides: Overrides | None = None) -> FastAPI:
    runtime = build_runtime(config, overrides or Overrides())

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        runtime.start()
        try:
            yield
        finally:
            runtime.stop()

    options = ApiOptions(
        version=package_version(),
        ui_base_url=config.ui_base_url,
        sse_heartbeat_seconds=config.sse_heartbeat_seconds,
        max_run_list_limit=config.max_run_list_limit,
    )
    app = build_api(runtime.use_cases, options, lifespan)
    app.state.runtime = runtime
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    mount_web_ui(app, config.web_dist_dir)
    return app


def app_from_environment() -> FastAPI:
    return create_app(load_config(os.environ))


def main() -> None:
    config = load_config(os.environ)
    logging.basicConfig(level=config.log_level.upper())
    uvicorn.run(
        "automator.main:app_from_environment",
        factory=True,
        host=config.host,
        port=config.port,
        reload=config.reload,
        log_level=config.log_level,
    )


if __name__ == "__main__":
    main()

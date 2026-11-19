from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from autotube.api.app import build_api
from autotube.api.container import ApiOptions, UseCases
from autotube.api.spa import mount_web_ui
from autotube.application.run_doctor import RunDoctor
from autotube.composition.overrides import Overrides as Overrides
from autotube.composition.ports import Ports
from autotube.composition.use_cases import build_use_cases
from autotube.domain.ports import AppSettingsRepository, SecretStore
from autotube.infrastructure.config import RuntimeConfig, load_config
from autotube.infrastructure.db.database import Database
from autotube.infrastructure.db.entity_repositories import (
    SqlAutomationRepository,
    SqlChannelRepository,
    SqlCredentialRepository,
)
from autotube.infrastructure.db.run_repository import SqlRunRepository
from autotube.infrastructure.db.settings_repositories import (
    SqlAppSettingsRepository,
    SqlProviderConfigRepository,
    SqlQuotaLedger,
)
from autotube.infrastructure.db.template_repository import SqlTemplateRepository
from autotube.infrastructure.diagnostics.setup_defaults import setup_defaults as setup_defaults
from autotube.infrastructure.diagnostics.system_inspector import build_system_inspector
from autotube.infrastructure.pipelines.engine_catalog import InstalledEngineCatalog
from autotube.infrastructure.pipelines.template_registry import TemplatePipelineRegistry
from autotube.infrastructure.providers.catalog import build_provider_catalog
from autotube.infrastructure.runtime.events import InProcessRunEvents
from autotube.infrastructure.runtime.scheduler import SchedulerTicker
from autotube.infrastructure.runtime.system import RandomIds, SystemClock, package_version
from autotube.infrastructure.runtime.worker_pool import WorkerPoolQueue
from autotube.infrastructure.scheduling.schedule_calculator import StandardScheduleCalculator
from autotube.infrastructure.secrets.selection import build_secret_store
from autotube.infrastructure.settings_env import settings_overrides
from autotube.infrastructure.storage.artifact_store import FileArtifactStore
from autotube.infrastructure.storage.run_storage import FileRunStorage
from autotube.infrastructure.youtube.gateway import GoogleYouTubeGateway
from autotube.infrastructure.youtube.settings import youtube_settings
from autotube.pipelines.registry import installed_engines, installed_pipelines

logger = logging.getLogger("autotube")


@dataclass(frozen=True)
class Runtime:
    config: RuntimeConfig
    database: Database
    ports: Ports
    queue: WorkerPoolQueue
    scheduler: SchedulerTicker
    use_cases: UseCases

    def start(self) -> None:
        logger.setLevel(self.ports.app_settings.get().log_level.upper())
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


def youtube_gateway(
    config: RuntimeConfig, settings: AppSettingsRepository | None = None
) -> GoogleYouTubeGateway:
    name = (lambda: settings.get().caption_track_name) if settings is not None else None
    return GoogleYouTubeGateway(youtube_settings(config), caption_name=name)


def secret_store(config: RuntimeConfig) -> SecretStore:
    return build_secret_store(config.secret_backend, config.data_dir, config.keyring_service)


def build_doctor(environ: Mapping[str, str]) -> RunDoctor:
    config = load_config(environ)
    secrets = secret_store(config)
    catalog = build_provider_catalog(secrets, config.data_dir)
    return RunDoctor(catalog, secrets, build_system_inspector(config), lambda: config.doctor_policy)


def app_settings(config: RuntimeConfig, database: Database) -> SqlAppSettingsRepository:
    return SqlAppSettingsRepository(database, str(config.data_dir), settings_overrides(config))


def build_ports(
    config: RuntimeConfig, database: Database, queue: WorkerPoolQueue, overrides: Overrides
) -> Ports:
    secrets = overrides.secrets or secret_store(config)
    settings = app_settings(config, database)
    templates = SqlTemplateRepository(database)
    engines = overrides.engines or InstalledEngineCatalog(installed_engines())
    static = installed_pipelines()
    return Ports(
        credentials=SqlCredentialRepository(database),
        channels=SqlChannelRepository(database),
        automations=SqlAutomationRepository(database),
        templates=templates,
        runs=SqlRunRepository(database),
        provider_configs=SqlProviderConfigRepository(database),
        app_settings=settings,
        ledger=SqlQuotaLedger(database),
        secrets=secrets,
        clock=overrides.clock or SystemClock(),
        ids=overrides.ids or RandomIds(),
        schedules=StandardScheduleCalculator(),
        store=FileArtifactStore(config.data_dir),
        files=FileRunStorage(config.data_dir),
        queue=queue,
        events=overrides.events or InProcessRunEvents(config.event_queue_size),
        pipelines=overrides.pipelines
        or TemplatePipelineRegistry(static, engines.list(), templates),
        engines=engines,
        catalog=overrides.catalog or build_provider_catalog(secrets, config.data_dir),
        youtube=overrides.youtube or youtube_gateway(config, settings),
        inspector=overrides.inspector or build_system_inspector(config),
        doctor_policy=config.doctor_policy,
    )


def build_runtime(config: RuntimeConfig, overrides: Overrides) -> Runtime:
    database = Database(config.database_path, config.database_busy_timeout_ms)
    database.migrate()
    settings = app_settings(config, database)
    queue = WorkerPoolQueue(lambda: settings.get().max_parallel_runs, config.worker_poll_seconds)
    ports = build_ports(config, database, queue, overrides)
    use_cases = build_use_cases(ports)
    ticks = (use_cases.automations.scheduler.execute, use_cases.storage.scheduled_cleanup.execute)
    scheduler = SchedulerTicker(ticks, ports.clock, config.scheduler_tick_seconds)
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
        "autotube.main:app_from_environment",
        factory=True,
        host=config.host,
        port=config.port,
        reload=config.reload,
        log_level=config.log_level.value,
    )


if __name__ == "__main__":
    main()

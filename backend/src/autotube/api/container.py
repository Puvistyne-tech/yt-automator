from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from autotube.application.cancel_run import CancelRun
from autotube.application.clean_up_storage import CleanUpStorage
from autotube.application.complete_channel_connect import CompleteChannelConnect
from autotube.application.create_automation import CreateAutomation
from autotube.application.create_credential import CreateCredential
from autotube.application.create_template import CreateTemplate
from autotube.application.delete_automation import DeleteAutomation
from autotube.application.delete_channel import DeleteChannel
from autotube.application.delete_credential import DeleteCredential
from autotube.application.delete_run import DeleteRun
from autotube.application.delete_secret import DeleteSecret
from autotube.application.delete_template import DeleteTemplate
from autotube.application.duplicate_automation import DuplicateAutomation
from autotube.application.duplicate_template import DuplicateTemplate
from autotube.application.execute_run import ExecuteRun
from autotube.application.export_automation import ExportAutomation
from autotube.application.get_automation import GetAutomation
from autotube.application.get_dashboard import GetDashboard
from autotube.application.get_pipeline import GetPipeline
from autotube.application.get_providers import GetProviders
from autotube.application.get_run import GetRun
from autotube.application.get_settings import GetSettings
from autotube.application.get_storage import GetStorage
from autotube.application.get_template import GetTemplate
from autotube.application.import_automation import ImportAutomation
from autotube.application.list_automations import ListAutomations
from autotube.application.list_channel_playlists import ListChannelPlaylists
from autotube.application.list_channels import ListChannels
from autotube.application.list_credentials import ListCredentials
from autotube.application.list_pipelines import ListPipelines
from autotube.application.list_runs import ListRuns
from autotube.application.list_secrets import ListSecrets
from autotube.application.list_template_engines import ListTemplateEngines
from autotube.application.list_templates import ListTemplates
from autotube.application.open_run_artifact import OpenRunArtifact
from autotube.application.preview_cleanup import PreviewCleanup
from autotube.application.publish_run import PublishRun
from autotube.application.recover_interrupted_runs import RecoverInterruptedRuns
from autotube.application.retry_run import RetryRun
from autotube.application.review_run import ReviewRun
from autotube.application.run_doctor import RunDoctor
from autotube.application.save_provider_config import SaveProviderConfig
from autotube.application.save_settings import SaveSettings
from autotube.application.scheduled_cleanup import ScheduledCleanup
from autotube.application.scheduler_tick import SchedulerTick
from autotube.application.set_automation_enabled import SetAutomationEnabled
from autotube.application.set_secret import SetSecret
from autotube.application.start_channel_connect import StartChannelConnect
from autotube.application.start_run import StartRun
from autotube.application.update_automation import UpdateAutomation
from autotube.application.update_channel_defaults import UpdateChannelDefaults
from autotube.application.update_credential import UpdateCredential
from autotube.application.update_template import UpdateTemplate
from autotube.domain.ports import RunEvents


@dataclass(frozen=True)
class ApiOptions:
    version: str
    ui_base_url: str
    sse_heartbeat_seconds: float
    max_run_list_limit: int


@dataclass(frozen=True)
class ChannelUseCases:
    list_credentials: ListCredentials
    create_credential: CreateCredential
    update_credential: UpdateCredential
    delete_credential: DeleteCredential
    list_channels: ListChannels
    start_connect: StartChannelConnect
    complete_connect: CompleteChannelConnect
    update_defaults: UpdateChannelDefaults
    delete_channel: DeleteChannel
    list_playlists: ListChannelPlaylists


@dataclass(frozen=True)
class AutomationUseCases:
    list_automations: ListAutomations
    create: CreateAutomation
    get: GetAutomation
    update: UpdateAutomation
    set_enabled: SetAutomationEnabled
    delete: DeleteAutomation
    duplicate: DuplicateAutomation
    export: ExportAutomation
    import_automation: ImportAutomation
    start_run: StartRun
    scheduler: SchedulerTick


@dataclass(frozen=True)
class RunUseCases:
    list_runs: ListRuns
    get: GetRun
    retry: RetryRun
    cancel: CancelRun
    review: ReviewRun
    publish: PublishRun
    delete: DeleteRun
    open_artifact: OpenRunArtifact
    execute: ExecuteRun
    recover: RecoverInterruptedRuns


@dataclass(frozen=True)
class ConfigUseCases:
    get_dashboard: GetDashboard
    list_pipelines: ListPipelines
    get_pipeline: GetPipeline
    get_providers: GetProviders
    save_providers: SaveProviderConfig
    list_secrets: ListSecrets
    set_secret: SetSecret
    delete_secret: DeleteSecret
    get_settings: GetSettings
    save_settings: SaveSettings
    doctor: RunDoctor


@dataclass(frozen=True)
class StorageUseCases:
    get_storage: GetStorage
    preview_cleanup: PreviewCleanup
    clean_up: CleanUpStorage
    scheduled_cleanup: ScheduledCleanup


@dataclass(frozen=True)
class TemplateUseCases:
    list_engines: ListTemplateEngines
    list_templates: ListTemplates
    get: GetTemplate
    create: CreateTemplate
    update: UpdateTemplate
    delete: DeleteTemplate
    duplicate: DuplicateTemplate


@dataclass(frozen=True)
class UseCases:
    channels: ChannelUseCases
    automations: AutomationUseCases
    runs: RunUseCases
    config: ConfigUseCases
    storage: StorageUseCases
    templates: TemplateUseCases
    events: RunEvents


def current_use_cases(request: Request) -> UseCases:
    use_cases: UseCases = request.app.state.use_cases
    return use_cases


def current_options(request: Request) -> ApiOptions:
    options: ApiOptions = request.app.state.options
    return options


App = Annotated[UseCases, Depends(current_use_cases)]
Options = Annotated[ApiOptions, Depends(current_options)]

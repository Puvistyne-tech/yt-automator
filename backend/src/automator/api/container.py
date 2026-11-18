from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from automator.application.cancel_run import CancelRun
from automator.application.clean_up_storage import CleanUpStorage
from automator.application.complete_channel_connect import CompleteChannelConnect
from automator.application.create_automation import CreateAutomation
from automator.application.create_credential import CreateCredential
from automator.application.delete_automation import DeleteAutomation
from automator.application.delete_channel import DeleteChannel
from automator.application.delete_credential import DeleteCredential
from automator.application.delete_run import DeleteRun
from automator.application.delete_secret import DeleteSecret
from automator.application.duplicate_automation import DuplicateAutomation
from automator.application.execute_run import ExecuteRun
from automator.application.get_automation import GetAutomation
from automator.application.get_dashboard import GetDashboard
from automator.application.get_pipeline import GetPipeline
from automator.application.get_providers import GetProviders
from automator.application.get_run import GetRun
from automator.application.get_settings import GetSettings
from automator.application.get_storage import GetStorage
from automator.application.list_automations import ListAutomations
from automator.application.list_channel_playlists import ListChannelPlaylists
from automator.application.list_channels import ListChannels
from automator.application.list_credentials import ListCredentials
from automator.application.list_pipelines import ListPipelines
from automator.application.list_runs import ListRuns
from automator.application.list_secrets import ListSecrets
from automator.application.open_run_artifact import OpenRunArtifact
from automator.application.preview_cleanup import PreviewCleanup
from automator.application.publish_run import PublishRun
from automator.application.recover_interrupted_runs import RecoverInterruptedRuns
from automator.application.retry_run import RetryRun
from automator.application.review_run import ReviewRun
from automator.application.run_doctor import RunDoctor
from automator.application.save_provider_config import SaveProviderConfig
from automator.application.save_settings import SaveSettings
from automator.application.scheduled_cleanup import ScheduledCleanup
from automator.application.scheduler_tick import SchedulerTick
from automator.application.set_automation_enabled import SetAutomationEnabled
from automator.application.set_secret import SetSecret
from automator.application.start_channel_connect import StartChannelConnect
from automator.application.start_run import StartRun
from automator.application.update_automation import UpdateAutomation
from automator.application.update_channel_defaults import UpdateChannelDefaults
from automator.application.update_credential import UpdateCredential
from automator.domain.ports import RunEvents


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
class UseCases:
    channels: ChannelUseCases
    automations: AutomationUseCases
    runs: RunUseCases
    config: ConfigUseCases
    storage: StorageUseCases
    events: RunEvents


def current_use_cases(request: Request) -> UseCases:
    use_cases: UseCases = request.app.state.use_cases
    return use_cases


def current_options(request: Request) -> ApiOptions:
    options: ApiOptions = request.app.state.options
    return options


App = Annotated[UseCases, Depends(current_use_cases)]
Options = Annotated[ApiOptions, Depends(current_options)]

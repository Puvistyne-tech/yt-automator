from __future__ import annotations

from automator.api.container import (
    AutomationUseCases,
    ChannelUseCases,
    ConfigUseCases,
    RunUseCases,
    UseCases,
)
from automator.application.cancel_run import CancelRun
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
from automator.application.list_automations import ListAutomations
from automator.application.list_channel_playlists import ListChannelPlaylists
from automator.application.list_channels import ListChannels
from automator.application.list_credentials import ListCredentials
from automator.application.list_pipelines import ListPipelines
from automator.application.list_runs import ListRuns
from automator.application.list_secrets import ListSecrets
from automator.application.open_run_artifact import OpenRunArtifact
from automator.application.publish_run import PublishRun
from automator.application.recover_interrupted_runs import RecoverInterruptedRuns
from automator.application.retry_run import RetryRun
from automator.application.review_run import ReviewRun
from automator.application.run_doctor import RunDoctor
from automator.application.run_due_automations import RunDueAutomations
from automator.application.save_provider_config import SaveProviderConfig
from automator.application.save_settings import SaveSettings
from automator.application.set_automation_enabled import SetAutomationEnabled
from automator.application.set_secret import SetSecret
from automator.application.stage_runner import StageRunner
from automator.application.start_channel_connect import StartChannelConnect
from automator.application.start_run import StartRun
from automator.application.update_automation import UpdateAutomation
from automator.application.update_channel_defaults import UpdateChannelDefaults
from automator.application.update_credential import UpdateCredential
from automator.application.upload_performer import UploadPerformer
from automator.composition.ports import (
    Collaborators,
    Ports,
    collaborators,
    current_doctor_policy,
)
from automator.composition.storage import storage_use_cases


def channel_use_cases(p: Ports, c: Collaborators) -> ChannelUseCases:
    return ChannelUseCases(
        list_credentials=ListCredentials(p.credentials, c.credential_views),
        create_credential=CreateCredential(
            p.credentials, p.secrets, p.ids, p.clock, c.credential_views
        ),
        update_credential=UpdateCredential(p.credentials, p.secrets, c.credential_views),
        delete_credential=DeleteCredential(p.credentials, p.channels, p.secrets),
        list_channels=ListChannels(p.channels),
        start_connect=StartChannelConnect(p.credentials, c.authorizer, p.youtube, p.ids, p.clock),
        complete_connect=CompleteChannelConnect(
            p.credentials, p.channels, c.authorizer, p.secrets, p.youtube, p.ids, p.clock
        ),
        update_defaults=UpdateChannelDefaults(p.channels),
        delete_channel=DeleteChannel(p.channels, p.automations, p.secrets),
        list_playlists=ListChannelPlaylists(p.channels, c.authorizer, p.youtube, c.expiry),
    )


def automation_use_cases(p: Ports, c: Collaborators) -> AutomationUseCases:
    starter = StartRun(p.automations, p.pipelines, c.recorder, p.queue, p.ids, p.clock)
    return AutomationUseCases(
        list_automations=ListAutomations(p.automations, c.presenter),
        create=CreateAutomation(p.automations, c.builder, c.presenter, p.ids, p.clock),
        get=GetAutomation(p.automations, c.presenter),
        update=UpdateAutomation(p.automations, c.builder, c.presenter, p.clock),
        set_enabled=SetAutomationEnabled(p.automations, c.presenter, p.clock),
        delete=DeleteAutomation(p.automations),
        duplicate=DuplicateAutomation(p.automations, c.presenter, p.ids, p.clock),
        start_run=starter,
        run_due=RunDueAutomations(p.automations, c.presenter, starter),
    )


def execute_run(p: Ports, c: Collaborators) -> ExecuteRun:
    runner = StageRunner(p.store, c.recorder, c.progress, p.ids, p.clock)
    return ExecuteRun(
        p.runs,
        p.pipelines,
        p.provider_configs,
        p.catalog,
        p.store,
        c.recorder,
        c.progress,
        runner,
    )


def publish_run(p: Ports, c: Collaborators) -> PublishRun:
    performer = UploadPerformer(p.youtube, p.store, c.authorizer, c.quota_report, c.expiry)
    return PublishRun(
        p.runs,
        p.automations,
        p.channels,
        p.credentials,
        p.pipelines,
        c.quota_report,
        performer,
        c.recorder,
        c.progress,
        p.clock,
    )


def run_use_cases(p: Ports, c: Collaborators) -> RunUseCases:
    return RunUseCases(
        list_runs=ListRuns(p.runs),
        get=GetRun(p.runs),
        retry=RetryRun(p.runs, p.store, c.progress, p.queue),
        cancel=CancelRun(p.runs, c.progress, p.queue),
        review=ReviewRun(p.runs, c.progress, p.clock),
        publish=publish_run(p, c),
        delete=DeleteRun(p.runs, p.store),
        open_artifact=OpenRunArtifact(p.runs, p.store),
        execute=execute_run(p, c),
        recover=RecoverInterruptedRuns(p.runs, c.recorder, c.progress, p.queue, p.clock),
    )


def config_use_cases(p: Ports, c: Collaborators) -> ConfigUseCases:
    return ConfigUseCases(
        get_dashboard=GetDashboard(
            p.automations,
            p.channels,
            p.credentials,
            p.runs,
            p.app_settings,
            c.quota_report,
            p.clock,
        ),
        list_pipelines=ListPipelines(p.pipelines),
        get_pipeline=GetPipeline(p.pipelines),
        get_providers=GetProviders(p.catalog, p.provider_configs),
        save_providers=SaveProviderConfig(p.catalog, p.provider_configs),
        list_secrets=ListSecrets(p.catalog, p.secrets),
        set_secret=SetSecret(p.catalog, p.secrets),
        delete_secret=DeleteSecret(p.catalog, p.secrets),
        get_settings=GetSettings(p.app_settings),
        save_settings=SaveSettings(p.app_settings),
        doctor=RunDoctor(p.catalog, p.secrets, p.inspector, lambda: current_doctor_policy(p)),
    )


def build_use_cases(ports: Ports) -> UseCases:
    shared = collaborators(ports)
    return UseCases(
        channels=channel_use_cases(ports, shared),
        automations=automation_use_cases(ports, shared),
        runs=run_use_cases(ports, shared),
        config=config_use_cases(ports, shared),
        storage=storage_use_cases(ports, shared),
        events=ports.events,
    )

from __future__ import annotations

from autotube.api.container import (
    AutomationUseCases,
    ChannelUseCases,
    ConfigUseCases,
    RunUseCases,
    UseCases,
)
from autotube.application.auto_publish import AutoPublish
from autotube.application.cancel_run import CancelRun
from autotube.application.complete_channel_connect import CompleteChannelConnect
from autotube.application.create_automation import CreateAutomation
from autotube.application.create_credential import CreateCredential
from autotube.application.delete_automation import DeleteAutomation
from autotube.application.delete_channel import DeleteChannel
from autotube.application.delete_credential import DeleteCredential
from autotube.application.delete_run import DeleteRun
from autotube.application.delete_secret import DeleteSecret
from autotube.application.duplicate_automation import DuplicateAutomation
from autotube.application.execute_run import ExecuteRun
from autotube.application.export_automation import ExportAutomation
from autotube.application.get_automation import GetAutomation
from autotube.application.get_dashboard import GetDashboard
from autotube.application.get_pipeline import GetPipeline
from autotube.application.get_providers import GetProviders
from autotube.application.get_run import GetRun
from autotube.application.get_settings import GetSettings
from autotube.application.import_automation import ImportAutomation
from autotube.application.list_automations import ListAutomations
from autotube.application.list_channel_playlists import ListChannelPlaylists
from autotube.application.list_channels import ListChannels
from autotube.application.list_credentials import ListCredentials
from autotube.application.list_pipelines import ListPipelines
from autotube.application.list_runs import ListRuns
from autotube.application.list_secrets import ListSecrets
from autotube.application.open_run_artifact import OpenRunArtifact
from autotube.application.publish_run import PublishRun
from autotube.application.recover_interrupted_runs import RecoverInterruptedRuns
from autotube.application.retry_due_runs import RetryDueRuns
from autotube.application.retry_run import RetryRun
from autotube.application.review_run import ReviewRun
from autotube.application.run_doctor import RunDoctor
from autotube.application.run_due_automations import RunDueAutomations
from autotube.application.save_provider_config import SaveProviderConfig
from autotube.application.save_settings import SaveSettings
from autotube.application.scheduler_tick import SchedulerTick
from autotube.application.set_automation_enabled import SetAutomationEnabled
from autotube.application.set_secret import SetSecret
from autotube.application.stage_runner import StageRunner
from autotube.application.start_channel_connect import StartChannelConnect
from autotube.application.start_run import StartRun
from autotube.application.update_automation import UpdateAutomation
from autotube.application.update_channel_defaults import UpdateChannelDefaults
from autotube.application.update_credential import UpdateCredential
from autotube.application.upload_performer import UploadPerformer
from autotube.composition.ports import (
    Collaborators,
    Ports,
    collaborators,
    current_doctor_policy,
)
from autotube.composition.storage import storage_use_cases


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


def scheduler_tick(p: Ports, c: Collaborators, starter: StartRun) -> SchedulerTick:
    retry = RetryRun(p.runs, p.store, c.progress, p.queue)
    return SchedulerTick(
        retry_due=RetryDueRuns(p.runs, retry, c.recorder),
        run_due=RunDueAutomations(p.automations, c.presenter, starter, p.runs, c.recorder),
    )


def automation_use_cases(p: Ports, c: Collaborators) -> AutomationUseCases:
    starter = StartRun(p.automations, p.pipelines, c.recorder, p.queue, p.ids, p.clock)
    create = CreateAutomation(p.automations, c.builder, c.presenter, p.ids, p.clock)
    return AutomationUseCases(
        list_automations=ListAutomations(p.automations, c.presenter),
        create=create,
        get=GetAutomation(p.automations, c.presenter),
        update=UpdateAutomation(p.automations, c.builder, c.presenter, p.clock),
        set_enabled=SetAutomationEnabled(p.automations, c.presenter, p.clock),
        delete=DeleteAutomation(p.automations),
        duplicate=DuplicateAutomation(p.automations, c.presenter, p.ids, p.clock),
        export=ExportAutomation(p.automations, p.channels, p.pipelines, p.clock),
        import_automation=ImportAutomation(p.channels, c.builder, create),
        start_run=starter,
        scheduler=scheduler_tick(p, c, starter),
    )


def execute_run(p: Ports, c: Collaborators, publisher: PublishRun) -> ExecuteRun:
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
        AutoPublish(p.runs, publisher, c.recorder),
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
    publisher = publish_run(p, c)
    return RunUseCases(
        list_runs=ListRuns(p.runs),
        get=GetRun(p.runs),
        retry=RetryRun(p.runs, p.store, c.progress, p.queue),
        cancel=CancelRun(p.runs, c.progress, p.queue),
        review=ReviewRun(p.runs, c.progress, p.clock, p.queue),
        publish=publisher,
        delete=DeleteRun(p.runs, p.store),
        open_artifact=OpenRunArtifact(p.runs, p.store),
        execute=execute_run(p, c, publisher),
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

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from automator.application.automation_builder import AutomationBuilder
from automator.application.automation_presenter import AutomationPresenter
from automator.application.channel_auth import ChannelAuthorizer
from automator.application.channel_expiry import ChannelExpiry
from automator.application.credential_views import CredentialViews
from automator.application.quota_report import QuotaReport
from automator.application.run_progress import RunProgress
from automator.application.run_recorder import RunRecorder
from automator.application.stage_runner import StageRunner
from automator.application.start_run import StartRun
from automator.application.upload_performer import UploadPerformer
from tests.fixtures.fake_pipeline import FakePipeline, FakePipelineRegistry, kids_pipeline
from tests.fixtures.fake_providers import FakeProviderCatalog
from tests.fixtures.fake_repositories import (
    InMemoryAppSettings,
    InMemoryAutomations,
    InMemoryChannels,
    InMemoryCredentials,
    InMemoryProviderConfigs,
    InMemoryRuns,
)
from tests.fixtures.fake_runtime import (
    FakeClock,
    InMemoryQuotaLedger,
    InMemorySecrets,
    PureScheduleCalculator,
    RecordingEvents,
    RecordingQueue,
    SequentialIds,
    TmpArtifactStore,
)
from tests.fixtures.fake_storage import InMemoryRunFiles
from tests.fixtures.fake_youtube import FakeYouTube


@dataclass
class Harness:
    root: Path
    clock: FakeClock = field(default_factory=FakeClock)
    ids: SequentialIds = field(default_factory=SequentialIds)
    secrets: InMemorySecrets = field(default_factory=InMemorySecrets)
    ledger: InMemoryQuotaLedger = field(default_factory=InMemoryQuotaLedger)
    queue: RecordingQueue = field(default_factory=RecordingQueue)
    events: RecordingEvents = field(default_factory=RecordingEvents)
    youtube: FakeYouTube = field(default_factory=FakeYouTube)
    catalog: FakeProviderCatalog = field(default_factory=FakeProviderCatalog)
    credentials: InMemoryCredentials = field(default_factory=InMemoryCredentials)
    channels: InMemoryChannels = field(default_factory=InMemoryChannels)
    automations: InMemoryAutomations = field(default_factory=InMemoryAutomations)
    runs: InMemoryRuns = field(default_factory=InMemoryRuns)
    provider_configs: InMemoryProviderConfigs = field(default_factory=InMemoryProviderConfigs)
    app_settings: InMemoryAppSettings = field(default_factory=InMemoryAppSettings)
    pipeline: FakePipeline = field(default_factory=FakePipeline)
    kids: FakePipeline = field(default_factory=kids_pipeline)
    schedules: PureScheduleCalculator = field(default_factory=PureScheduleCalculator)
    files: InMemoryRunFiles = field(default_factory=InMemoryRunFiles)

    def __post_init__(self) -> None:
        self.store = TmpArtifactStore(self.root)
        self.pipelines = FakePipelineRegistry([self.pipeline, self.kids])

    @property
    def authorizer(self) -> ChannelAuthorizer:
        return ChannelAuthorizer(self.credentials, self.secrets)

    @property
    def quota_report(self) -> QuotaReport:
        return QuotaReport(self.ledger, self.clock)

    @property
    def expiry(self) -> ChannelExpiry:
        return ChannelExpiry(self.channels)

    @property
    def credential_views(self) -> CredentialViews:
        return CredentialViews(self.secrets, self.quota_report)

    @property
    def presenter(self) -> AutomationPresenter:
        return AutomationPresenter(self.runs, self.schedules)

    @property
    def builder(self) -> AutomationBuilder:
        return AutomationBuilder(self.pipelines, self.channels, self.ids)

    @property
    def recorder(self) -> RunRecorder:
        return RunRecorder(self.runs, self.events, self.clock)

    @property
    def progress(self) -> RunProgress:
        return RunProgress(self.runs, self.recorder, self.clock)

    @property
    def stage_runner(self) -> StageRunner:
        return StageRunner(self.store, self.recorder, self.progress, self.ids, self.clock)

    @property
    def performer(self) -> UploadPerformer:
        return UploadPerformer(
            self.youtube, self.store, self.authorizer, self.quota_report, self.expiry
        )

    @property
    def start_run(self) -> StartRun:
        return StartRun(
            self.automations, self.pipelines, self.recorder, self.queue, self.ids, self.clock
        )

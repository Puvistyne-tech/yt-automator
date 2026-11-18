from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from autotube.domain.pipeline import Stage, StageContext
from autotube.domain.pipeline_descriptors import PipelineDescriptor
from autotube.domain.quality import ScoreItem
from autotube.domain.run_parts import Artifact, StageRun, Upload
from autotube.infrastructure.config import RuntimeConfig
from autotube.main import Overrides
from tests.fixtures.fake_pipeline import FakePipeline, FakePipelineRegistry
from tests.fixtures.fake_runtime import RecordingEvents
from tests.unit.api.client import Api, ok, streamed_events, wired

UI_SCHEMA: dict[str, Any] = {
    "ui:sections": [
        {"title": "Story", "fields": ["topic", "score"]},
        {"title": "Testing", "fields": ["fail_stage", "with_thumbnail", "extra_meta", "font_file"]},
    ],
    "topic": {"ui:widget": "textarea", "ui:options": {"rows": 2}},
}


@dataclass(frozen=True)
class SectionedPipeline:
    inner: FakePipeline = field(default_factory=FakePipeline)

    @property
    def descriptor(self) -> PipelineDescriptor:
        inner = self.inner.descriptor.model_dump()
        return PipelineDescriptor.model_validate({**inner, "ui_schema": UI_SCHEMA})

    @property
    def settings_model(self) -> type[BaseModel]:
        return self.inner.settings_model

    def stages(self) -> Sequence[Stage]:
        return self.inner.stages()

    def score(self, context: StageContext) -> Sequence[ScoreItem]:
        return self.inner.score(context)


def test_ui_schema_is_passed_through(config: RuntimeConfig, overrides: Overrides) -> None:
    pipelines = FakePipelineRegistry([SectionedPipeline()])
    with wired(config, overrides, pipelines=pipelines) as client:
        assert ok(client.get("/api/pipelines/fake"))["ui_schema"] == UI_SCHEMA


def payload_keys(events: list[dict[str, Any]], kind: str) -> set[frozenset[str]]:
    return {frozenset(event["payload"]) for event in events if event["kind"] == kind}


def test_event_payloads_match_the_ui(config: RuntimeConfig, overrides: Overrides) -> None:
    with wired(config, overrides, events=RecordingEvents()) as client:
        api = Api(client, client.app.state.runtime)  # type: ignore[attr-defined]
        run = api.approved_run()
        ok(client.post(f"/api/runs/{run['id']}/publish"))
        events = streamed_events(client)
    assert {event["run_id"] for event in events} == {run["id"]}
    assert all(set(event) == {"run_id", "kind", "at", "payload"} for event in events)
    assert payload_keys(events, "status") == {frozenset({"status", "error"})}
    assert payload_keys(events, "stage") == {frozenset(StageRun.model_fields)}
    assert payload_keys(events, "artifact") == {frozenset(Artifact.model_fields)}
    assert payload_keys(events, "upload") == {frozenset(Upload.model_fields)}
    logs = [event["payload"] for event in events if event["kind"] == "log"]
    assert logs[0] == {"message": "script running", "level": "info", "stage_id": "script"}

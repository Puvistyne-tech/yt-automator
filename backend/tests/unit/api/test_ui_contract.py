from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from fastapi.testclient import TestClient
from pydantic import BaseModel

from automator.domain.pipeline import Stage, StageContext
from automator.domain.pipeline_descriptors import PipelineDescriptor
from automator.domain.quality import ScoreItem
from automator.domain.run_parts import Artifact, StageRun, Upload
from automator.infrastructure.config import RuntimeConfig
from automator.main import Overrides, create_app
from tests.fixtures.fake_pipeline import FakePipeline, FakePipelineRegistry
from tests.fixtures.fake_runtime import RecordingEvents
from tests.unit.api.client import Api, ok

UI_SCHEMA: dict[str, Any] = {
    "ui:sections": [{"title": "Story", "fields": ["topic", "score"]}],
    "topic": {"ui:widget": "textarea", "ui:help": "What the story is about"},
}


@dataclass(frozen=True)
class SectionedPipeline:
    inner: FakePipeline = field(default_factory=FakePipeline)

    @property
    def descriptor(self) -> PipelineDescriptor:
        return self.inner.descriptor.model_copy(update={"ui_schema": UI_SCHEMA})

    @property
    def settings_model(self) -> type[BaseModel]:
        return self.inner.settings_model

    def stages(self) -> Sequence[Stage]:
        return self.inner.stages()

    def score(self, context: StageContext) -> Sequence[ScoreItem]:
        return self.inner.score(context)


def wired(config: RuntimeConfig, overrides: Overrides, **changes: Any) -> TestClient:
    app = create_app(config, Overrides(**(vars(overrides) | changes)))
    return TestClient(app, follow_redirects=False)


def test_ui_schema_is_passed_through(config: RuntimeConfig, overrides: Overrides) -> None:
    pipelines = FakePipelineRegistry([SectionedPipeline()])
    with wired(config, overrides, pipelines=pipelines) as client:
        assert ok(client.get("/api/pipelines/fake"))["ui_schema"] == UI_SCHEMA


def streamed_events(client: TestClient) -> list[dict[str, Any]]:
    with client.stream("GET", "/api/events") as response:
        lines = [line for line in response.iter_lines() if line.startswith("data: ")]
    return [json.loads(line.removeprefix("data: ")) for line in lines]


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
    assert logs[0] == {"message": "script running", "level": "info", "stage_id": None}

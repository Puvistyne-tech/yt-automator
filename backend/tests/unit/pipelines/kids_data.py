from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from automator.domain.capabilities import TextRequest
from automator.domain.pipeline import Stage, StageContext, StageOutcome
from automator.domain.run_parts import Artifact
from automator.pipelines.kids_story.resources import resource_json
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from tests.unit.pipelines.kids_fakes import FakeProviders, FakeWriter, as_json

REFRAIN_EN = "Be kind, be brave, be you!"


def bundled_raw(name: str = "golden_mango") -> dict[str, Any]:
    loaded = resource_json("bundled", f"{name}.json")
    assert isinstance(loaded, dict)
    return loaded


def draft_dict(name: str = "golden_mango", refrain: str = REFRAIN_EN) -> dict[str, Any]:
    raw = bundled_raw(name)
    text = raw["text"]["en"]
    scenes = [
        {**scene, "narration": narration.replace("{refrain}", refrain)}
        for scene, narration in zip(raw["scenes"], text["narrations"], strict=True)
    ]
    return {
        "title": text["title"],
        "moral": text["moral"],
        "scenes": scenes,
        "questions": text["questions"],
        "short_scenes": raw["short_scenes"],
        "hook_line": text["hook_line"],
        "thumbnail": raw["thumbnail"],
    }


def tamil_text(name: str = "golden_mango") -> dict[str, Any]:
    raw = bundled_raw(name)
    text = dict(raw["text"]["ta"])
    refrain = KidsStorySettings().series.refrain.ta
    text["narrations"] = [line.replace("{refrain}", refrain) for line in text["narrations"]]
    return text


def is_translation(request: TextRequest) -> bool:
    schema = request.json_schema or {}
    return schema.get("title") == "StoryText"


def is_judge(request: TextRequest) -> bool:
    return bool(request.images)


def smart_writer(judge_answer: str = "2") -> FakeWriter:
    def respond(request: TextRequest) -> str:
        if is_judge(request):
            return judge_answer
        if is_translation(request):
            return as_json(tamil_text())
        return as_json(draft_dict())

    return FakeWriter(respond)


def quick_settings(**sections: dict[str, Any]) -> KidsStorySettings:
    base: dict[str, Any] = {
        "episode": {"resolution": "1280x720"},
        "short": {"resolution": "720x1280"},
        "thumbnail": {"width": 640, "height": 360},
        "visuals": {"image_candidates": 1, "hero_candidates": 2, "sheet_size": 256},
    }
    for name, values in sections.items():
        base[name] = {**base.get(name, {}), **values}
    return KidsStorySettings.model_validate(base)


@dataclass
class StageRig:
    root: Path
    settings: KidsStorySettings = field(default_factory=quick_settings)
    languages: tuple[str, ...] = ("en", "ta")
    providers: FakeProviders = field(default_factory=FakeProviders)
    artifacts: list[Artifact] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    run_id: str = "run-1"

    def context(self) -> StageContext:
        self.root.mkdir(parents=True, exist_ok=True)
        return StageContext(
            run_id=self.run_id,
            settings=self.settings,
            languages=self.languages,
            workspace=self.root,
            artifacts=tuple(self.artifacts),
            providers=self.providers,
            log=self.logs.append,
        )

    def run(self, stage: Stage) -> StageOutcome:
        outcome = stage.run(self.context())
        for number, new in enumerate(outcome.artifacts):
            self.artifacts.append(
                Artifact(
                    id=f"{stage.descriptor.id}-{number}",
                    kind=new.kind,
                    stage_id=stage.descriptor.id,
                    language=new.language,
                    variant=new.variant,
                    filename=new.path.relative_to(self.root).as_posix(),
                    media_type=new.media_type,
                    size_bytes=new.path.stat().st_size,
                    meta=new.meta,
                )
            )
        return outcome

    def produced_by(self, stage_id: str) -> list[Artifact]:
        return [item for item in self.artifacts if item.stage_id == stage_id]

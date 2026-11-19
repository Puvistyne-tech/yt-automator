from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from autotube.domain.capabilities import TextRequest
from autotube.domain.pipeline import Stage, StageContext, StageOutcome
from autotube.domain.run_enums import ArtifactKind
from autotube.domain.run_parts import Artifact
from autotube.pipelines.narrated_video.plugin import KidsStoryPipeline
from autotube.pipelines.narrated_video.resources import resource_json
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.timeline.voices import VoiceLine
from tests.fixtures.kids_fakes import FakeProviders, FakeWriter, LogBook, as_json
from tests.fixtures.quick_sections import QUICK_SECTIONS

REFRAIN_EN = "Be kind, be brave, be you!"
STAGES: tuple[Stage, ...] = tuple(KidsStoryPipeline().stages())
BOTH = [("en", "episode"), ("en", "short"), ("ta", "episode"), ("ta", "short")]


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


def story(language: str = "en", **changes: Any) -> Story:
    return Story.model_validate(
        {**draft_dict(), "language": language, "theme": "sharing", **changes}
    )


def tamil_text(name: str = "golden_mango") -> dict[str, Any]:
    raw = bundled_raw(name)
    text = dict(raw["text"]["ta"])
    refrain = KidsStorySettings().series.refrain.ta
    text["narrations"] = [line.replace("{refrain}", refrain) for line in text["narrations"]]
    return text


def tamil_draft() -> dict[str, Any]:
    draft, text = draft_dict(), tamil_text()
    scenes = [
        {**scene, "narration": line}
        for scene, line in zip(draft["scenes"], text["narrations"], strict=True)
    ]
    keys = ("title", "moral", "questions", "hook_line")
    return {**draft, **{key: text[key] for key in keys}, "scenes": scenes}


def english_text() -> dict[str, Any]:
    draft = draft_dict()
    keys = ("title", "moral", "questions", "hook_line")
    narrations = [scene["narration"] for scene in draft["scenes"]]
    return {**{key: draft[key] for key in keys}, "narrations": narrations}


def is_translation(request: TextRequest) -> bool:
    schema = request.json_schema or {}
    return schema.get("title") == "StoryText"


def is_judge(request: TextRequest) -> bool:
    return bool(request.images)


def story_answer(name: str = "golden_mango") -> str:
    return as_json(draft_dict(name))


def tamil_answer(name: str = "golden_mango") -> str:
    return as_json(tamil_text(name))


def smart_writer(
    judge_answer: str = "2", name: str = "golden_mango", draft: dict[str, Any] | None = None
) -> FakeWriter:
    answer = as_json(draft) if draft else story_answer(name)

    def respond(request: TextRequest) -> str:
        if is_judge(request):
            return judge_answer
        return tamil_answer(name) if is_translation(request) else answer

    return FakeWriter(respond)


def quick_settings(**sections: dict[str, Any]) -> KidsStorySettings:
    merged = {key: {**QUICK_SECTIONS.get(key, {}), **values} for key, values in sections.items()}
    return KidsStorySettings.model_validate(QUICK_SECTIONS | merged)


@dataclass
class StageRig:
    root: Path
    settings: KidsStorySettings = field(default_factory=quick_settings)
    languages: tuple[str, ...] = ("en", "ta")
    providers: FakeProviders = field(default_factory=FakeProviders)
    artifacts: list[Artifact] = field(default_factory=list)
    book: LogBook = field(default_factory=LogBook)
    run_id: str = "run-1"

    @property
    def logs(self) -> list[str]:
        return self.book.lines

    def context(self) -> StageContext:
        self.root.mkdir(parents=True, exist_ok=True)
        return StageContext(
            run_id=self.run_id,
            settings=self.settings,
            languages=self.languages,
            workspace=self.root,
            artifacts=tuple(self.artifacts),
            providers=self.providers,
            log=self.book,
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


def with_font(font: Path, **sections: dict[str, Any]) -> KidsStorySettings:
    fonts = {"en": [str(font)], "ta": [str(font)]}
    thumbnail = {**sections.pop("thumbnail", {}), "font_files": fonts}
    return quick_settings(thumbnail=thumbnail, **sections)


def voices(
    draft: Story, seconds: float = 10.0, extra: tuple[str, ...] = ("intro", "outro", "hook")
) -> dict[str, VoiceLine]:
    keys = [f"scene-{index}" for index in range(len(draft.scenes))] + list(extra)
    return {
        key: VoiceLine(segment=key, filename=f"voice/{key}.wav", seconds=seconds, text="hi")
        for key in keys
    }


def run_chain(rig: StageRig, until: str | None = None) -> StageRig:
    for stage in STAGES:
        rig.run(stage)
        if stage.descriptor.id == until:
            break
    return rig


def stage_named(stage_id: str) -> Stage:
    return next(stage for stage in STAGES if stage.descriptor.id == stage_id)


def meta_of(rig: StageRig, role: str) -> list[Artifact]:
    return [item for item in rig.artifacts if item.meta.get("role") == role]


def roles(rig: StageRig, kind: ArtifactKind) -> list[tuple[str | None, str | None]]:
    pairs = ((item.language, item.variant) for item in rig.artifacts if item.kind is kind)
    return sorted(pairs, key=str)

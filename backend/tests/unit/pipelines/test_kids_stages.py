from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import BaseModel

from autotube.domain.run_enums import ArtifactKind
from autotube.pipelines.kids_story.stages.package import PackageStage
from autotube.pipelines.kids_story.stages.run_settings import kids_settings
from autotube.pipelines.kids_story.stages.story import StoryStage
from tests.fixtures.kids_data import (
    BOTH,
    StageRig,
    meta_of,
    quick_settings,
    roles,
    run_chain,
    smart_writer,
)
from tests.fixtures.kids_fakes import FakeMedia, FakeProviders, failing_writer


def test_full_chain_writes_translates_and_packages_both_languages(tmp_path: Path) -> None:
    writer = smart_writer()
    rig = run_chain(StageRig(tmp_path, providers=FakeProviders(writer=writer)))
    stories = meta_of(rig, "story")
    assert [(item.language, item.meta["source"]) for item in stories] == [
        ("en", "llm"),
        ("ta", "llm"),
    ]
    assert roles(rig, ArtifactKind.THUMBNAIL) == BOTH
    assert roles(rig, ArtifactKind.METADATA) == BOTH
    assert roles(rig, ArtifactKind.SUBTITLE) == BOTH
    finals = [(item.language, item.variant) for item in meta_of(rig, "final_video")]
    assert sorted(finals) == BOTH
    assert all(item.language is None for item in meta_of(rig, "clip"))
    assert any(request.images for request in writer.requests)
    metadata = meta_of(rig, "upload_metadata")
    assert all(item.meta["made_for_kids"] is True for item in metadata)
    tamil_meta = next(item for item in metadata if item.language == "ta")
    assert tamil_meta.meta["default_language"] == "ta"


def test_failing_writer_falls_back_to_a_bundled_story(tmp_path: Path) -> None:
    rig = StageRig(tmp_path, providers=FakeProviders(writer=failing_writer()))
    outcome = rig.run(StoryStage())
    assert outcome.provider == "bundled"
    assert {item.meta["source"] for item in meta_of(rig, "story")} == {"bundled"}
    warnings = rig.book.warnings()
    assert any("story writer unavailable" in line for line in warnings)
    assert any("falling back" in line for line in warnings)
    assert not any("using bundled story" in line for line in warnings)


def test_missing_writer_logs_and_uses_a_bundled_story(tmp_path: Path) -> None:
    rig = StageRig(tmp_path)
    assert rig.run(StoryStage()).provider == "bundled"
    assert any("story writer unavailable: no provider for llm" in line for line in rig.logs)


def test_bundled_only_never_asks_the_model(tmp_path: Path) -> None:
    writer = smart_writer()
    settings = quick_settings(story={"source": "bundled_only"})
    rig = StageRig(tmp_path, settings=settings, providers=FakeProviders(writer=writer))
    assert rig.run(StoryStage()).provider == "bundled" and writer.requests == []
    assert not any("falling back" in line for line in rig.logs)


def test_scene_bounds_reject_the_model_story(tmp_path: Path) -> None:
    writer = smart_writer()
    settings = quick_settings(
        story={"scene_count_min": 10, "scene_count_max": 12, "max_attempts": 2}
    )
    rig = StageRig(tmp_path, settings=settings, providers=FakeProviders(writer=writer))
    assert rig.run(StoryStage()).provider == "bundled"
    assert "use between 10 and 12 scenes" in writer.requests[1].prompt


def test_no_compatible_bundled_story_fails_the_stage(tmp_path: Path) -> None:
    bundled_only = quick_settings(story={"source": "bundled_only"})
    settings = bundled_only.model_copy(update={"cast": bundled_only.cast[:1]})
    with pytest.raises(LookupError, match="no bundled story"):
        StageRig(tmp_path, settings=settings).run(StoryStage())


def test_package_reports_the_local_provider(tmp_path: Path) -> None:
    rig = run_chain(StageRig(tmp_path, languages=("en",)), "assemble")
    assert rig.run(PackageStage()).provider == "local"


class ForeignSettings(BaseModel):
    pass


def test_stages_refuse_settings_of_another_pipeline(tmp_path: Path) -> None:
    foreign = replace(StageRig(tmp_path).context(), settings=ForeignSettings())
    with pytest.raises(TypeError, match="KidsStorySettings"):
        kids_settings(foreign)


class UnmeasurableMedia(FakeMedia):
    def duration_seconds(self, media: Path) -> float:
        raise OSError(f"cannot probe {media.name}")


def test_an_unmeasurable_video_keeps_its_planned_length(tmp_path: Path) -> None:
    providers = FakeProviders(media=UnmeasurableMedia())
    settings = quick_settings(short={"enabled": False})
    rig = StageRig(tmp_path, settings=settings, languages=("en",), providers=providers)
    [final] = meta_of(run_chain(rig, "assemble"), "final_video")
    assert final.meta["duration_seconds"] == final.meta["planned_seconds"]
    assert any("could not measure en-episode.mp4" in line for line in rig.logs)

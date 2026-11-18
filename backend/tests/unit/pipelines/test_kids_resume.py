from __future__ import annotations

import json
from pathlib import Path

import pytest

from automator.domain.run_enums import ArtifactKind
from automator.domain.run_parts import Artifact
from automator.pipelines.kids_story.artifacts import MissingArtifactError, Role, latest, required
from tests.fixtures.kids_data import STAGES, StageRig, meta_of, run_chain, stage_named
from tests.fixtures.kids_fakes import FakeProviders

PRODUCED = {
    "voice": {"narration"},
    "art": {"candidate", "character_sheet", "visual", "thumbnail_art"},
    "motion": {"clip"},
    "music": {"music", "sound_effect"},
    "assemble": {"final_video", "composition", "captions"},
    "package": {"thumbnail", "upload_metadata", "caption_track"},
}


@pytest.fixture(scope="module")
def finished(tmp_path_factory: pytest.TempPathFactory) -> StageRig:
    return run_chain(StageRig(tmp_path_factory.mktemp("resume")))


def produced_before(rig: StageRig, stage_id: str) -> list[Artifact]:
    ids = [stage.descriptor.id for stage in STAGES]
    earlier = set(ids[: ids.index(stage_id)])
    return [item for item in rig.artifacts if item.stage_id in earlier]


@pytest.mark.parametrize("stage_id", list(PRODUCED))
def test_each_stage_resumes_from_earlier_artifacts_only(finished: StageRig, stage_id: str) -> None:
    rig = StageRig(finished.root, artifacts=produced_before(finished, stage_id))
    rig.run(stage_named(stage_id))
    made = rig.produced_by(stage_id)
    assert {str(item.meta["role"]) for item in made} == PRODUCED[stage_id]
    assert len(made) == len(finished.produced_by(stage_id))


@pytest.mark.parametrize(
    ("stage_id", "removed", "message"),
    [
        ("voice", "story", "missing story artifact"),
        ("art", "story", "missing story artifact"),
        ("motion", "visual", "missing visual artifact"),
        ("assemble", "story", "missing story artifact"),
        ("package", "thumbnail_art", "missing thumbnail_art artifact"),
        ("package", "captions", "missing captions artifact"),
    ],
)
def test_a_missing_input_names_the_role(
    finished: StageRig, stage_id: str, removed: str, message: str
) -> None:
    kept = [item for item in produced_before(finished, stage_id) if item.meta["role"] != removed]
    rig = StageRig(finished.root, artifacts=kept, providers=FakeProviders())
    with pytest.raises(MissingArtifactError, match=message):
        rig.run(stage_named(stage_id))


def test_the_newest_artifact_of_a_role_wins(finished: StageRig, tmp_path: Path) -> None:
    original = next(item for item in meta_of(finished, "story") if item.language == "en")
    story = json.loads((finished.root / original.filename).read_text(encoding="utf-8"))
    rewritten = tmp_path / "story-en-again.json"
    rewritten.write_text(json.dumps({**story, "title": "A Second Story"}), encoding="utf-8")
    newer = original.model_copy(update={"id": "story-again", "filename": str(rewritten)})
    artifacts = [*produced_before(finished, "package"), newer]
    rig = StageRig(finished.root, artifacts=artifacts)
    rig.run(stage_named("package"))
    titles = {
        item.meta["title"] for item in meta_of(rig, "upload_metadata") if item.language == "en"
    }
    assert all(str(title).startswith("A Second Story") for title in titles)
    assert len(titles) == 2


def artifact(number: int, language: str = "en") -> Artifact:
    return Artifact(
        id=f"a{number}",
        kind=ArtifactKind.AUDIO,
        stage_id="voice",
        language=language,
        filename=f"{number}.wav",
        media_type="audio/wav",
        size_bytes=1,
        meta={"role": "narration", "segment": "intro"},
    )


def test_latest_and_required_filter_by_role_language_and_meta() -> None:
    items = [artifact(1), artifact(2), artifact(3, "ta")]
    found = latest(items, Role.NARRATION, "en", segment="intro")
    assert found is not None and found.id == "a2"
    assert latest(items, Role.NARRATION, "en", segment="outro") is None
    assert latest(items, Role.MUSIC) is None
    with pytest.raises(
        MissingArtifactError, match="missing narration artifact for en any segment=outro"
    ):
        required(items, Role.NARRATION, "en", segment="outro")

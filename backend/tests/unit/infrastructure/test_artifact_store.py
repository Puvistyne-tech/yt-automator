from __future__ import annotations

from pathlib import Path

import pytest

from automator.domain.pipeline import NewArtifact
from automator.domain.run_enums import ArtifactKind
from automator.domain.run_parts import Artifact
from automator.infrastructure.storage.artifact_store import FileArtifactStore
from automator.shared.errors import NotFound, ValidationFailed


@pytest.fixture
def store(tmp_path: Path) -> FileArtifactStore:
    return FileArtifactStore(tmp_path)


def new_artifact(path: Path) -> NewArtifact:
    return NewArtifact(
        kind=ArtifactKind.VIDEO, path=path, language="en", media_type="video/mp4", meta={"s": 1}
    )


def test_save_copies_into_a_stable_folder(store: FileArtifactStore, tmp_path: Path) -> None:
    workspace = store.workspace("run-1")
    assert workspace == tmp_path / "runs" / "run-1" / "workspace"
    (workspace / "clips").mkdir()
    source = workspace / "clips" / "en.mp4"
    source.write_bytes(b"12345")
    artifact = store.save("run-1", "art-1", "render", new_artifact(source))
    assert (artifact.filename, artifact.size_bytes, artifact.stage_id) == (
        "clips/en.mp4",
        5,
        "render",
    )
    assert (artifact.language, artifact.meta) == ("en", {"s": 1})
    source.write_bytes(b"changed")
    assert store.open("run-1", artifact).read_bytes() == b"12345"
    assert source.exists()


def test_relative_paths_resolve_inside_the_workspace(store: FileArtifactStore) -> None:
    (store.workspace("run-1") / "a.txt").write_text("hi", encoding="utf-8")
    artifact = store.save("run-1", "art-1", "s", new_artifact(Path("a.txt")))
    assert store.open("run-1", artifact).read_text(encoding="utf-8") == "hi"


@pytest.mark.parametrize("escape", ["../../outside.mp4", "/etc/passwd"])
def test_save_refuses_paths_outside_the_workspace(
    store: FileArtifactStore, tmp_path: Path, escape: str
) -> None:
    (tmp_path / "outside.mp4").write_bytes(b"x")
    store.workspace("run-1")
    with pytest.raises(ValidationFailed):
        store.save("run-1", "art-1", "s", new_artifact(Path(escape)))


@pytest.mark.parametrize(("run_id", "artifact_id"), [("../x", "a"), ("run-1", "../../a")])
def test_ids_cannot_traverse(store: FileArtifactStore, run_id: str, artifact_id: str) -> None:
    source = store.workspace("run-1") / "a.txt"
    source.write_text("x", encoding="utf-8")
    with pytest.raises(ValidationFailed):
        store.save(run_id, artifact_id, "s", new_artifact(source))


def test_missing_source_is_rejected(store: FileArtifactStore) -> None:
    with pytest.raises(ValidationFailed):
        store.save("run-1", "a", "s", new_artifact(store.workspace("run-1") / "nope.mp4"))


def test_discard_and_delete_run_remove_files(store: FileArtifactStore, tmp_path: Path) -> None:
    source = store.workspace("run-1") / "a.txt"
    source.write_text("x", encoding="utf-8")
    artifact = store.save("run-1", "art-1", "s", new_artifact(source))
    store.discard("run-1", artifact)
    assert not source.exists()
    with pytest.raises(NotFound):
        store.open("run-1", artifact)
    store.delete_run("run-1")
    assert not (tmp_path / "runs" / "run-1").exists()


def stored_artifact(**changes: str) -> Artifact:
    base = Artifact(
        id="art-1",
        kind=ArtifactKind.VIDEO,
        stage_id="s",
        filename="a.txt",
        media_type="t",
        size_bytes=1,
    )
    return base.model_copy(update=changes)


@pytest.mark.parametrize(
    ("artifact", "error"),
    [
        (stored_artifact(filename=".."), ValidationFailed),
        (stored_artifact(id="../a"), ValidationFailed),
        (stored_artifact(filename="../x"), NotFound),
    ],
)
def test_open_refuses_malicious_names(
    store: FileArtifactStore, artifact: Artifact, error: type[Exception]
) -> None:
    with pytest.raises(error):
        store.open("run-1", artifact)


@pytest.mark.parametrize(
    "artifact",
    [stored_artifact(filename=".."), stored_artifact(filename="../x"), stored_artifact(id="../a")],
)
def test_discard_refuses_malicious_names(store: FileArtifactStore, artifact: Artifact) -> None:
    with pytest.raises(ValidationFailed):
        store.discard("run-1", artifact)

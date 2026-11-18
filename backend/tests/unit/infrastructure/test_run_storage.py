from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from automator.infrastructure.storage.disk_usage import tree_bytes
from automator.infrastructure.storage.run_storage import FileRunStorage
from automator.shared.errors import UpstreamFailure

FINAL = frozenset({"a-video"})


def write(path: Path, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


@pytest.fixture
def storage(tmp_path: Path) -> FileRunStorage:
    runs = tmp_path / "runs"
    write(runs / "run-1" / "artifacts" / "a-video" / "en.mp4", 100)
    write(runs / "run-1" / "artifacts" / "a-image" / "scene.png", 30)
    write(runs / "run-1" / "workspace" / "scene" / "raw.wav", 20)
    write(runs / "run-2" / "workspace" / "story.json", 5)
    write(runs / "not an id" / "x", 1)
    write(runs / "stray.txt", 1)
    write(tmp_path / "automator.db", 50)
    return FileRunStorage(tmp_path)


def test_run_ids_are_the_run_folders_with_opaque_names(storage: FileRunStorage) -> None:
    assert storage.run_ids() == {"run-1", "run-2"}


def test_a_data_folder_without_runs_has_no_run_ids(tmp_path: Path) -> None:
    assert FileRunStorage(tmp_path / "fresh").run_ids() == frozenset()


def test_usage_splits_final_outputs_from_working_files(storage: FileRunStorage) -> None:
    usage = storage.usage("run-1", FINAL)
    assert (usage.final_bytes, usage.intermediate_bytes) == (100, 50)
    assert storage.usage("missing", FINAL).total_bytes == 0


def test_removing_working_files_keeps_final_outputs_and_is_idempotent(
    storage: FileRunStorage, tmp_path: Path
) -> None:
    assert storage.remove_intermediate("run-1", FINAL) == 50
    run_dir = tmp_path / "runs" / "run-1"
    assert sorted(p.name for p in (run_dir / "artifacts").iterdir()) == ["a-video"]
    assert not (run_dir / "workspace").exists()
    assert storage.remove_intermediate("run-1", FINAL) == 0
    assert storage.remove_intermediate("missing", FINAL) == 0


def test_deleting_a_run_reports_what_it_freed_and_is_idempotent(
    storage: FileRunStorage, tmp_path: Path
) -> None:
    assert storage.delete_run("run-1") == 150
    assert not (tmp_path / "runs" / "run-1").exists()
    assert storage.delete_run("run-1") == 0


def test_a_symlinked_working_file_is_removed_without_following_it(
    storage: FileRunStorage, tmp_path: Path
) -> None:
    outside = tmp_path / "outside"
    write(outside / "keep.bin", 7)
    (tmp_path / "runs" / "run-2" / "link").symlink_to(outside, target_is_directory=True)
    storage.remove_intermediate("run-2", frozenset())
    assert (outside / "keep.bin").exists()
    assert tree_bytes(tmp_path / "runs" / "run-2") == 0


def test_deleting_every_run_id_leaves_the_database_and_non_run_entries(
    storage: FileRunStorage, tmp_path: Path
) -> None:
    for run_id in storage.run_ids():
        storage.delete_run(run_id)
    runs = tmp_path / "runs"
    kept = [tmp_path / "automator.db", runs / "not an id" / "x", runs / "stray.txt"]
    assert [path.stat().st_size for path in kept] == [50, 1, 1]
    assert storage.run_ids() == frozenset()


def outside_tree(tmp_path: Path) -> Path:
    outside = tmp_path / "outside"
    write(outside / "keep.bin", 7)
    return outside


def test_a_run_named_link_to_an_outside_folder_is_never_a_run(
    storage: FileRunStorage, tmp_path: Path
) -> None:
    outside = outside_tree(tmp_path)
    (tmp_path / "runs" / "run-link").symlink_to(outside, target_is_directory=True)
    assert "run-link" not in storage.run_ids()
    assert storage.usage("run-link", FINAL).total_bytes == 0
    assert storage.remove_intermediate("run-link", FINAL) == 0
    assert storage.delete_run("run-link") == 0
    assert (outside / "keep.bin").stat().st_size == 7


def test_an_artifacts_link_to_an_outside_folder_is_not_followed(
    storage: FileRunStorage, tmp_path: Path
) -> None:
    outside = outside_tree(tmp_path)
    (tmp_path / "runs" / "run-2" / "artifacts").symlink_to(outside, target_is_directory=True)
    assert storage.usage("run-2", frozenset()).intermediate_bytes == 5
    storage.remove_intermediate("run-2", frozenset())
    assert (outside / "keep.bin").stat().st_size == 7


def test_deleting_a_run_removes_a_linked_file_without_following_it(
    storage: FileRunStorage, tmp_path: Path
) -> None:
    outside = outside_tree(tmp_path)
    (tmp_path / "runs" / "run-2" / "linked.bin").symlink_to(outside / "keep.bin")
    storage.delete_run("run-2")
    assert not (tmp_path / "runs" / "run-2").exists()
    assert (outside / "keep.bin").stat().st_size == 7


def test_a_run_folder_that_survives_removal_is_reported_as_a_failure(
    storage: FileRunStorage, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(shutil, "rmtree", lambda _: None)
    with pytest.raises(UpstreamFailure, match="run-1"):
        storage.delete_run("run-1")
    assert (tmp_path / "runs" / "run-1").is_dir()


def test_a_folder_that_cannot_be_removed_raises(
    storage: FileRunStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(_: Path) -> None:
        raise PermissionError("busy")

    monkeypatch.setattr(shutil, "rmtree", refuse)
    with pytest.raises(PermissionError):
        storage.delete_run("run-1")


def test_disk_facts_cover_the_whole_data_folder(storage: FileRunStorage) -> None:
    assert storage.disk().data_dir_bytes == 100 + 30 + 20 + 5 + 1 + 1 + 50


def test_disk_space_is_unknown_when_the_disk_cannot_be_read(
    storage: FileRunStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unreadable(_: Path) -> None:
        raise OSError("no disk")

    monkeypatch.setattr(shutil, "disk_usage", unreadable)
    disk = storage.disk()
    assert disk.free_bytes is None and disk.disk_bytes is None

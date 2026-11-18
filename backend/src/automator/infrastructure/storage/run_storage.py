from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

from automator.domain.storage import DiskSpace, FileUsage
from automator.infrastructure.storage.artifact_store import (
    ARTIFACTS_DIR,
    RUNS_DIR,
    FileArtifactStore,
)
from automator.infrastructure.storage.disk_usage import disk_usage, tree_bytes
from automator.shared.errors import UpstreamFailure
from automator.shared.ids import is_opaque_id


def is_real_dir(path: Path) -> bool:
    return path.is_dir() and not path.is_symlink()


def remove(path: Path) -> None:
    if is_real_dir(path):
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


class FileRunStorage:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.root = data_dir / RUNS_DIR
        self.paths = FileArtifactStore(data_dir)

    def is_owned(self, path: Path) -> bool:
        inside = path.resolve().parent == self.root.resolve()
        return is_real_dir(path) and inside

    def owned_run_dir(self, run_id: str) -> Path | None:
        run_dir = self.paths.run_dir(run_id)
        return run_dir if self.is_owned(run_dir) else None

    def run_ids(self) -> frozenset[str]:
        if not self.root.is_dir():
            return frozenset()
        return frozenset(
            entry.name
            for entry in self.root.iterdir()
            if is_opaque_id(entry.name) and self.is_owned(entry)
        )

    def intermediate_paths(self, run_id: str, final_ids: frozenset[str]) -> Iterator[Path]:
        run_dir = self.owned_run_dir(run_id)
        if run_dir is None:
            return
        for entry in run_dir.iterdir():
            if entry.name != ARTIFACTS_DIR:
                yield entry
            elif is_real_dir(entry):
                yield from (item for item in entry.iterdir() if item.name not in final_ids)

    def usage(self, run_id: str, final_ids: frozenset[str]) -> FileUsage:
        run_dir = self.owned_run_dir(run_id)
        if run_dir is None:
            return FileUsage(final_bytes=0, intermediate_bytes=0)
        intermediate = sum(tree_bytes(path) for path in self.intermediate_paths(run_id, final_ids))
        return FileUsage(
            final_bytes=tree_bytes(run_dir) - intermediate, intermediate_bytes=intermediate
        )

    def remove_intermediate(self, run_id: str, final_ids: frozenset[str]) -> int:
        freed = 0
        for path in list(self.intermediate_paths(run_id, final_ids)):
            freed += tree_bytes(path)
            remove(path)
        return freed

    def delete_run(self, run_id: str) -> int:
        run_dir = self.owned_run_dir(run_id)
        if run_dir is None:
            return 0
        freed = tree_bytes(run_dir)
        shutil.rmtree(run_dir)
        if run_dir.exists():
            raise UpstreamFailure(f"folder of run {run_id} is still there after removal")
        return freed

    def disk(self) -> DiskSpace:
        usage = disk_usage(self.data_dir)
        return DiskSpace(
            data_dir=str(self.data_dir),
            data_dir_bytes=tree_bytes(self.data_dir),
            disk_bytes=usage[0] if usage is not None else None,
            free_bytes=usage[1] if usage is not None else None,
        )

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
from automator.shared.ids import is_opaque_id


def remove(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)


class FileRunStorage:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.paths = FileArtifactStore(data_dir)

    def run_ids(self) -> frozenset[str]:
        root = self.data_dir / RUNS_DIR
        if not root.is_dir():
            return frozenset()
        return frozenset(
            entry.name for entry in root.iterdir() if entry.is_dir() and is_opaque_id(entry.name)
        )

    def intermediate_paths(self, run_id: str, final_ids: frozenset[str]) -> Iterator[Path]:
        run_dir = self.paths.run_dir(run_id)
        if not run_dir.is_dir():
            return
        for entry in run_dir.iterdir():
            if entry.name != ARTIFACTS_DIR or not entry.is_dir():
                yield entry
                continue
            yield from (item for item in entry.iterdir() if item.name not in final_ids)

    def usage(self, run_id: str, final_ids: frozenset[str]) -> FileUsage:
        total = tree_bytes(self.paths.run_dir(run_id))
        intermediate = sum(tree_bytes(path) for path in self.intermediate_paths(run_id, final_ids))
        return FileUsage(final_bytes=total - intermediate, intermediate_bytes=intermediate)

    def remove_intermediate(self, run_id: str, final_ids: frozenset[str]) -> int:
        freed = 0
        for path in list(self.intermediate_paths(run_id, final_ids)):
            freed += tree_bytes(path)
            remove(path)
        return freed

    def delete_run(self, run_id: str) -> int:
        run_dir = self.paths.run_dir(run_id)
        freed = tree_bytes(run_dir)
        shutil.rmtree(run_dir, ignore_errors=True)
        return freed

    def disk(self) -> DiskSpace:
        usage = disk_usage(self.data_dir)
        return DiskSpace(
            data_dir=str(self.data_dir),
            data_dir_bytes=tree_bytes(self.data_dir),
            disk_bytes=usage[0] if usage is not None else None,
            free_bytes=usage[1] if usage is not None else None,
        )

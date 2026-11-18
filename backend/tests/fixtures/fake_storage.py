from __future__ import annotations

from autotube.domain.storage import DiskSpace, FileUsage
from autotube.shared.errors import UpstreamFailure

ARTIFACTS = "artifacts/"
WORKSPACE = "workspace/"


def artifact_path(artifact_id: str, name: str = "file") -> str:
    return f"{ARTIFACTS}{artifact_id}/{name}"


def workspace_path(name: str) -> str:
    return f"{WORKSPACE}{name}"


def is_final_path(path: str, final_ids: frozenset[str]) -> bool:
    parts = path.split("/")
    return path.startswith(ARTIFACTS) and len(parts) > 2 and parts[1] in final_ids


class InMemoryRunFiles:
    def __init__(self, free_bytes: int | None = 5_000_000, other_bytes: int = 0) -> None:
        self.files: dict[str, dict[str, int]] = {}
        self.free_bytes = free_bytes
        self.other_bytes = other_bytes
        self.failing: set[str] = set()

    def put(self, run_id: str, path: str, size: int) -> None:
        self.files.setdefault(run_id, {})[path] = size

    def fail_for(self, run_id: str) -> None:
        self.failing.add(run_id)

    def check(self, run_id: str) -> None:
        if run_id in self.failing:
            raise UpstreamFailure(f"disk refused to remove {run_id}")

    def run_ids(self) -> frozenset[str]:
        return frozenset(self.files)

    def usage(self, run_id: str, final_ids: frozenset[str]) -> FileUsage:
        files = self.files.get(run_id, {})
        final = sum(size for path, size in files.items() if is_final_path(path, final_ids))
        return FileUsage(final_bytes=final, intermediate_bytes=sum(files.values()) - final)

    def remove_intermediate(self, run_id: str, final_ids: frozenset[str]) -> int:
        self.check(run_id)
        files = self.files.get(run_id, {})
        kept = {path: size for path, size in files.items() if is_final_path(path, final_ids)}
        freed = sum(files.values()) - sum(kept.values())
        if run_id in self.files:
            self.files[run_id] = kept
        return freed

    def delete_run(self, run_id: str) -> int:
        self.check(run_id)
        return sum(self.files.pop(run_id, {}).values())

    def disk(self) -> DiskSpace:
        used = sum(sum(files.values()) for files in self.files.values())
        return DiskSpace(
            data_dir="/tmp/autotube",
            data_dir_bytes=used + self.other_bytes,
            free_bytes=self.free_bytes,
            disk_bytes=None if self.free_bytes is None else self.free_bytes + used,
        )

from __future__ import annotations

import shutil
from pathlib import Path

from autotube.domain.pipeline import NewArtifact
from autotube.domain.run_parts import Artifact
from autotube.shared.errors import NotFound, ValidationFailed
from autotube.shared.ids import is_opaque_id

RUNS_DIR = "runs"
WORKSPACE_DIR = "workspace"
ARTIFACTS_DIR = "artifacts"


def safe_id(value: str, field: str) -> str:
    if not is_opaque_id(value):
        raise ValidationFailed({field: "must be an opaque id"})
    return value


def contained(path: Path, root: Path, field: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValidationFailed({field: "path escapes the run folder"})
    return resolved


class FileArtifactStore:
    def __init__(self, data_dir: Path) -> None:
        self.root = data_dir / RUNS_DIR

    def run_dir(self, run_id: str) -> Path:
        return self.root / safe_id(run_id, "run_id")

    def workspace(self, run_id: str) -> Path:
        path = self.run_dir(run_id) / WORKSPACE_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    def artifact_dir(self, run_id: str, artifact_id: str) -> Path:
        return self.run_dir(run_id) / ARTIFACTS_DIR / safe_id(artifact_id, "artifact_id")

    def save(self, run_id: str, artifact_id: str, stage_id: str, new: NewArtifact) -> Artifact:
        workspace = self.workspace(run_id)
        source = contained(workspace / new.path, workspace, "path")
        if not source.is_file():
            raise ValidationFailed({"path": f"artifact file {new.path.name!r} does not exist"})
        target_dir = self.artifact_dir(run_id, artifact_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        stored = shutil.copyfile(source, target_dir / source.name)
        return Artifact(
            id=artifact_id,
            kind=new.kind,
            stage_id=stage_id,
            language=new.language,
            variant=new.variant,
            filename=source.relative_to(workspace.resolve()).as_posix(),
            media_type=new.media_type,
            size_bytes=stored.stat().st_size,
            meta=new.meta,
        )

    def stored_path(self, run_id: str, artifact: Artifact) -> Path:
        directory = self.artifact_dir(run_id, artifact.id)
        return contained(directory / Path(artifact.filename).name, directory, "filename")

    def open(self, run_id: str, artifact: Artifact) -> Path:
        path = self.stored_path(run_id, artifact)
        if not path.is_file():
            raise NotFound("artifact_file", artifact.id)
        return path

    def discard(self, run_id: str, artifact: Artifact) -> None:
        shutil.rmtree(self.artifact_dir(run_id, artifact.id), ignore_errors=True)
        workspace = self.workspace(run_id)
        contained(workspace / artifact.filename, workspace, "filename").unlink(missing_ok=True)

    def delete_run(self, run_id: str) -> None:
        shutil.rmtree(self.run_dir(run_id), ignore_errors=True)

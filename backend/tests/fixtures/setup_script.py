from __future__ import annotations

import shutil
import stat
import subprocess
from pathlib import Path

from autotube.infrastructure.config import REPOSITORY_ROOT

SCRIPT = REPOSITORY_ROOT / "scripts" / "setup.sh"
HOST_TOOLS = ("dirname", "uname", "id", "cat", "awk", "sort", "tr", "grep", "env", "ln", "mkdir")


def hermetic_bin(tmp_path: Path) -> Path:
    folder = tmp_path / "bin"
    folder.mkdir(exist_ok=True)
    for tool in HOST_TOOLS:
        found = shutil.which(tool)
        assert found, tool
        if not (folder / tool).exists():
            (folder / tool).symlink_to(found)
    return folder


def stub(folder: Path, name: str, body: str = "exit 0") -> Path:
    path = folder / name
    path.unlink(missing_ok=True)
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def setup_run(
    tmp_path: Path,
    *flags: str,
    stubs: tuple[str, ...] = (),
    data_dir: bool = True,
    extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    folder = hermetic_bin(tmp_path)
    for name in stubs:
        stub(folder, name)
    env = {
        "HOME": str(home),
        "PATH": str(folder),
        "SETUP_EXTRA_PATH": "",
        "SETUP_BACKEND_PYTHON": str(tmp_path / "no-venv" / "python"),
    }
    if data_dir:
        env["AUTOTUBE_DATA_DIR"] = str(home / "data")
    env |= extra or {}
    bash = shutil.which("bash") or "bash"
    return subprocess.run(
        [bash, str(SCRIPT), *flags],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )


def planned(tmp_path: Path, *flags: str) -> str:
    result = setup_run(tmp_path, "--dry-run", *flags)
    assert result.returncode == 0, result.stderr
    assert list((tmp_path / "home").iterdir()) == []
    return result.stdout


def groups_in(plan: str) -> set[str]:
    return {line.removeprefix("==> ").split(":")[0] for line in plan.splitlines() if "==> " in line}

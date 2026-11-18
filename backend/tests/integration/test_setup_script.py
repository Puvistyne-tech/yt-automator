from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from automator.infrastructure.config import REPOSITORY_ROOT

SCRIPT = REPOSITORY_ROOT / "scripts" / "setup.sh"
MODEL_GROUPS = ("ollama", "images", "motion", "speech", "music", "fonts")

pytestmark = pytest.mark.integration


def setup_run(tmp_path: Path, *flags: str) -> subprocess.CompletedProcess[str]:
    env = os.environ | {"HOME": str(tmp_path), "AUTOMATOR_DATA_DIR": str(tmp_path / "data")}
    return subprocess.run(
        ["bash", str(SCRIPT), *flags],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )


def planned(tmp_path: Path, *flags: str) -> str:
    result = setup_run(tmp_path, "--dry-run", *flags)
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "data").exists()
    assert not (tmp_path / "Library").exists()
    return result.stdout


def groups_in(plan: str) -> set[str]:
    return {line.removeprefix("==> ").split(":")[0] for line in plan.splitlines() if "==> " in line}


def test_script_parses() -> None:
    assert subprocess.run(["bash", "-n", str(SCRIPT)], check=False).returncode == 0


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck is not installed")
def test_script_passes_shellcheck() -> None:
    assert subprocess.run(["shellcheck", str(SCRIPT)], check=False).returncode == 0


def test_script_has_no_comments_besides_the_shebang() -> None:
    lines = SCRIPT.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "#!/usr/bin/env bash"
    assert [line for line in lines[1:] if line.lstrip().startswith("#")] == []


def test_default_plan_is_the_base_only(tmp_path: Path) -> None:
    plan = planned(tmp_path)
    assert groups_in(plan) == {"base", "summary"}
    assert "just setup" in plan
    assert "pnpm build" in plan


def test_selected_model_groups_are_planned(tmp_path: Path) -> None:
    plan = planned(tmp_path, "--speech", "--music")
    assert groups_in(plan) == {"base", "speech", "music", "python extras", "summary"}
    assert "--extra tts --extra align --extra mac" in plan
    assert str(tmp_path / "data" / "tools" / "ace-step") in plan
    assert str(tmp_path / "data" / "assets" / "music") in plan


def test_models_flag_plans_every_model_group(tmp_path: Path) -> None:
    plan = planned(tmp_path, "--models", "--no-base")
    assert groups_in(plan) >= set(MODEL_GROUPS)
    assert "base" not in groups_in(plan)
    assert "ollama pull" in plan
    assert "uv tool install" in plan and "mflux" in plan and "depthflow" in plan
    assert "font-noto-sans-tamil" in plan


def test_all_plans_everything_including_the_service(tmp_path: Path) -> None:
    plan = planned(tmp_path, "--all")
    assert groups_in(plan) >= {"base", "service", *MODEL_GROUPS}
    assert "com.yt-automator.app.plist" in plan
    assert "AUTOMATOR_PORT" in plan


def test_uninstall_service_alone_skips_the_base(tmp_path: Path) -> None:
    plan = planned(tmp_path, "--uninstall-service")
    assert groups_in(plan) == {"uninstall service", "summary"}


def test_unknown_flag_is_refused(tmp_path: Path) -> None:
    result = setup_run(tmp_path, "--bogus")
    assert result.returncode == 2
    assert "Usage" in result.stderr


def test_help_prints_usage(tmp_path: Path) -> None:
    result = setup_run(tmp_path, "--help")
    assert result.returncode == 0
    assert "--dry-run" in result.stdout

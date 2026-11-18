from __future__ import annotations

import io
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from automator.doctor import main as doctor_main
from automator.infrastructure.config import REPOSITORY_ROOT

SCRIPT = REPOSITORY_ROOT / "scripts" / "setup.sh"
HOST_TOOLS = ("dirname", "uname", "id", "cat", "awk", "sort", "tr", "grep")
MODEL_GROUPS = ("ollama", "images", "motion", "speech", "music", "fonts")

pytestmark = pytest.mark.integration


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
        env["AUTOMATOR_DATA_DIR"] = str(home / "data")
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


def test_default_plan_is_the_base_only(tmp_path: Path) -> None:
    plan = planned(tmp_path)
    assert groups_in(plan) == {"base", "summary"}
    assert "just setup" in plan and "pnpm build" in plan
    assert "would run: uv tool update-shell" in plan
    assert "Planned:" in plan and "Dry run: nothing was changed." in plan
    assert "Start the app with: just dev-api" in plan


@pytest.mark.parametrize(
    ("flag", "expected"),
    [
        ("--ollama", {"ollama"}),
        ("--images", {"images"}),
        ("--motion", {"motion"}),
        ("--fonts", {"fonts"}),
        ("--speech", {"speech", "python extras"}),
        ("--music", {"music"}),
        ("--service", {"service"}),
    ],
)
def test_each_flag_plans_its_own_group(tmp_path: Path, flag: str, expected: set[str]) -> None:
    assert groups_in(planned(tmp_path, flag)) == {"base", "summary", *expected}


def test_model_groups_plan_their_installs(tmp_path: Path) -> None:
    plan = planned(tmp_path, "--models", "--no-base")
    assert groups_in(plan) == {*MODEL_GROUPS, "python extras", "summary"}
    assert "would run: ollama pull gemma3:12b" in plan
    assert "uv tool install --python 3.12 mflux" in plan
    assert "uv tool install --python 3.12 depthflow" in plan
    assert "--extra tts --extra align --extra mac" in plan
    assert "font-noto-sans-tamil" in plan
    assert str(tmp_path / "home" / "data" / "tools" / "ace-step") in plan
    assert str(tmp_path / "home" / "data" / "assets" / "music") in plan


def test_all_plans_everything_including_the_service(tmp_path: Path) -> None:
    plan = planned(tmp_path, "--all")
    assert groups_in(plan) >= {"base", "service", *MODEL_GROUPS}
    assert "com.yt-automator.app.plist with AUTOMATOR_HOST=127.0.0.1 AUTOMATOR_PORT=8000" in plan
    assert "The app starts at login." in plan


def test_uninstall_service_alone_skips_the_base(tmp_path: Path) -> None:
    plan = planned(tmp_path, "--uninstall-service")
    assert groups_in(plan) == {"uninstall service", "summary"}
    assert "would run: launchctl bootout" in plan
    assert "would run: rm -f" in plan


def test_uninstall_with_another_group_keeps_the_base(tmp_path: Path) -> None:
    plan = planned(tmp_path, "--uninstall-service", "--music")
    assert groups_in(plan) == {"base", "music", "uninstall service", "summary"}


def test_no_base_alone_plans_nothing(tmp_path: Path) -> None:
    assert groups_in(planned(tmp_path, "--no-base")) == {"summary"}


def test_present_tools_are_skipped(tmp_path: Path) -> None:
    result = setup_run(tmp_path, "--dry-run", stubs=("uv", "just"))
    assert result.returncode == 0, result.stderr
    assert "uv is already present" in result.stdout
    assert "just is already present" in result.stdout


def test_unknown_flag_is_refused(tmp_path: Path) -> None:
    result = setup_run(tmp_path, "--bogus")
    assert result.returncode == 2
    assert "Usage" in result.stderr


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_help_prints_usage(tmp_path: Path, flag: str) -> None:
    result = setup_run(tmp_path, flag)
    assert result.returncode == 0
    assert "--dry-run" in result.stdout
    assert "SETUP_EXTRA_PATH" in result.stdout


@pytest.mark.parametrize(
    "environ",
    [{}, {"AUTOMATOR_PORT": "9000"}, {"AUTOMATOR_HOST": "0.0.0.0", "AUTOMATOR_PORT": "8100"}],
)
def test_script_defaults_match_the_app(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, environ: dict[str, str]
) -> None:
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    out = io.StringIO()
    assert doctor_main(["--print-defaults"], environ, out) == 0
    result = setup_run(tmp_path, "--print-defaults", data_dir=False, extra=environ)
    assert result.returncode == 0
    assert f"DATA_DIR={home / '.yt-automator'}" in result.stdout.splitlines()
    assert result.stdout.splitlines() == out.getvalue().splitlines()


def test_the_plan_uses_the_app_defaults_once_the_backend_exists(tmp_path: Path) -> None:
    defaults = f"OLLAMA_MODEL=stub:1b\nMUSIC_DIR={tmp_path}/tracks\nREDIRECT_BASE_URL=http://x:1"
    body = f'if [ "$1" = "-m" ]; then printf "{defaults}\\n"; else echo 3.12; fi'
    python = stub(tmp_path, "python", body)
    extra = {"SETUP_BACKEND_PYTHON": str(python)}
    plan = setup_run(tmp_path, "--dry-run", "--ollama", "--music", extra=extra).stdout
    assert "would run: ollama pull stub:1b" in plan
    assert f"would run: mkdir -p {tmp_path}/tracks" in plan
    assert "backend venv (Python 3.12, needed by Kokoro) is already present" in plan


@pytest.mark.parametrize("variable", ["OLLAMA_WAIT_SECONDS", "SERVICE_STOP_WAIT_SECONDS"])
def test_wait_limits_must_be_whole_seconds(tmp_path: Path, variable: str) -> None:
    result = setup_run(tmp_path, "--dry-run", extra={variable: "soon"})
    assert result.returncode == 1
    assert f"{variable} must be a whole number of seconds, got 'soon'" in result.stderr

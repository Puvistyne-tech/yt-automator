from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

GUARD_PATH = Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "guard_bash.py"


def load_guard() -> ModuleType:
    spec = importlib.util.spec_from_file_location("guard_bash", GUARD_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


GUARD = load_guard()


@pytest.mark.parametrize(
    "command",
    [
        "git merge -X ours origin/main",
        "git merge -Xtheirs origin/main",
        "git merge --strategy-option ours origin/main",
        "git merge --strategy-option=theirs origin/main",
        "git merge -s ours origin/main",
        "git merge -sours origin/main",
        "git merge --strategy ours origin/main",
        "git merge --strategy=ours origin/main",
        "git pull -X theirs origin main",
        "git pull --strategy=ours origin main",
        "git -C /tmp merge -X ours origin/main",
    ],
)
def test_blocks_merges_that_discard_one_side(command: str, tmp_path: Path) -> None:
    reason = GUARD.violation(command, tmp_path)
    assert reason is not None and "plain merge" in reason


@pytest.mark.parametrize(
    "command",
    [
        "git merge origin/main",
        "git merge --no-edit origin/main",
        "git merge -s ort origin/main",
        "git merge -X patience origin/main",
        "git pull --ff-only",
        "git checkout --ours CLAUDE.md",
        "git log -s",
    ],
)
def test_allows_plain_merges_and_unrelated_commands(command: str, tmp_path: Path) -> None:
    assert GUARD.violation(command, tmp_path) is None


def test_main_blocks_a_chained_one_sided_merge(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    event = {"tool_input": {"command": "git fetch origin && git merge -X ours origin/main"}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    assert GUARD.main() == 2
    assert "resolve conflicts by hand" in capsys.readouterr().err

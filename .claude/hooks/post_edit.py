#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from comment_scan import PYTHON_SUFFIXES, SCRIPT_SUFFIXES, Finding, is_source, scan_file  # noqa: E402

TIMEOUT_SECONDS = 30


def project_root() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])


def run_quietly(command: list[str], cwd: Path) -> str:
    try:
        done = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return "" if done.returncode == 0 else (done.stdout + done.stderr).strip()


def ruff_command() -> list[str] | None:
    if shutil.which("ruff"):
        return ["ruff"]
    if shutil.which("uvx"):
        return ["uvx", "ruff"]
    return None


def format_python(path: Path, root: Path) -> str:
    ruff = ruff_command()
    if ruff is None:
        return ""
    run_quietly([*ruff, "format", str(path)], root)
    return run_quietly([*ruff, "check", "--fix", "--quiet", str(path)], root)


def format_script(path: Path, root: Path) -> str:
    web = root / "web"
    biome = web / "node_modules" / ".bin" / "biome"
    if not biome.exists() or web not in path.parents:
        return ""
    return run_quietly([str(biome), "check", "--write", str(path)], web)


def format_and_lint(path: Path, root: Path) -> str:
    if path.suffix in PYTHON_SUFFIXES:
        return format_python(path, root)
    if path.suffix in SCRIPT_SUFFIXES:
        return format_script(path, root)
    return ""


def added_lines(tool_input: dict[str, object]) -> set[str]:
    added = str(tool_input.get("new_string") or tool_input.get("content") or "")
    return {line.strip() for line in added.splitlines() if line.strip()}


def new_comment_findings(path: Path, tool_input: dict[str, object]) -> list[Finding]:
    added = added_lines(tool_input)
    return [
        finding
        for finding in scan_file(path)
        if finding.text.removeprefix("docstring: ").strip() in added
    ]


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    tool_input = event.get("tool_input") or {}
    raw_path = tool_input.get("file_path")
    if not raw_path:
        return 0
    root = project_root()
    path = Path(raw_path)
    path = path if path.is_absolute() else root / path
    if not path.is_file() or root not in path.resolve().parents or not is_source(path):
        return 0
    problems = []
    lint_output = format_and_lint(path, root)
    if lint_output:
        problems.append("Lint findings:\n" + lint_output)
    comments = new_comment_findings(path, tool_input)
    if comments:
        rendered = "\n".join(finding.render() for finding in comments)
        problems.append(
            "Comments are forbidden (.claude/rules/no-comments.md). Remove these:\n" + rendered
        )
    if not problems:
        return 0
    print("\n\n".join(problems), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())

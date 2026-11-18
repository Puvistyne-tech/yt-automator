#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

PROTECTED_BRANCHES = {"main", "master"}
SEPARATORS = re.compile(r"&&|\|\||[;|\n]|\$\(|`")
GIT_OPTIONS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree"}


def project_root() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])


def git_output(arguments: list[str], cwd: Path) -> str:
    try:
        done = subprocess.run(
            ["git", *arguments], cwd=cwd, capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return done.stdout.strip()


def tokens_of(segment: str) -> list[str]:
    try:
        tokens = shlex.split(segment)
    except ValueError:
        tokens = segment.split()
    while tokens and (re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]) or tokens[0] == "sudo"):
        tokens = tokens[1:]
    return tokens


def git_subcommand(tokens: list[str]) -> list[str]:
    rest = tokens[1:]
    while rest and rest[0].startswith("-"):
        rest = rest[2:] if rest[0] in GIT_OPTIONS_WITH_VALUE else rest[1:]
    return rest


def short_flags(tokens: list[str]) -> str:
    return "".join(token[1:] for token in tokens if re.fullmatch(r"-[A-Za-z]+", token))


def rm_violation(tokens: list[str]) -> str | None:
    flags = short_flags(tokens)
    recursive = "r" in flags or "R" in flags or "--recursive" in tokens
    forced = "f" in flags or "--force" in tokens
    if recursive and forced:
        return "rm -rf is blocked. Delete specific paths without the force flag, or use git clean."
    return None


def targets_protected(refspecs: list[str]) -> bool:
    destinations = {spec.split(":")[-1].lstrip("+").removeprefix("refs/heads/") for spec in refspecs}
    return bool(destinations & PROTECTED_BRANCHES)


def push_violation(arguments: list[str], branch: str) -> str | None:
    if "--force" in arguments or "f" in short_flags(arguments) or any(a.startswith("+") for a in arguments):
        return "Force pushes are blocked. Use --force-with-lease on a feature branch if history must change."
    positional = [argument for argument in arguments if not argument.startswith("-")]
    refspecs = positional[1:]
    pushes_current_branch = not refspecs or "HEAD" in refspecs
    if targets_protected(refspecs) or (pushes_current_branch and branch in PROTECTED_BRANCHES):
        return "Direct pushes to main are blocked. Create a feature branch and deliver with /ship."
    return None


def merge_marker_matches(root: Path) -> bool:
    marker = root / ".claude" / ".ship-verified"
    if not marker.is_file():
        return False
    return marker.read_text(encoding="utf-8").strip() == git_output(["rev-parse", "HEAD"], root)


def git_violation(arguments: list[str], root: Path) -> str | None:
    if not arguments:
        return None
    branch = git_output(["rev-parse", "--abbrev-ref", "HEAD"], root)
    command, rest = arguments[0], arguments[1:]
    if command == "reset" and "--hard" in rest:
        return "git reset --hard is blocked. Use git stash, or git restore on specific paths."
    if command == "push":
        return push_violation(rest, branch)
    if command in {"commit", "merge", "rebase", "cherry-pick"} and branch in PROTECTED_BRANCHES:
        return f"git {command} on {branch} is blocked. Work on a feature branch and deliver with /ship."
    return None


def gh_violation(tokens: list[str], root: Path) -> str | None:
    if tokens[1:3] == ["pr", "merge"] and not merge_marker_matches(root):
        return "gh pr merge is allowed only from /ship, after verification of the current commit."
    return None


def violation(segment: str, root: Path) -> str | None:
    tokens = tokens_of(segment)
    if not tokens:
        return None
    program = Path(tokens[0]).name
    if program == "rm":
        return rm_violation(tokens)
    if program == "git":
        return git_violation(git_subcommand(tokens), root)
    if program == "gh":
        return gh_violation(tokens, root)
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    command = str((event.get("tool_input") or {}).get("command") or "")
    root = project_root()
    for segment in SEPARATORS.split(command):
        reason = violation(segment.strip(" ()"), root)
        if reason:
            print(reason, file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

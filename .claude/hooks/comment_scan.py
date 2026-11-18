#!/usr/bin/env python3
from __future__ import annotations

import ast
import io
import re
import subprocess
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path

PYTHON_SUFFIXES = {".py"}
SCRIPT_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
SOURCE_SUFFIXES = PYTHON_SUFFIXES | SCRIPT_SUFFIXES
IGNORED_PARTS = {"node_modules", ".venv", "dist", "build", "migrations", "__pycache__", "data"}

ALLOWED_PYTHON = re.compile(r"#\s*(type:\s*ignore\[[^\]]+\]|noqa:\s*[A-Z]+[0-9]+|pragma:\s*\S+)")
ALLOWED_SCRIPT = re.compile(r"^(//\s*biome-ignore\s+\S+|//\s*@ts-expect-error|///\s*<reference\s)")
SCRIPT_LITERALS = re.compile(
    r"""("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)""",
    re.DOTALL,
)
SCRIPT_COMMENT = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)
DOCSTRING_OWNERS = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    text: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: {self.text.strip()[:120]}"


def is_source(path: Path) -> bool:
    return path.suffix in SOURCE_SUFFIXES and not IGNORED_PARTS.intersection(path.parts)


def python_comment_findings(path: str, source: str) -> list[Finding]:
    findings = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type != tokenize.COMMENT:
            continue
        is_shebang = token.start[0] == 1 and token.string.startswith("#!")
        if is_shebang or ALLOWED_PYTHON.match(token.string):
            continue
        findings.append(Finding(path, token.start[0], token.line))
    return findings


def python_docstring_findings(path: str, source: str) -> list[Finding]:
    lines = source.splitlines()
    findings = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, DOCSTRING_OWNERS) or not node.body:
            continue
        first = node.body[0]
        is_docstring = (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        )
        if is_docstring:
            findings.append(Finding(path, first.lineno, "docstring: " + lines[first.lineno - 1]))
    return findings


def python_findings(path: str, source: str) -> list[Finding]:
    try:
        return python_comment_findings(path, source) + python_docstring_findings(path, source)
    except (SyntaxError, tokenize.TokenError, IndentationError):
        return []


def blank_out(match: re.Match[str]) -> str:
    return re.sub(r"[^\n]", " ", match.group(0))


def script_findings(path: str, source: str) -> list[Finding]:
    masked = SCRIPT_LITERALS.sub(blank_out, source)
    lines = source.splitlines()
    findings = []
    for match in SCRIPT_COMMENT.finditer(masked):
        line_number = masked.count("\n", 0, match.start()) + 1
        comment = source[match.start() : match.end()]
        if ALLOWED_SCRIPT.match(comment):
            continue
        findings.append(Finding(path, line_number, lines[line_number - 1]))
    return findings


def scan_text(path: str, source: str) -> list[Finding]:
    suffix = Path(path).suffix
    if suffix in PYTHON_SUFFIXES:
        return python_findings(path, source)
    if suffix in SCRIPT_SUFFIXES:
        return script_findings(path, source)
    return []


def scan_file(path: Path) -> list[Finding]:
    try:
        return scan_text(str(path), path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return []


def tracked_sources(roots: list[str]) -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", *roots],
        capture_output=True,
        text=True,
        check=False,
    )
    candidates = [Path(line) for line in listed.stdout.splitlines() if line]
    return [path for path in candidates if is_source(path) and path.is_file()]


def main(roots: list[str]) -> int:
    findings = [finding for path in tracked_sources(roots or ["."]) for finding in scan_file(path)]
    for finding in findings:
        print(finding.render())
    if findings:
        print(f"{len(findings)} comment(s) or docstring(s) found. See .claude/rules/no-comments.md")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

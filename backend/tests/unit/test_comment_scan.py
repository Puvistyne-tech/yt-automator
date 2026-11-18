from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCANNER_PATH = Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "comment_scan.py"


def load_scanner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("comment_scan", SCANNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SCANNER = load_scanner()


def findings(path: str, source: str) -> int:
    return len(SCANNER.scan_text(path, source))


@pytest.mark.parametrize(
    ("source", "count"),
    [
        ("#!/usr/bin/env python3\nx = 1\n", 0),
        ("x = 1  # type: ignore[attr-defined]\n", 0),
        ("import os  # noqa: E402\n", 0),
        ("import os  # noqa: E402, F401\n", 0),
        ('x = "a # not a comment"\n', 0),
        ("x = 1  # explain\n", 1),
        ("import os  # noqa: E402 explanation\n", 1),
        ("import os  # noqa\n", 1),
        ("x = 1  # type: ignore\n", 1),
        ("x = 1  # pragma: no cover\n", 1),
        ("x = 1\n#!/usr/bin/env python3\n", 1),
        ('def f() -> None:\n    """Explain."""\n', 1),
        ('"""Module docstring."""\n', 1),
    ],
)
def test_python_lines(source: str, count: int) -> None:
    assert findings("module.py", source) == count


@pytest.mark.parametrize(
    ("source", "count"),
    [
        ("// biome-ignore lint/suspicious/noExplicitAny: external type\nlet a: any;\n", 0),
        ("// @ts-expect-error\nlet a: number = 'x';\n", 0),
        ('/// <reference types="vite/client" />\n', 0),
        ('const url = "https://example.com";\n', 0),
        ("const s = '// not a comment';\n", 0),
        ("const t = `a // b ${x} /* c */`;\n", 0),
        ("const a = 1; // explain\n", 1),
        ("/* block */\nconst a = 1;\n", 1),
        ("// biome-ignore lint/style/noNonNullAssertion\nx!;\n", 1),
        ("// biome-ignore format: reason\nx;\n", 1),
        ("// @ts-ignore\nx;\n", 1),
    ],
)
def test_script_lines(source: str, count: int) -> None:
    assert findings("module.ts", source) == count

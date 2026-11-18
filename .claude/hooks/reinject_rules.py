#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

RULE_FILES = ("no-comments.md", "architecture.md")


def main() -> int:
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
    print("Core repository rules, restored after context compaction. They remain mandatory.\n")
    for name in RULE_FILES:
        rule = root / ".claude" / "rules" / name
        if rule.is_file():
            print(rule.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())

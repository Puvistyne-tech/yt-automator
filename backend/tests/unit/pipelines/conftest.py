from __future__ import annotations

from pathlib import Path

import pytest

from automator.pipelines.kids_story.art import lettering
from tests.fixtures.fonts import embedded_font


@pytest.fixture
def font_file(tmp_path: Path) -> Path:
    return embedded_font(tmp_path)


@pytest.fixture
def shaping(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    monkeypatch.setattr(lettering, "shaping_available", lambda: True)
    return monkeypatch

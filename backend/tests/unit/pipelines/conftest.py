from __future__ import annotations

from pathlib import Path

import pytest

from autotube.pipelines.narrated_video.art import lettering
from autotube.pipelines.narrated_video.scoring.inputs import ScoreInputs, gathered
from tests.fixtures.fonts import embedded_font
from tests.fixtures.kids_scoring import finished


@pytest.fixture
def font_file(tmp_path: Path) -> Path:
    return embedded_font(tmp_path)


@pytest.fixture
def shaping(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    monkeypatch.setattr(lettering, "shaping_available", lambda: True)
    return monkeypatch


@pytest.fixture(scope="module")
def inputs(tmp_path_factory: pytest.TempPathFactory) -> ScoreInputs:
    return gathered(finished(tmp_path_factory.mktemp("score")).context())

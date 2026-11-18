from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.kids_fakes import embedded_font


@pytest.fixture
def font_file(tmp_path: Path) -> Path:
    return embedded_font(tmp_path)

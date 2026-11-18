from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from autotube.pipelines.kids_story.settings.root import KidsStorySettings
from tests.fixtures.look_rig import STORED_SETTINGS, rendered_ass, rendered_command

GOLDEN = Path(__file__).parent / "golden" / "look_baseline.json"


def golden() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(GOLDEN.read_text(encoding="utf-8"))
    return loaded


def stored() -> KidsStorySettings:
    return KidsStorySettings.model_validate(STORED_SETTINGS)


@pytest.mark.parametrize("variant", ["episode", "short"])
def test_stored_settings_render_the_same_ffmpeg_command(variant: str) -> None:
    assert rendered_command(stored(), variant) == golden()["commands"][variant]


@pytest.mark.parametrize("variant", ["episode", "short"])
def test_stored_settings_render_the_same_ass_document(variant: str, tmp_path: Path) -> None:
    assert rendered_ass(stored(), tmp_path, variant) == golden()["ass"][variant]

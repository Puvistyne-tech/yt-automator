from __future__ import annotations

import json
from pathlib import Path

from autotube.pipelines.narrated_video.engine import ENGINE_ID
from autotube.pipelines.narrated_video.template.builtins import packaged_templates

REPOSITORY = Path(__file__).resolve().parents[4]
WEB_SEED = REPOSITORY / "web" / "src" / "api" / "mocks" / "fixtures" / "builtinTemplates.json"
SEEDED_FIELDS = ("id", "name", "description", "audience", "definition")
STALE_SEED = f"regenerate {WEB_SEED.name} from packaged_templates so mock mode matches the API"


def test_the_web_mock_seed_matches_the_packaged_builtins() -> None:
    seeded = json.loads(WEB_SEED.read_text(encoding="utf-8"))
    packaged = [template.model_dump(mode="json") for template in packaged_templates(ENGINE_ID)]
    expected = [{field: item[field] for field in SEEDED_FIELDS} for item in packaged]
    assert seeded == expected, STALE_SEED

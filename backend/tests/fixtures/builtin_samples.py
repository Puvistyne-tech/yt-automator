from __future__ import annotations

import json
from functools import partial
from pathlib import Path
from typing import Any

from tests.fixtures.kids_fakes import FakeWriter
from tests.fixtures.script_builders import scripted_writer

FOLDER = Path(__file__).resolve().parent / "builtin_scripts"
WRITTEN, TRANSLATED = "en", "ta"
SCENE_KEYS = ("visual", "action", "setting", "mood")


def sample_ids() -> list[str]:
    return sorted(path.stem for path in FOLDER.glob("*.json"))


def sample(template_id: str) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads((FOLDER / f"{template_id}.json").read_text("utf-8"))
    return loaded


def scene_draft(data: dict[str, Any], index: int, language: str) -> dict[str, Any]:
    scene = data["scenes"][index]
    shared = {key: scene.get(key, data.get(key, "")) for key in SCENE_KEYS}
    return {
        **shared,
        "characters": data["cast"],
        "camera": "push_in",
        "hero": index in data["short_scenes"],
        "sound_effects": [],
        "speaker": "narrator",
        **scene[language],
    }


def sample_draft(template_id: str, language: str = WRITTEN) -> dict[str, Any]:
    data = sample(template_id)
    scenes = [scene_draft(data, index, language) for index in range(len(data["scenes"]))]
    return {
        **data["text"][language],
        "scenes": scenes,
        "short_scenes": data["short_scenes"],
        "thumbnail": data["thumbnail"],
    }


def sample_text(template_id: str, language: str = TRANSLATED) -> dict[str, Any]:
    data = sample(template_id)
    lines = [scene[language] for scene in data["scenes"]]
    labels = [{key: value for key, value in line.items() if key != "narration"} for line in lines]
    return {
        **data["text"][language],
        "narrations": [line["narration"] for line in lines],
        "scene_labels": labels if any(labels) else None,
    }


def sample_writer(template_id: str) -> FakeWriter:
    return scripted_writer(partial(sample_draft, template_id), partial(sample_text, template_id))

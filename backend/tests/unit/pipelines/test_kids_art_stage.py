from __future__ import annotations

from pathlib import Path

import pytest

from automator.domain.capabilities import ImageRequest, TextRequest
from automator.domain.model_base import JsonObject
from automator.pipelines.kids_story.art.prompts import parse_choice
from tests.fixtures.kids_data import (
    StageRig,
    is_judge,
    is_translation,
    meta_of,
    quick_settings,
    run_chain,
    smart_writer,
    story_answer,
    tamil_answer,
)
from tests.fixtures.kids_fakes import FakeImages, FakeProviders, FakeWriter


def episode_visuals(rig: StageRig) -> dict[int, JsonObject]:
    return {
        int(str(item.meta["scene"])): item.meta
        for item in meta_of(rig, "visual")
        if item.variant == "episode" and "scene" in item.meta
    }


def art_run(
    root: Path, writer: FakeWriter | None = None, **sections: dict[str, object]
) -> StageRig:
    rig = StageRig(
        root, settings=quick_settings(**sections), providers=FakeProviders(writer=writer)
    )
    return run_chain(rig, "art")


@pytest.mark.parametrize(
    ("answer", "chosen"), [("banana", 0), ("0", 0), ("7", 0), ("I pick 2", 1), ("1", 0)]
)
def test_parse_choice_keeps_only_valid_candidate_numbers(answer: str, chosen: int) -> None:
    assert parse_choice(answer, 2) == chosen


def test_judge_is_asked_only_for_scenes_with_several_candidates(tmp_path: Path) -> None:
    writer = smart_writer("2")
    visuals = episode_visuals(art_run(tmp_path, writer))
    assert sum(1 for request in writer.requests if is_judge(request)) == 2
    assert visuals[0]["candidate"] == 1 and visuals[6]["candidate"] == 1
    assert {visuals[index]["candidate"] for index in (1, 2, 3, 4, 5, 7, 8)} == {0}


def test_a_failing_judge_keeps_the_first_picture(tmp_path: Path) -> None:
    def respond(request: TextRequest) -> str:
        if is_judge(request):
            raise RuntimeError("vision offline")
        return tamil_answer() if is_translation(request) else story_answer()

    rig = art_run(tmp_path, FakeWriter(respond))
    assert {meta["candidate"] for meta in episode_visuals(rig).values()} == {0}
    assert any("picture judge failed" in line and "vision offline" in line for line in rig.logs)


def test_no_language_model_means_no_judge(tmp_path: Path) -> None:
    rig = art_run(tmp_path, visuals={"use_vision_judge": True})
    assert {meta["candidate"] for meta in episode_visuals(rig).values()} == {0}
    assert any("no language model for picking pictures" in line for line in rig.logs)


def test_turned_off_judge_never_sees_pictures(tmp_path: Path) -> None:
    writer = smart_writer("2")
    rig = art_run(tmp_path, writer, visuals={"use_vision_judge": False})
    assert not any(is_judge(request) for request in writer.requests)
    assert {meta["candidate"] for meta in episode_visuals(rig).values()} == {0}


def scene_requests(images: FakeImages) -> list[ImageRequest]:
    return [
        request for request in images.requests if (request.width, request.height) == (1280, 720)
    ]


def test_character_sheets_are_drawn_once_and_referenced(tmp_path: Path) -> None:
    rig = art_run(tmp_path, smart_writer())
    sheets = meta_of(rig, "character_sheet")
    assert sorted(str(item.meta["character"]) for item in sheets) == [
        "aamai_thatha",
        "chinnu",
        "kutty",
        "mittu",
    ]
    first_scene = scene_requests(rig.providers.images)[0]
    assert [path.name for path in first_scene.reference_images] == ["sheet-kutty.png"]


def test_character_sheets_can_be_turned_off(tmp_path: Path) -> None:
    rig = art_run(tmp_path, smart_writer(), visuals={"character_sheets": False})
    assert meta_of(rig, "character_sheet") == []
    assert not any(request.reference_images for request in rig.providers.images.requests)


def test_native_vertical_pictures_are_drawn_portrait(tmp_path: Path) -> None:
    rig = art_run(tmp_path, smart_writer(), visuals={"short_art_mode": "native"})
    shorts = [item for item in meta_of(rig, "visual") if item.variant == "short"]
    portrait = [r for r in rig.providers.images.requests if (r.width, r.height) == (720, 1280)]
    assert len(portrait) == len(shorts) == 5


class CorruptScenes(FakeImages):
    def generate(self, request: ImageRequest, output: Path) -> Path:
        if (request.width, request.height) != (1280, 720):
            return super().generate(request, output)
        self.requests.append(request)
        output.write_bytes(b"not a picture")
        return output


def test_a_picture_that_cannot_be_cropped_is_redrawn(tmp_path: Path) -> None:
    providers = FakeProviders(writer=smart_writer(), images=CorruptScenes())
    rig = run_chain(StageRig(tmp_path, providers=providers), "art")
    assert any("could not crop scene-0-c" in line for line in rig.logs)
    portrait = [r for r in providers.images.requests if (r.width, r.height) == (720, 1280)]
    assert len(portrait) == 5


@pytest.mark.parametrize(("intro", "outro"), [(True, False), (False, True), (False, False)])
def test_cards_follow_their_switches(tmp_path: Path, intro: bool, outro: bool) -> None:
    rig = art_run(tmp_path, episode={"intro_card": intro, "outro_card": outro})
    cards = {
        (item.language, item.meta["card"]) for item in meta_of(rig, "visual") if "card" in item.meta
    }
    wanted = {name for name, on in (("intro", intro), ("outro", outro)) if on}
    assert cards == {(language, name) for language in ("en", "ta") for name in wanted}

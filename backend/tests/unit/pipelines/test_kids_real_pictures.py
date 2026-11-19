from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import pytest

from autotube.domain.capabilities import Capability
from autotube.domain.provider_fallbacks import ProviderFallback
from autotube.domain.run_parts import Artifact
from autotube.pipelines.narrated_video.art.stand_ins import STAND_IN_FOR
from autotube.pipelines.narrated_video.artifacts import EPISODE, Role, with_role
from autotube.pipelines.narrated_video.scoring.inputs import ScoreInputs, gathered
from autotube.pipelines.narrated_video.scoring.output_items import real_pictures
from tests.fixtures.kids_fakes import FakeProviders
from tests.fixtures.kids_scoring import finished, required


def scene_pictures(artifacts: Sequence[Artifact]) -> list[Artifact]:
    return [a for a in with_role(artifacts, Role.VISUAL, variant=EPISODE) if "scene" in a.meta]


def with_stand_ins_at(inputs: ScoreInputs, count: int) -> ScoreInputs:
    replaced = {a.id for a in scene_pictures(inputs.artifacts)[:count]}
    stand_in = {STAND_IN_FOR: ["mflux"]}
    artifacts = tuple(
        a.model_copy(update={"meta": {**a.meta, **stand_in}}) if a.id in replaced else a
        for a in inputs.artifacts
    )
    return replace(inputs, artifacts=artifacts)


@pytest.mark.parametrize("count", [0, 1])
def test_real_pictures_scores_the_share_drawn_by_the_chosen_model(
    inputs: ScoreInputs, count: int
) -> None:
    total = len(scene_pictures(inputs.artifacts))
    item = required(real_pictures(with_stand_ins_at(inputs, count)))
    assert item.score == pytest.approx(100 * (total - count) / total)
    assert item.detail == (
        f"{count} of {total} episode pictures are stand-ins drawn after mflux failed"
        if count
        else f"all {total} episode pictures came from the chosen image model"
    )


@pytest.mark.parametrize(("used", "marked"), [("fake-image", True), ("other-image", False)])
def test_the_art_stage_marks_pictures_drawn_after_an_image_fallback(
    tmp_path: Path, used: str, marked: bool
) -> None:
    gated = ProviderFallback(capability=Capability.IMAGE, failed="mflux", used=used, reason="403")
    rig = finished(tmp_path, FakeProviders(fallen_back=[gated]), ("en",))
    pictures = scene_pictures(rig.artifacts)
    assert pictures and all((STAND_IN_FOR in a.meta) is marked for a in pictures)
    candidates = with_role(rig.artifacts, Role.CANDIDATE)
    assert candidates
    assert not any(STAND_IN_FOR in a.meta for a in candidates)
    item = required(real_pictures(gathered(rig.context())))
    assert item.score == (0 if marked else 100)

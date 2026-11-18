from __future__ import annotations

from pathlib import Path

import pytest

from automator.domain.run_enums import ArtifactKind
from tests.fixtures.kids_data import StageRig, meta_of, quick_settings, roles, run_chain
from tests.fixtures.kids_fakes import FakeProviders


@pytest.mark.parametrize(
    ("languages", "short"),
    [(("en",), False), (("en",), True), (("ta",), False), (("ta",), True), (("en", "ta"), False)],
)
def test_languages_and_variants_produce_exactly_their_outputs(
    tmp_path: Path, languages: tuple[str, ...], short: bool
) -> None:
    providers = FakeProviders()
    settings = quick_settings(short={"enabled": short})
    rig = run_chain(StageRig(tmp_path, settings=settings, languages=languages, providers=providers))
    variants = ("episode", "short") if short else ("episode",)
    expected = sorted(((code, variant) for code in languages for variant in variants), key=str)
    for kind in (ArtifactKind.THUMBNAIL, ArtifactKind.METADATA, ArtifactKind.SUBTITLE):
        assert roles(rig, kind) == expected
    finals = sorted(
        ((item.language, item.variant) for item in meta_of(rig, "final_video")), key=str
    )
    assert finals == expected
    assert [item.language for item in meta_of(rig, "story")] == list(languages)
    assert {request.language for request in providers.speech.requests} == set(languages)
    has_hooks = any(item.filename.endswith("-hook.wav") for item in rig.artifacts)
    assert has_hooks is short
    assert any(item.variant == "short" for item in meta_of(rig, "clip")) is short
    assert {item.variant for item in meta_of(rig, "music")} == set(variants)

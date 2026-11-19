from __future__ import annotations

from pathlib import Path

from autotube.domain.quality import ScoreItem
from tests.fixtures.kids_data import StageRig, run_chain
from tests.fixtures.kids_fakes import FakeProviders


def finished(
    root: Path, providers: FakeProviders | None = None, languages: tuple[str, ...] = ("en", "ta")
) -> StageRig:
    return run_chain(StageRig(root, providers=providers or FakeProviders(), languages=languages))


def required(item: ScoreItem | None) -> ScoreItem:
    assert item is not None
    return item

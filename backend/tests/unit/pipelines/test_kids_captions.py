from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures.kids_data import StageRig, meta_of, quick_settings, run_chain
from tests.fixtures.kids_fakes import FakeProviders, FakeSpeech


def captioned(root: Path, **subtitles: object) -> StageRig:
    settings = quick_settings(subtitles=subtitles, short={"enabled": False})
    return run_chain(StageRig(root, settings=settings, languages=("en",)))


def test_turned_off_subtitles_make_no_files_and_burn_nothing(tmp_path: Path) -> None:
    rig = captioned(tmp_path, enabled=False, burn_in_episode=True)
    assert not (tmp_path / "subtitles").exists()
    assert meta_of(rig, "captions") == [] and meta_of(rig, "caption_track") == []
    [final] = meta_of(rig, "final_video")
    assert final.meta["burned_subtitles"] is False
    assert rig.providers.media.compositions["en-episode.mp4"].subtitles is None


def test_burned_subtitles_are_recorded(tmp_path: Path) -> None:
    rig = captioned(tmp_path, burn_in_episode=True)
    [final] = meta_of(rig, "final_video")
    assert final.meta["burned_subtitles"] is True


@pytest.mark.parametrize(("upload", "tracks"), [(True, 1), (False, 0)])
def test_caption_tracks_follow_the_upload_switch(tmp_path: Path, upload: bool, tracks: int) -> None:
    rig = captioned(tmp_path, upload_captions=upload)
    assert len(meta_of(rig, "captions")) == 1
    assert len(meta_of(rig, "caption_track")) == tracks


def test_missing_word_timings_give_no_cues_and_no_caption_track(tmp_path: Path) -> None:
    providers = FakeProviders(speech=FakeSpeech(with_words=False))
    settings = quick_settings(short={"enabled": False})
    rig = run_chain(StageRig(tmp_path, settings=settings, languages=("en",), providers=providers))
    [captions] = meta_of(rig, "captions")
    assert captions.size_bytes == 0
    assert meta_of(rig, "caption_track") == []
    assert any("no caption track for en episode" in line for line in rig.logs)

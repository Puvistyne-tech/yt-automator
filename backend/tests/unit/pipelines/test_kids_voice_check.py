from __future__ import annotations

from pathlib import Path

import pytest

from autotube.domain.capabilities import Speech, SpeechRequest
from autotube.pipelines.narrated_video.settings.audio import NarrationCheck
from autotube.pipelines.narrated_video.stages.story import StoryStage
from autotube.pipelines.narrated_video.stages.voice import VoiceStage
from autotube.pipelines.narrated_video.stages.voice_check import checks_language
from autotube.pipelines.narrated_video.text.error_rate import character_error_rate
from tests.fixtures.kids_data import StageRig, meta_of, quick_settings
from tests.fixtures.kids_fakes import FakeProviders, FakeSpeech

TAMIL = "ஒரு காட்டில், ஒரு யானை!"


@pytest.mark.parametrize(
    ("reference", "heard", "rate"),
    [
        ("hello", "hallo", 0.2),
        (TAMIL, "ஒரு  காட்டில் ஒரு யானை", 0.0),
        ("Hello, World.", "hello world", 0.0),
        ("\u0b95\u0bca", "\u0b95\u0bc6\u0bbe", 0.0),
        ("abc", "", 1.0),
        ("", "", 0.0),
        ("", "abc", 1.0),
        ("abc", "abcdef", 1.0),
        ("ab", "abcdef", 2.0),
    ],
)
def test_character_error_rate(reference: str, heard: str, rate: float) -> None:
    assert character_error_rate(reference, heard) == pytest.approx(rate)


def garbled(text: str, share: float | None) -> str:
    if share is None:
        return ""
    wrong = round(share * len(text))
    return "x" * wrong + text[wrong:]


class MishearingSpeech(FakeSpeech):
    def __init__(self, shares: list[float | None]) -> None:
        super().__init__()
        self.shares = shares

    def synthesize(self, request: SpeechRequest, output: Path) -> Speech:
        speech = super().synthesize(request, output)
        attempt = len(self.requests) - 1
        share = self.shares[attempt] if attempt < len(self.shares) else 0.0
        return speech.model_copy(update={"transcript": garbled(request.text, share)})


def checked_rig(root: Path, shares: list[float | None], **check: object) -> StageRig:
    settings = quick_settings(
        voice={"include_intro": False, "include_outro": False, "quality_check": check},
        short={"enabled": False},
    )
    providers = FakeProviders(speech=MishearingSpeech(shares))
    rig = StageRig(root, settings=settings, languages=("ta",), providers=providers)
    rig.run(StoryStage())
    rig.run(VoiceStage())
    return rig


def first_line(rig: StageRig) -> dict[str, object]:
    return dict(meta_of(rig, "narration")[0].meta)


def test_a_clean_line_passes_on_the_first_try(tmp_path: Path) -> None:
    rig = checked_rig(tmp_path, [0.1])
    assert len(rig.providers.speech.requests) == 9
    assert first_line(rig)["attempts"] == 1
    assert first_line(rig)["error_rate"] == pytest.approx(0.1, abs=0.06)
    note = next(line for line in rig.logs if line.startswith("narration check ta scene-0 "))
    assert note.endswith("after 1 attempt(s)")
    assert not any("error rate" in line for line in rig.book.warnings())


def test_a_garbled_line_is_retried_and_the_best_attempt_kept(tmp_path: Path) -> None:
    rig = checked_rig(tmp_path, [0.9, 0.3, 0.5], retries=2)
    meta = first_line(rig)
    assert len(rig.providers.speech.requests) == 11
    assert meta["attempts"] == 3
    assert meta["error_rate"] == pytest.approx(0.3, abs=0.06)
    assert meta_of(rig, "narration")[0].filename.endswith("ta-scene-0-retry1.wav")
    assert any("still above" in line for line in rig.book.warnings())


@pytest.mark.parametrize("check", [{"enabled": False}, {"languages": ["en"]}])
def test_a_switched_off_or_unlisted_language_is_not_checked(
    tmp_path: Path, check: dict[str, object]
) -> None:
    rig = checked_rig(tmp_path, [0.9], **check)
    assert len(rig.providers.speech.requests) == 9
    assert first_line(rig)["error_rate"] is None


def test_a_voice_without_a_transcript_skips_the_check_with_a_note(tmp_path: Path) -> None:
    rig = checked_rig(tmp_path, [None] * 9)
    assert len(rig.providers.speech.requests) == 9
    assert first_line(rig)["error_rate"] is None
    assert any("no transcript" in line for line in rig.logs)


def test_a_retry_that_passes_stops_retrying(tmp_path: Path) -> None:
    rig = checked_rig(tmp_path, [0.9, 0.0], retries=2)
    assert len(rig.providers.speech.requests) == 10
    assert first_line(rig)["attempts"] == 2
    assert first_line(rig)["error_rate"] == 0.0


@pytest.mark.parametrize(
    ("shares", "retries", "attempts"), [([0.9, None, None], 2, 3), ([0.9], 0, 1)]
)
def test_a_line_that_never_improves_keeps_its_first_attempt(
    tmp_path: Path, shares: list[float | None], retries: int, attempts: int
) -> None:
    rig = checked_rig(tmp_path, shares, retries=retries)
    assert first_line(rig)["attempts"] == attempts
    assert first_line(rig)["error_rate"] == pytest.approx(0.9, abs=0.06)
    assert meta_of(rig, "narration")[0].filename.endswith("ta-scene-0.wav")
    assert any("still above" in line for line in rig.book.warnings())


@pytest.mark.parametrize(("language", "checked"), [("ta-IN", True), ("TA", True), ("en-US", False)])
def test_checks_language_reads_the_primary_subtag(language: str, checked: bool) -> None:
    assert checks_language(NarrationCheck(), language) is checked

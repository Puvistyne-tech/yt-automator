from __future__ import annotations

import json
from pathlib import Path

import pytest

from autotube.domain.capabilities import Capability, SpeechRequest, TimingSource, WordTiming
from autotube.infrastructure.providers.host import HostProbe
from autotube.infrastructure.providers.tts.mlx_audio_voice import (
    WORKER_SCRIPT,
    MlxAudioOptions,
    MlxAudioSpeech,
)
from autotube.infrastructure.providers.tts.whisper_aligner import AlignmentOptions
from tests.unit.infrastructure.providers.fakes import (
    RecordingRunner,
    host,
    local_catalog,
    make_context,
    write_tone,
)

PYTHON = "/venv/bin/python"
MODELS = "/models"
OPTIONS = MlxAudioOptions(
    python=PYTHON, models_root=MODELS, alignment=AlignmentOptions(enabled=False)
)


class HelloAligner:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, str]] = []

    def recognise(self, audio: Path, language: str) -> list[WordTiming] | None:
        self.calls.append((audio, language))
        return [WordTiming(word="Hello", start_seconds=0.1, end_seconds=0.4)]


def writes_job_output(seconds: float) -> RecordingRunner:
    runner = RecordingRunner()

    def effect(_command: list[str]) -> None:
        write_tone(Path(json.loads(runner.calls[-1].stdin or "")["output"]), seconds, 24000)

    runner.effect = effect
    return runner


def adapter(
    tmp_path: Path, runner: RecordingRunner, options: MlxAudioOptions, aligner: HelloAligner
) -> MlxAudioSpeech:
    return MlxAudioSpeech(options, make_context(tmp_path, runner=runner), aligner=aligner)


def test_tamil_uses_its_default_preset_in_the_model_python(tmp_path: Path) -> None:
    runner = writes_job_output(1.5)
    output = tmp_path / "speech" / "ta.wav"
    request = SpeechRequest(text="ஒரு காட்டில் யானை", language="ta-IN")
    speech = adapter(tmp_path, runner, OPTIONS, HelloAligner()).synthesize(request, output)
    call = runner.calls[0]
    assert call.command == [PYTHON, "-I", str(WORKER_SCRIPT)]
    assert call.timeout_seconds == 900.0
    assert call.env == {"HF_HOME": "/Volumes/backup/bakeoff-models/hf", "HF_HUB_OFFLINE": "1"}
    assert json.loads(call.stdin or "") == {
        "model_dir": f"{MODELS}/aruntemme__maya2-native-mlx-8bit",
        "text": "ஒரு காட்டில் யானை",
        "kwargs": {"voice": "Kayal", "lang_code": "ta"},
        "sentence_split": False,
        "pause_ms": 0,
        "output": str(output),
    }
    assert speech.duration_seconds == pytest.approx(1.5)
    assert speech.timing_source is TimingSource.ESTIMATE
    assert [word.word for word in speech.words] == ["ஒரு", "காட்டில்", "யானை"]


def test_named_preset_passes_its_split_and_pause(tmp_path: Path) -> None:
    runner = writes_job_output(1.0)
    request = SpeechRequest(text="Hi.", language="ta", voice="svara_male")
    adapter(tmp_path, runner, OPTIONS, HelloAligner()).synthesize(request, tmp_path / "s.wav")
    job = json.loads(runner.calls[0].stdin or "")
    assert job["model_dir"] == f"{MODELS}/mlx-community__svara-tts-v1-4bit"
    assert (job["sentence_split"], job["pause_ms"]) == (True, 250)
    assert job["kwargs"] == {"voice": "Tamil (Male)"}


def test_english_defaults_to_the_storyteller_and_aligns(tmp_path: Path) -> None:
    runner = writes_job_output(1.0)
    options = OPTIONS.model_copy(update={"alignment": AlignmentOptions()})
    aligner = HelloAligner()
    speech = adapter(tmp_path, runner, options, aligner).synthesize(
        SpeechRequest(text="Hello", language="en"), tmp_path / "e.wav"
    )
    assert aligner.calls == [(tmp_path / "e.wav", "en")]
    job = json.loads(runner.calls[0].stdin or "")
    assert job["model_dir"].endswith("Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit")
    assert job["kwargs"]["lang_code"] == "English"
    assert speech.timing_source is TimingSource.ALIGNMENT
    assert speech.words == (WordTiming(word="Hello", start_seconds=0.1, end_seconds=0.4),)


@pytest.mark.parametrize(
    ("paths", "reason"),
    [
        (frozenset(), f"mlx-audio Python not found at {PYTHON}"),
        (frozenset({PYTHON}), f"mlx-audio models folder not found at {MODELS}"),
        (frozenset({PYTHON, MODELS}), None),
    ],
)
def test_availability_needs_the_python_and_the_models(
    tmp_path: Path, paths: frozenset[str], reason: str | None
) -> None:
    context = make_context(tmp_path, probe=host(paths=paths))
    assert MlxAudioSpeech(OPTIONS, context).available() == reason


def test_without_the_mac_paths_tts_resolves_to_a_fallback(tmp_path: Path) -> None:
    resolver = local_catalog(tmp_path).resolver([])
    assert resolver.resolve(Capability.TTS).provider_id == "espeak"
    skipped = resolver.skipped[Capability.TTS]
    assert any(reason.startswith("mlx_audio: mlx-audio Python not found") for reason in skipped)


def test_host_probe_checks_real_paths(tmp_path: Path) -> None:
    assert HostProbe().missing_path(str(tmp_path), "folder") is None
    assert HostProbe().missing_path(str(tmp_path / "gone"), "folder") == (
        f"folder not found at {tmp_path / 'gone'}"
    )


def test_default_presets_cover_the_chosen_voices() -> None:
    languages = {key: preset.languages for key, preset in MlxAudioOptions().presets.items()}
    assert languages == {
        "warm_storyteller": ["en"],
        "qwen3_narrator": ["en"],
        "news_reader": ["en"],
        "kayal": ["ta"],
        "vaidehi": ["ta"],
        "svara_male": ["ta"],
    }

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from autotube.infrastructure.providers.tts.mlx_audio_presets import default_presets
from tests.fixtures.setup_script import hermetic_bin, planned, setup_run, stub

VOICE_MODELS = (
    "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-8bit",
    "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit",
    "mlx-community/chatterbox-turbo-4bit",
    "aruntemme/maya2-native-mlx-8bit",
    "mlx-community/svara-tts-v1-4bit",
    "mlx-community/whisper-large-v3-turbo",
)
CACHED_REPOS = (
    "mlx-community/S3TokenizerV2",
    "kyutai/moshiko-pytorch-bf16",
    "aufklarer/SpeechBrain-ECAPA-VoxCeleb-20M-MLX",
    "mlx-community/snac_24khz",
)
SVARA = "mlx-community__svara-tts-v1-4bit"
HF_LOG_STUB = 'echo "$@" >> "$HF_LOG"; [ "$3" = --local-dir ] && mkdir -p "$4"; exit 0'
MAC_UNAME = 'case "$1" in -s) echo Darwin ;; -m) echo arm64 ;; *) echo Darwin ;; esac'

pytestmark = pytest.mark.integration


def folder_name(repo: str) -> str:
    return repo.replace("/", "__")


def hf_download(data: Path, repo: str) -> str:
    return f"env HF_HOME={data / 'hf'} {data / 'venvs' / 'mlx' / 'bin' / 'hf'} download {repo}"


def test_voices_plan_downloads_every_model_and_cached_repo(tmp_path: Path) -> None:
    plan = planned(tmp_path, "--voices", "--no-base")
    data = tmp_path / "home" / "data"
    for repo in VOICE_MODELS:
        target = data / "models" / folder_name(repo)
        assert f"{hf_download(data, repo)} --local-dir {target}" in plan
    for repo in CACHED_REPOS:
        assert f"would run: {hf_download(data, repo)}\n" in plan
    assert {preset.model for preset in default_presets().values()} <= set(
        map(folder_name, VOICE_MODELS)
    )
    assert "mlx-audio==0.6.6 mlx-whisper huggingface_hub[cli]" in plan
    assert "hf auth login" in plan


def test_video_plan_installs_ltx_and_links_its_command(tmp_path: Path) -> None:
    plan = planned(tmp_path, "--video", "--no-base")
    data = tmp_path / "home" / "data"
    clone = data / "tools" / "ltx-2-mlx"
    assert f"git clone https://github.com/dgrauet/ltx-2-mlx {clone}" in plan
    assert f"-e {clone}/packages/ltx-core-mlx -e {clone}/packages/ltx-pipelines-mlx" in plan
    model = data / "models" / "reverie-studio__ltx-2.5-mlx-q4-distilled"
    assert f"download reverie-studio/ltx-2.5-mlx-q4-distilled --local-dir {model}" in plan
    assert f"ln -sf {data}/venvs/mlx/bin/ltx-2-mlx {tmp_path}/home/.local/bin/ltx-2-mlx" in plan


def mlx_venv(tmp_path: Path) -> Path:
    folder = hermetic_bin(tmp_path)
    for name in ("uv", "git"):
        stub(folder, name)
    stub(folder, "uname", MAC_UNAME)
    venv_bin = tmp_path / "home" / "data" / "venvs" / "mlx" / "bin"
    venv_bin.mkdir(parents=True)
    (venv_bin / "python").symlink_to(sys.executable)
    stub(venv_bin, "hf", HF_LOG_STUB)
    return tmp_path / "hf.log"


def voices_run(tmp_path: Path, extra: dict[str, str]) -> str:
    log = tmp_path / "hf.log"
    result = setup_run(tmp_path, "--voices", "--no-base", extra={"HF_LOG": str(log)} | extra)
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_models_from_links_existing_weights_and_cache(tmp_path: Path) -> None:
    log = mlx_venv(tmp_path)
    source = tmp_path / "bakeoff"
    for repo in VOICE_MODELS:
        (source / "local" / folder_name(repo)).mkdir(parents=True)
    (source / "local" / SVARA / "config.json").write_text("{}", encoding="utf-8")
    (source / "hf").mkdir()
    voices_run(tmp_path, {"AUTOTUBE_MODELS_FROM": str(source)})
    data = tmp_path / "home" / "data"
    for repo in VOICE_MODELS:
        linked = data / "models" / folder_name(repo)
        assert linked.readlink() == source / "local" / folder_name(repo)
    assert (data / "hf").readlink() == source / "hf"
    assert "--local-dir" not in log.read_text(encoding="utf-8")


def test_rerun_skips_present_models_and_fixes_the_svara_tokenizer(tmp_path: Path) -> None:
    log = mlx_venv(tmp_path)
    svara = tmp_path / "home" / "data" / "models" / SVARA
    svara.mkdir(parents=True)
    (svara / "config.json").write_text('{"tokenizer_name": "x", "keep": 1}', encoding="utf-8")
    voices_run(tmp_path, {})
    assert log.read_text(encoding="utf-8").count("--local-dir") == len(VOICE_MODELS) - 1
    rerun = voices_run(tmp_path, {})
    assert log.read_text(encoding="utf-8").count("--local-dir") == len(VOICE_MODELS) - 1
    assert f"model {VOICE_MODELS[0]} is already present" in rerun
    config = json.loads((svara / "config.json").read_text(encoding="utf-8"))
    assert config == {"tokenizer_name": str(svara), "keep": 1}

from __future__ import annotations

import json
from pathlib import Path

import pytest

from autotube.infrastructure.providers.tts.mlx_audio_presets import default_presets
from tests.fixtures.setup_script import folder_name, logged, mlx_host, mlx_run, planned, stub

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

pytestmark = pytest.mark.integration


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
    svara = data / "models" / SVARA
    assert f"would set tokenizer_name in {svara}/config.json to {svara}" in plan


def test_video_plan_installs_ltx_and_links_its_command(tmp_path: Path) -> None:
    plan = planned(tmp_path, "--video", "--no-base")
    data = tmp_path / "home" / "data"
    clone = data / "tools" / "ltx-2-mlx"
    assert f"git clone https://github.com/dgrauet/ltx-2-mlx {clone}" in plan
    assert f"-e {clone}/packages/ltx-core-mlx -e {clone}/packages/ltx-pipelines-mlx" in plan
    model = data / "models" / "reverie-studio__ltx-2.5-mlx-q4-distilled"
    assert f"download reverie-studio/ltx-2.5-mlx-q4-distilled --local-dir {model}" in plan
    assert f"ln -sf {data}/venvs/mlx/bin/ltx-2-mlx {tmp_path}/home/.local/bin/ltx-2-mlx" in plan


def test_mlx_groups_share_one_venv_and_one_login_note(tmp_path: Path) -> None:
    plan = planned(tmp_path, "--images", "--video", "--voices", "--no-base")
    assert plan.count("would run: uv venv") == 1
    assert plan.count("    note: If a download is refused") == 1


def test_video_stops_when_git_is_missing(tmp_path: Path) -> None:
    mlx_host(tmp_path, ready=True, tools=("uv",))
    result = mlx_run(tmp_path, "--video")
    assert result.returncode == 1
    assert "git is missing" in result.stderr


def test_video_reuses_a_clone_and_links_the_command(tmp_path: Path) -> None:
    data = mlx_host(tmp_path, ready=True)
    clone = data / "tools" / "ltx-2-mlx"
    (clone / ".git").mkdir(parents=True)
    assert mlx_run(tmp_path, "--video").returncode == 0
    assert "git clone" not in logged(tmp_path)
    assert f"uv pip install --python {data}/venvs/mlx/bin/python -e {clone}" in logged(tmp_path)
    link = tmp_path / "home" / ".local" / "bin" / "ltx-2-mlx"
    assert link.readlink() == data / "venvs" / "mlx" / "bin" / "ltx-2-mlx"
    stub(data / "venvs" / "mlx" / "bin", "ltx-2-mlx")
    rerun = mlx_run(tmp_path, "--video").stdout
    assert f"ltx-2-mlx in {data}/venvs/mlx is already present" in rerun
    assert f"{link} is already present" in rerun


def test_models_from_links_existing_weights_and_cache(tmp_path: Path) -> None:
    data = mlx_host(tmp_path, ready=True)
    source = tmp_path / "bakeoff"
    for repo in VOICE_MODELS:
        (source / "local" / folder_name(repo)).mkdir(parents=True)
    (source / "local" / SVARA / "config.json").write_text("{}", encoding="utf-8")
    (source / "hf").mkdir()
    assert (
        mlx_run(tmp_path, "--voices", extra={"AUTOTUBE_MODELS_FROM": str(source)}).returncode == 0
    )
    for repo in VOICE_MODELS:
        linked = data / "models" / folder_name(repo)
        assert linked.readlink() == source / "local" / folder_name(repo)
    assert (data / "hf").readlink() == source / "hf"
    assert "--local-dir" not in logged(tmp_path)


def test_models_from_partial_links_one_and_downloads_the_rest(tmp_path: Path) -> None:
    data = mlx_host(tmp_path, ready=True)
    source = tmp_path / "bakeoff"
    (source / "local" / folder_name(VOICE_MODELS[0])).mkdir(parents=True)
    result = mlx_run(tmp_path, "--voices", extra={"AUTOTUBE_MODELS_FROM": str(source)})
    assert result.returncode == 0, result.stderr
    assert (data / "models" / folder_name(VOICE_MODELS[0])).is_symlink()
    assert logged(tmp_path).count("--local-dir") == len(VOICE_MODELS) - 1
    for repo in CACHED_REPOS:
        assert f"hf download {repo}\n" in logged(tmp_path)
    assert not (data / "hf").is_symlink()
    assert "the Svara tokenizer fix was skipped" in result.stdout


def test_present_venv_models_and_cached_repos_are_skipped(tmp_path: Path) -> None:
    data = mlx_host(tmp_path, ready=True)
    for repo in VOICE_MODELS:
        (data / "models" / folder_name(repo)).mkdir(parents=True)
    for repo in CACHED_REPOS:
        (data / "hf" / "hub" / f"models--{repo.replace('/', '--')}").mkdir(parents=True)
    result = mlx_run(tmp_path, "--voices")
    assert result.returncode == 0, result.stderr
    assert logged(tmp_path) == ""
    assert f"mlx venv at {data}/venvs/mlx is already present" in result.stdout
    assert f"cached repo {CACHED_REPOS[0]} is already present" in result.stdout


def test_svara_fix_points_the_tokenizer_at_its_folder(tmp_path: Path) -> None:
    data = mlx_host(tmp_path, ready=False)
    svara = data / "models" / SVARA
    svara.mkdir(parents=True)
    (svara / "config.json").write_text('{"tokenizer_name": "x", "keep": 1}', encoding="utf-8")
    assert mlx_run(tmp_path, "--voices").returncode == 0
    assert f"uv venv --python 3.12 {data}/venvs/mlx" not in logged(tmp_path)
    assert f"uv pip install --python {data}/venvs/mlx/bin/python mlx-audio" in logged(tmp_path)
    config = json.loads((svara / "config.json").read_text(encoding="utf-8"))
    assert config == {"tokenizer_name": str(svara), "keep": 1}

from __future__ import annotations

from collections.abc import Mapping

from automator.infrastructure.config import load_config
from automator.infrastructure.providers.llm.ollama import OllamaOptions
from automator.infrastructure.providers.music.ace_step import ace_step_venv
from automator.infrastructure.providers.music.library_music import default_music_folder


def setup_defaults(environ: Mapping[str, str]) -> dict[str, str]:
    config = load_config(environ)
    ollama = OllamaOptions()
    return {
        "DATA_DIR": str(config.data_dir),
        "APP_HOST": config.host,
        "APP_PORT": str(config.port),
        "OLLAMA_MODEL": ollama.model,
        "OLLAMA_URL": ollama.base_url,
        "ACE_STEP_DIR": str(ace_step_venv(config.data_dir)),
        "MUSIC_DIR": str(default_music_folder(config.data_dir)),
    }

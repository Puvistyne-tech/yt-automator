from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from automator.domain.diagnostics import DoctorPolicy
from automator.domain.run_parts import DEFAULT_MAX_RUN_LOGS
from automator.infrastructure.runtime.python_requirement import required_python

ENV_PREFIX = "AUTOMATOR_"
LOOPBACK_HOST = "127.0.0.1"
WILDCARD_HOSTS = frozenset({"", "0.0.0.0", "::"})
DEFAULT_MIN_FREE_GB: float = DoctorPolicy.model_fields["min_free_gb"].default
OAUTH_CALLBACK_PATH = "/api/oauth/callback"
REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


class SecretBackend(StrEnum):
    AUTO = "auto"
    KEYRING = "keyring"
    FILE = "file"


def default_data_dir() -> Path:
    return Path.home() / ".yt-automator"


def default_redirect_base(host: str, port: int) -> str:
    reachable = LOOPBACK_HOST if host in WILDCARD_HOSTS else host
    return f"http://{reachable}:{port}"


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    data_dir: Path = Field(default_factory=default_data_dir, description="Where all state lives")
    host: str = Field(default="127.0.0.1", description="Interface the web server binds to")
    port: int = Field(default=8000, ge=1, le=65535, description="Port the web server binds to")
    reload: bool = Field(default=False, description="Restart the server when code changes")
    redirect_base_url: str = Field(
        default="",
        description="Public base URL used for the OAuth redirect; empty follows host and port",
    )
    ui_base_url: str = Field(default="", description="Base URL the OAuth callback redirects to")
    scheduler_tick_seconds: float = Field(
        default=30.0, gt=0, description="Seconds between scheduler checks"
    )
    worker_poll_seconds: float = Field(
        default=1.0, gt=0, description="Seconds the worker pool waits between queue checks"
    )
    shutdown_timeout_seconds: float = Field(
        default=10.0, ge=0, description="Seconds to wait for workers on shutdown"
    )
    secret_backend: SecretBackend = Field(
        default=SecretBackend.AUTO, description="auto, keyring or file"
    )
    keyring_service: str = Field(default="yt-automator", description="Keychain service name")
    web_dist_dir: Path = Field(
        default=REPOSITORY_ROOT / "web" / "dist", description="Built web UI to serve"
    )
    cors_origins: tuple[str, ...] = Field(
        default=("http://localhost:5173", "http://127.0.0.1:5173"),
        description="Origins allowed to call the API (the Vite dev server)",
    )
    event_queue_size: int = Field(
        default=256, ge=1, description="Buffered events per live subscriber"
    )
    sse_heartbeat_seconds: float = Field(
        default=15.0, gt=0, description="Seconds between keep-alive messages on the event stream"
    )
    max_run_list_limit: int = Field(
        default=100, ge=1, description="Largest limit accepted when listing runs"
    )
    upload_chunk_bytes: int = Field(
        default=8 * 1024 * 1024, ge=256 * 1024, description="Resumable upload chunk size"
    )
    database_busy_timeout_ms: int = Field(
        default=5000, ge=0, description="Milliseconds SQLite waits for a locked database"
    )
    youtube_caption_track_name: str = Field(
        default="", description="Name shown on YouTube for uploaded caption tracks"
    )
    youtube_playlist_page_size: int = Field(
        default=50, ge=1, le=50, description="Playlists fetched per YouTube API page"
    )
    max_run_log_entries: int = Field(
        default=DEFAULT_MAX_RUN_LOGS, ge=1, description="Newest log entries kept on each run"
    )
    log_level: str = Field(default="info", description="Server log level")
    doctor_min_free_gb: float = Field(
        default=DEFAULT_MIN_FREE_GB,
        ge=0,
        description="Free disk space below which the doctor warns, in GB",
    )
    doctor_tool_timeout_seconds: float = Field(
        default=5.0, gt=0, description="Seconds the doctor waits for ffmpeg -version"
    )

    @property
    def oauth_redirect_uri(self) -> str:
        return self.redirect_base.rstrip("/") + OAUTH_CALLBACK_PATH

    @property
    def redirect_base(self) -> str:
        return self.redirect_base_url or default_redirect_base(self.host, self.port)

    @property
    def database_path(self) -> Path:
        return self.data_dir / "automator.db"

    @property
    def doctor_policy(self) -> DoctorPolicy:
        policy = DoctorPolicy(min_free_gb=self.doctor_min_free_gb)
        minimum = required_python()
        return policy.model_copy(update={"min_python": minimum}) if minimum else policy


def env_value(name: str, raw: str) -> Any:
    if name == "cors_origins":
        return tuple(item.strip() for item in raw.split(",") if item.strip())
    return raw


def load_config(environ: Mapping[str, str]) -> RuntimeConfig:
    values = {
        name: env_value(name, environ[ENV_PREFIX + name.upper()])
        for name in RuntimeConfig.model_fields
        if ENV_PREFIX + name.upper() in environ
    }
    return RuntimeConfig.model_validate(values)

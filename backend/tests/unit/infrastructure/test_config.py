from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from automator.infrastructure.config import (
    REPOSITORY_ROOT,
    RuntimeConfig,
    SecretBackend,
    default_data_dir,
    load_config,
)

OVERRIDES: list[tuple[str, str, Any]] = [
    ("data_dir", "/tmp/automator-data", Path("/tmp/automator-data")),
    ("host", "0.0.0.0", "0.0.0.0"),
    ("port", "9000", 9000),
    ("reload", "true", True),
    ("redirect_base_url", "http://host:1/", "http://host:1/"),
    ("ui_base_url", "http://ui:3000", "http://ui:3000"),
    ("scheduler_tick_seconds", "0.5", 0.5),
    ("worker_poll_seconds", "0.25", 0.25),
    ("shutdown_timeout_seconds", "2.5", 2.5),
    ("secret_backend", "file", SecretBackend.FILE),
    ("keyring_service", "other", "other"),
    ("web_dist_dir", "/srv/web", Path("/srv/web")),
    ("cors_origins", "http://a, http://b", ("http://a", "http://b")),
    ("event_queue_size", "8", 8),
    ("sse_heartbeat_seconds", "0.5", 0.5),
    ("max_run_list_limit", "20", 20),
    ("upload_chunk_bytes", "262144", 262144),
    ("database_busy_timeout_ms", "250", 250),
    ("youtube_caption_track_name", "English", "English"),
    ("youtube_playlist_page_size", "10", 10),
    ("max_run_log_entries", "50", 50),
    ("log_level", "debug", "debug"),
    ("doctor_min_free_gb", "2.5", 2.5),
    ("doctor_tool_timeout_seconds", "1.5", 1.5),
]
DEFAULTS: dict[str, Any] = {
    "data_dir": default_data_dir(),
    "host": "127.0.0.1",
    "port": 8000,
    "reload": False,
    "redirect_base_url": "http://127.0.0.1:8000",
    "ui_base_url": "",
    "scheduler_tick_seconds": 30.0,
    "worker_poll_seconds": 1.0,
    "shutdown_timeout_seconds": 10.0,
    "secret_backend": SecretBackend.AUTO,
    "keyring_service": "yt-automator",
    "web_dist_dir": REPOSITORY_ROOT / "web" / "dist",
    "cors_origins": ("http://localhost:5173", "http://127.0.0.1:5173"),
    "event_queue_size": 256,
    "sse_heartbeat_seconds": 15.0,
    "max_run_list_limit": 100,
    "upload_chunk_bytes": 8 * 1024 * 1024,
    "database_busy_timeout_ms": 5000,
    "youtube_caption_track_name": "",
    "youtube_playlist_page_size": 50,
    "max_run_log_entries": 2000,
    "log_level": "info",
    "doctor_min_free_gb": 10.0,
    "doctor_tool_timeout_seconds": 5.0,
}


def env(field: str) -> str:
    return "AUTOMATOR_" + field.upper()


def test_every_field_has_a_tested_override_and_default() -> None:
    assert {name for name, _, _ in OVERRIDES} == set(RuntimeConfig.model_fields)
    assert set(DEFAULTS) == set(RuntimeConfig.model_fields)


@pytest.mark.parametrize(("field", "raw", "expected"), OVERRIDES)
def test_each_field_reads_its_prefixed_environment_variable(
    field: str, raw: str, expected: Any
) -> None:
    config = load_config({env(field): raw, "UNRELATED": "x"})
    assert getattr(config, field) == expected


def test_defaults_and_derived_paths(tmp_path: Path) -> None:
    config = RuntimeConfig()
    assert {name: getattr(config, name) for name in DEFAULTS} == DEFAULTS
    assert config.oauth_redirect_uri == "http://127.0.0.1:8000/api/oauth/callback"
    moved = load_config({env("data_dir"): str(tmp_path), env("redirect_base_url"): "http://h:1/"})
    assert moved.database_path == tmp_path / "automator.db"
    assert moved.oauth_redirect_uri == "http://h:1/api/oauth/callback"


def test_doctor_policy_follows_the_config() -> None:
    policy = load_config({env("doctor_min_free_gb"): "3"}).doctor_policy
    assert policy.min_free_gb == 3.0


def test_empty_cors_origins_allow_none() -> None:
    assert load_config({env("cors_origins"): ""}).cors_origins == ()


@pytest.mark.parametrize(
    ("field", "raw"),
    [
        ("port", "0"),
        ("port", "abc"),
        ("port", "70000"),
        ("secret_backend", "vault"),
        ("scheduler_tick_seconds", "0"),
        ("worker_poll_seconds", "-1"),
        ("upload_chunk_bytes", "1"),
        ("event_queue_size", "0"),
        ("max_run_list_limit", "0"),
        ("reload", "maybe"),
        ("database_busy_timeout_ms", "-1"),
        ("youtube_playlist_page_size", "51"),
        ("max_run_log_entries", "0"),
        ("doctor_min_free_gb", "-1"),
        ("doctor_tool_timeout_seconds", "0"),
    ],
)
def test_invalid_values_are_rejected(field: str, raw: str) -> None:
    with pytest.raises(ValueError, match=field):
        load_config({env(field): raw})

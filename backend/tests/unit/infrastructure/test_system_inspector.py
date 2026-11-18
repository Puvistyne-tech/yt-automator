from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path

import pytest

from automator.infrastructure.config import RuntimeConfig
from automator.infrastructure.diagnostics.system_inspector import (
    build_system_inspector,
    tool_version,
    writable_dir,
)
from automator.infrastructure.providers.process import SubprocessRunner
from automator.infrastructure.storage.disk_usage import free_space
from tests.fixtures.fake_diagnostics import MIGRATION_HEAD


def script(folder: Path, body: str) -> Path:
    path = folder / "tool"
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def config_for(tmp_path: Path, tool_timeout_seconds: float = 5.0) -> RuntimeConfig:
    return RuntimeConfig(
        data_dir=tmp_path / "data",
        web_dist_dir=tmp_path / "dist",
        doctor_tool_timeout_seconds=tool_timeout_seconds,
    )


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("echo 'ffmpeg version 7.1 Copyright (c) 2000'", "ffmpeg version 7.1"),
        ("echo 'ffprobe 7.1 custom build'", "ffprobe 7.1 custom build"),
        ("exit 3", ""),
        ("sleep 5", ""),
        ("true", ""),
    ],
)
def test_tool_version_reads_the_first_line(tmp_path: Path, body: str, expected: str) -> None:
    assert tool_version(SubprocessRunner(), str(script(tmp_path, body)), 0.5) == expected


def test_tool_version_of_a_missing_binary_is_empty(tmp_path: Path) -> None:
    assert tool_version(SubprocessRunner(), str(tmp_path / "absent"), 0.5) == ""


def test_writable_dir_walks_up_to_an_existing_folder(tmp_path: Path) -> None:
    assert writable_dir(tmp_path / "a" / "b")
    blocker = tmp_path / "file"
    blocker.write_text("x", encoding="utf-8")
    assert not writable_dir(blocker / "data")


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write to read-only folders")
def test_read_only_folder_is_not_writable(tmp_path: Path) -> None:
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o500)
    try:
        assert not writable_dir(locked / "data")
    finally:
        locked.chmod(0o700)


def test_free_space_is_unknown_when_the_disk_cannot_be_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unreadable(_: Path) -> None:
        raise OSError("no disk")

    monkeypatch.setattr(shutil, "disk_usage", unreadable)
    assert free_space(tmp_path) is None


def test_facts_of_a_fresh_install(tmp_path: Path) -> None:
    facts = build_system_inspector(config_for(tmp_path)).facts()
    assert facts.data_dir == str(tmp_path / "data")
    assert facts.data_dir_writable
    assert facts.free_bytes is not None and facts.free_bytes > 0
    assert facts.database_revision is None
    assert facts.database_head == MIGRATION_HEAD
    assert not facts.ui_built
    assert not (tmp_path / "data").exists()


def test_facts_see_the_ui_build(tmp_path: Path) -> None:
    (tmp_path / "dist").mkdir()
    (tmp_path / "dist" / "index.html").write_text("<html></html>", encoding="utf-8")
    assert build_system_inspector(config_for(tmp_path)).facts().ui_built


def test_tool_timeout_comes_from_the_config(tmp_path: Path) -> None:
    config = config_for(tmp_path, tool_timeout_seconds=1.5)
    assert build_system_inspector(config).settings.tool_timeout_seconds == 1.5

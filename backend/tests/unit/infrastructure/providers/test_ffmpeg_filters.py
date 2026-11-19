from __future__ import annotations

from pathlib import Path

from autotube.infrastructure.providers.ffmpeg_filters import ffmpeg_filter_names, listed_filters
from autotube.infrastructure.providers.host import HostProbe
from autotube.infrastructure.providers.process import ProcessResult
from tests.fixtures.setup_script import stub
from tests.unit.infrastructure.providers.fakes import RecordingRunner

LISTING = """Filters:
  T.. = Timeline support
  ... = Multiple inputs
 ... ashowinfo         A->A       Show textual information for each audio frame.
 ... ass               V->V       Render ASS subtitles onto input video using the libass library.
 TSC zoompan           V->V       Apply Zoom & Pan effect.
"""


def test_listed_filters_reads_the_name_column() -> None:
    names = listed_filters(LISTING)
    assert {"ashowinfo", "ass", "zoompan"} <= names
    assert "subtitles" not in names and "Timeline" not in names


def test_filter_names_come_from_one_hidden_banner_listing() -> None:
    runner = RecordingRunner(results=[ProcessResult(stdout=LISTING, stderr="")])
    assert "ass" in ffmpeg_filter_names("/x/ffmpeg", 3.0, runner)
    assert runner.commands == [["/x/ffmpeg", "-hide_banner", "-filters"]]
    assert runner.calls[0].timeout_seconds == 3.0


def test_a_failing_ffmpeg_lists_no_filters() -> None:
    assert ffmpeg_filter_names("ffmpeg", 1.0, RecordingRunner(fail_with="boom")) == frozenset()


def test_the_default_probe_runs_the_real_binary(tmp_path: Path) -> None:
    binary = str(stub(tmp_path, "ffmpeg", "echo ' ... ass  V->V  libass'"))
    assert HostProbe().missing_ffmpeg_filter(binary, "ass", 5.0) is None
    assert HostProbe().missing_ffmpeg_filter(binary, "zoompan", 5.0) == (
        f"{binary} has no 'zoompan' filter"
    )

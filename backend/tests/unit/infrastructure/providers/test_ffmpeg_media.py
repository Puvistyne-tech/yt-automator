from __future__ import annotations

from pathlib import Path

import pytest

from automator.domain.capabilities import TimedClip, VideoComposition
from automator.infrastructure.providers.media.ffmpeg_media import FfmpegMedia
from automator.infrastructure.providers.media.ffmpeg_options import FfmpegOptions
from automator.infrastructure.providers.process import ProcessResult
from automator.shared.errors import UpstreamFailure
from tests.unit.infrastructure.providers.fakes import RecordingRunner, host, make_context

MEASURED = """[Parsed_loudnorm_0 @ 0x1]
{
\t"input_i" : "-24.10",
\t"input_tp" : "-6.00",
\t"input_lra" : "3.20",
\t"input_thresh" : "-34.50",
\t"output_i" : "-16.0",
\t"target_offset" : "0.40"
}
"""
SILENT = MEASURED.replace('"-24.10"', '"-inf"').replace('"-6.00"', '"-inf"')


def video(narration: bool = True) -> VideoComposition:
    still = TimedClip(path=Path("/w/a.png"), start_seconds=0, duration_seconds=2)
    voice = TimedClip(path=Path("/w/n.wav"), start_seconds=0, duration_seconds=1)
    return VideoComposition(
        width=320, height=180, visuals=(still,), narration=(voice,) if narration else ()
    )


def media(tmp_path: Path, runner: RecordingRunner, **options: object) -> FfmpegMedia:
    return FfmpegMedia(FfmpegOptions.model_validate(options), make_context(tmp_path, runner=runner))


def graph_of(command: list[str]) -> str:
    return command[command.index("-filter_complex") + 1]


def test_two_pass_measures_then_normalises_linearly(tmp_path: Path) -> None:
    runner = RecordingRunner(results=[ProcessResult("", MEASURED)])
    media(tmp_path, runner).compose_video(video(), tmp_path / "out.mp4")
    measure, render = runner.commands
    assert measure[-4:] == ["-vn", "-f", "null", "-"]
    assert "print_format=json" in graph_of(measure)
    assert "measured_I=-24.1" in graph_of(render)
    assert "linear=true" in graph_of(render)


def test_silent_measurement_skips_normalisation(tmp_path: Path) -> None:
    runner = RecordingRunner(results=[ProcessResult("", SILENT)])
    media(tmp_path, runner).compose_video(video(), tmp_path / "out.mp4")
    assert "loudnorm" not in graph_of(runner.commands[1])


def test_single_pass_and_videos_without_audio_render_once(tmp_path: Path) -> None:
    runner = RecordingRunner()
    adapter = media(tmp_path, runner, two_pass_loudness=False)
    adapter.compose_video(video(), tmp_path / "a.mp4")
    adapter.compose_video(video(narration=False), tmp_path / "b.mp4")
    first, second = runner.commands
    assert "loudnorm=I=-16:TP=-1.5:LRA=11[" not in graph_of(first)
    assert "loudnorm=I=-16:TP=-1.5:LRA=11," in graph_of(first)
    assert "anullsrc" in graph_of(second)


def test_composition_needs_a_visual(tmp_path: Path) -> None:
    empty = video().model_copy(update={"visuals": ()})
    with pytest.raises(UpstreamFailure, match="visual"):
        media(tmp_path, RecordingRunner()).compose_video(empty, tmp_path / "x.mp4")


def test_probe_frame_and_loudness(tmp_path: Path) -> None:
    runner = RecordingRunner(
        results=[
            ProcessResult("12.48\n", ""),
            ProcessResult("", ""),
            ProcessResult(
                "", "t: 1 I: -30.0 LUFS\n  Integrated loudness:\n    I:         -16.2 LUFS\n"
            ),
        ]
    )
    adapter = media(tmp_path, runner)
    assert adapter.duration_seconds(Path("/w/v.mp4")) == 12.48
    adapter.extract_frame(Path("/w/v.mp4"), 1.5, tmp_path / "f.png")
    assert adapter.loudness_lufs(Path("/w/v.mp4")) == -16.2
    assert runner.commands[0][0] == "ffprobe"
    assert runner.commands[1][5:8] == ["-ss", "1.500", "-i"]
    assert "ebur128=peak=true" in runner.commands[2]


def test_unparseable_probe_output_is_an_upstream_failure(tmp_path: Path) -> None:
    runner = RecordingRunner(results=[ProcessResult("N/A", ""), ProcessResult("", "nothing")])
    adapter = media(tmp_path, runner)
    with pytest.raises(UpstreamFailure):
        adapter.duration_seconds(Path("/w/v.mp4"))
    with pytest.raises(UpstreamFailure):
        adapter.loudness_lufs(Path("/w/v.mp4"))


def test_availability_needs_ffmpeg_and_ffprobe(tmp_path: Path) -> None:
    only_ffmpeg = make_context(tmp_path, probe=host(binaries=frozenset({"ffmpeg"})))
    assert "ffprobe" in (FfmpegMedia(FfmpegOptions(), only_ffmpeg).available() or "")
    both = make_context(tmp_path, probe=host(binaries=frozenset({"ffmpeg", "ffprobe"})))
    assert FfmpegMedia(FfmpegOptions(), both).available() is None

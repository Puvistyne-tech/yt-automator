from __future__ import annotations

from pathlib import Path

import pytest

from automator.domain.capabilities import SubtitleStyle
from automator.infrastructure.providers.media.ass_document import ass_color
from automator.infrastructure.providers.media.composition_audio import (
    LoudnessMeasurement,
    audio_graph,
)
from automator.infrastructure.providers.media.composition_inputs import (
    plan_inputs,
    timeline_seconds,
)
from automator.infrastructure.providers.media.composition_video import video_graph
from automator.infrastructure.providers.media.media_commands import compose_command
from automator.infrastructure.providers.media.subtitle_filter import filter_path, subtitle_filter
from automator.shared.errors import UpstreamFailure
from tests.unit.infrastructure.providers.media_fixtures import OPTIONS, composition


def test_inputs_loop_stills_and_music() -> None:
    plan = plan_inputs(composition())
    assert plan.args == [
        "-loop",
        "1",
        "-framerate",
        "24",
        "-t",
        "2.000",
        "-i",
        "/w/a.png",
        "-i",
        "/w/b.mp4",
        "-i",
        "/w/n1.wav",
        "-i",
        "/w/n2.wav",
        "-i",
        "/w/pop.wav",
        "-stream_loop",
        "-1",
        "-i",
        "/w/music.wav",
    ]
    assert (plan.visuals, plan.narration, plan.effects, plan.music) == ([0, 1], [2, 3], [4], 5)
    assert timeline_seconds(composition()) == 3.5


def test_video_graph_places_clips_on_a_timeline_with_subtitles_and_fades() -> None:
    graph = video_graph(composition(), plan_inputs(composition()), 3.5, OPTIONS)
    assert graph[0] == "color=c=#000000:s=320x180:r=24:d=3.500,format=yuv420p[base]"
    assert graph[3] == (
        "[1:v]scale=320:180:force_original_aspect_ratio=increase:flags=lanczos,crop=320:180,"
        "setsar=1,fps=24,format=yuv420p,tpad=stop_mode=clone:stop_duration=1.500,"
        "trim=duration=1.500,setpts=PTS-STARTPTS+2.000/TB[v1]"
    )
    assert graph[4] == "[o0][v1]overlay=eof_action=pass:repeatlast=0[o1]"
    assert graph[5].startswith("[o1]ass=filename=/w/subs.srt:shaping=complex,fade=")
    assert graph[5].endswith(
        "fade=t=in:st=0:d=0.500,fade=t=out:st=3.000:d=0.500,format=yuv420p[vout]"
    )


def test_subtitles_are_skipped_unless_burned_in() -> None:
    soft = composition(subtitle_style=SubtitleStyle(burn_in=False), fade_seconds=0)
    graph = video_graph(soft, plan_inputs(soft), 3.5, OPTIONS)
    assert graph[-1] == "[o1]format=yuv420p[vout]"


def test_audio_graph_mixes_narration_ducks_music_and_normalises() -> None:
    graph = audio_graph(composition(), plan_inputs(composition()), 3.5, OPTIONS, "loudnorm=I=-16")
    assert graph[1] == (
        "[3:a]atrim=duration=1.000,asetpts=PTS-STARTPTS,aresample=48000,"
        "aformat=sample_fmts=fltp:channel_layouts=stereo,volume=0.800,adelay=delays=2000:all=1[n1]"
    )
    assert "[n0][n1]amix=inputs=2:duration=longest:normalize=0[voice]" in graph
    assert "[voice]apad=whole_dur=3.500,asplit=2[voice_mix][voice_key]" in graph
    assert (
        "[music][voice_key]sidechaincompress=threshold=0.03:ratio=6.50:attack=40:release=500[bed]"
        in graph
    )
    assert graph[-2] == "[voice_mix][bed][e0]amix=inputs=3:duration=longest:normalize=0[mix]"
    assert graph[-1] == (
        "[mix]apad=whole_dur=3.500,atrim=duration=3.500,afade=t=in:st=0:d=0.500,"
        "afade=t=out:st=3.000:d=0.500,loudnorm=I=-16,aresample=48000,"
        "aformat=sample_fmts=fltp:channel_layouts=stereo[aout]"
    )


def test_music_without_ducking_and_silent_videos() -> None:
    plain = composition(music_ducking=0.0, sound_effects=())
    graph = audio_graph(plain, plan_inputs(plain), 3.5, OPTIONS, None)
    assert graph[-2] == "[voice][music]amix=inputs=2:duration=longest:normalize=0[mix]"
    silent = composition(narration=(), music=None, sound_effects=())
    assert audio_graph(silent, plan_inputs(silent), 2.0, OPTIONS, None) == [
        "anullsrc=r=48000:cl=stereo,atrim=duration=2.000[aout]"
    ]


def test_compose_command_applies_measured_loudness_and_encoding() -> None:
    measured = LoudnessMeasurement(-23.5, -4.1, 6.0, -34.0, 0.3)
    command = compose_command(composition(), OPTIONS, Path("/w/out.mp4"), measured, True)
    graph = command[command.index("-filter_complex") + 1]
    assert (
        "loudnorm=I=-16:TP=-1.5:LRA=11:measured_I=-23.5:measured_TP=-4.1"
        ":measured_LRA=6:measured_thresh=-34:offset=0.3:linear=true" in graph
    )
    assert command[-11:] == [
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        "-movflags",
        "+faststart",
        "-t",
        "3.500",
        "/w/out.mp4",
    ]
    assert command[command.index("-pix_fmt") : command.index("-pix_fmt") + 2] == [
        "-pix_fmt",
        "yuv420p",
    ]


def test_filter_paths_and_colours_are_escaped() -> None:
    assert filter_path(Path("/a b/it's:[x],y;z")) == "/a b/it\\\\\\'s\\\\:\\[x\\]\\,y\\;z"
    assert ass_color("#FFD54A") == "&H004AD5FF"
    with pytest.raises(UpstreamFailure):
        ass_color("gold")


def test_subtitles_use_complex_shaping_and_the_configured_fonts_dir() -> None:
    rendered = subtitle_filter(Path("/w/s.ass"), SubtitleStyle(), "/fonts")
    assert rendered == "ass=filename=/w/s.ass:shaping=complex:fontsdir=/fonts"


def test_a_font_file_brings_its_own_folder() -> None:
    style = SubtitleStyle(font_file=Path("/opt/type/Tamil.ttf"))
    rendered = subtitle_filter(Path("/w/s.ass"), style, "/fonts")
    assert rendered.endswith(":shaping=complex:fontsdir=/opt/type")


def test_no_fonts_dir_leaves_the_system_fonts() -> None:
    assert subtitle_filter(Path("/w/s.ass"), SubtitleStyle(), "") == (
        "ass=filename=/w/s.ass:shaping=complex"
    )

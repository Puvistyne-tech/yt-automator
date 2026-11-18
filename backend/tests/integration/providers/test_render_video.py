from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from automator.domain.capabilities import (
    CameraMove,
    Capability,
    ImageRequest,
    MotionRequest,
    MusicRequest,
    Speech,
    SpeechRequest,
    SubtitleStyle,
    TimedClip,
    TimingSource,
    VideoComposition,
)
from automator.domain.pipeline import ProviderResolver
from automator.domain.providers import ProviderChoice, ProviderConfig
from automator.infrastructure.providers.catalog import build_provider_catalog
from tests.fixtures.fake_runtime import InMemorySecrets

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
        reason="ffmpeg and ffprobe are needed to render video",
    ),
]
WIDTH, HEIGHT, FPS = 320, 180, 24


def offline_resolver(tmp_path: Path, voice: str) -> ProviderResolver:
    chains = {
        Capability.IMAGE: "offline_image",
        Capability.MOTION: "ffmpeg_pan_zoom",
        Capability.TTS: voice,
        Capability.MUSIC: "synth_music",
    }
    configs = [
        ProviderConfig(capability=capability, chain=(ProviderChoice(provider_id=provider_id),))
        for capability, provider_id in chains.items()
    ]
    return build_provider_catalog(InMemorySecrets(), tmp_path).resolver(configs)


def probe(path: Path) -> dict[str, Any]:
    command = ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]
    loaded: dict[str, Any] = json.loads(
        subprocess.run(command, capture_output=True, check=True).stdout
    )
    return loaded


def subtitles_for(speech: Speech, path: Path) -> Path:
    stamp = "00:00:00,300 --> 00:00:02,700"
    text = " ".join(word.word for word in speech.words)
    path.write_text(f"1\n{stamp}\n{text}\n", encoding="utf-8")
    return path


def moving_clip(tmp_path: Path, resolver: ProviderResolver, still: Path) -> Path:
    return resolver.resolve(Capability.MOTION).animate(
        MotionRequest(
            image=still,
            duration_seconds=1.5,
            width=WIDTH,
            height=HEIGHT,
            fps=FPS,
            camera=CameraMove.PAN_RIGHT,
        ),
        tmp_path / "clip.mp4",
    )


def render(tmp_path: Path, resolver: ProviderResolver, text: str, language: str) -> Path:
    still = resolver.resolve(Capability.IMAGE).generate(
        ImageRequest(prompt="a fox under the moon", width=WIDTH, height=HEIGHT, seed=3),
        tmp_path / "scene.png",
    )
    clip = moving_clip(tmp_path, resolver, still)
    speech = resolver.resolve(Capability.TTS).synthesize(
        SpeechRequest(text=text, language=language), tmp_path / "voice.wav"
    )
    music = resolver.resolve(Capability.MUSIC).compose(
        MusicRequest(prompt="gentle night", duration_seconds=3), tmp_path / "music.wav"
    )
    composition = VideoComposition(
        width=WIDTH,
        height=HEIGHT,
        fps=FPS,
        visuals=(
            TimedClip(path=clip, start_seconds=0, duration_seconds=1.5),
            TimedClip(path=still, start_seconds=1.5, duration_seconds=1.5),
        ),
        narration=(
            TimedClip(
                path=speech.path,
                start_seconds=0.3,
                duration_seconds=min(speech.duration_seconds, 2.5),
            ),
        ),
        music=music,
        subtitles=subtitles_for(speech, tmp_path / "voice.srt"),
        subtitle_style=SubtitleStyle(burn_in=True, font_size=18, margin_bottom=12),
        loudness_lufs=-16.0,
    )
    return resolver.resolve(Capability.MEDIA).compose_video(composition, tmp_path / "final.mp4")


def assert_video(path: Path, tmp_path: Path, resolver: ProviderResolver) -> None:
    info = probe(path)
    streams = {stream["codec_type"]: stream for stream in info["streams"]}
    video = streams["video"]
    assert (video["codec_name"], video["width"], video["height"]) == ("h264", WIDTH, HEIGHT)
    assert video["pix_fmt"] == "yuv420p"
    assert video["r_frame_rate"] == f"{FPS}/1"
    assert streams["audio"]["codec_name"] == "aac"
    assert float(info["format"]["duration"]) == pytest.approx(3.0, abs=0.1)
    media = resolver.resolve(Capability.MEDIA)
    assert media.loudness_lufs(path) == pytest.approx(-16.0, abs=2.0)
    assert media.duration_seconds(path) == pytest.approx(3.0, abs=0.1)
    assert media.extract_frame(path, 1.0, tmp_path / "frame.png").stat().st_size > 1000


def test_offline_speech_video_renders_end_to_end(tmp_path: Path) -> None:
    resolver = offline_resolver(tmp_path, "offline_speech")
    path = render(tmp_path, resolver, "Once upon a time a small fox", "en")
    assert_video(path, tmp_path, resolver)


@pytest.mark.skipif(not shutil.which("espeak-ng"), reason="espeak-ng is not installed")
def test_espeak_tamil_video_renders_end_to_end(tmp_path: Path) -> None:
    resolver = offline_resolver(tmp_path, "espeak")
    speech = resolver.resolve(Capability.TTS).synthesize(
        SpeechRequest(text="ஒரு சிறிய நரி", language="ta"), tmp_path / "check.wav"
    )
    assert speech.timing_source in {TimingSource.ESTIMATE, TimingSource.ALIGNMENT}
    assert len(speech.words) == 3
    path = render(tmp_path, resolver, "ஒரு சிறிய நரி காட்டில் வாழ்ந்தது", "ta")
    assert_video(path, tmp_path, resolver)

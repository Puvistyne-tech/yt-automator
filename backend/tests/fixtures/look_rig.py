from __future__ import annotations

from pathlib import Path
from typing import Any

from autotube.domain.capabilities import VideoComposition, WordTiming
from autotube.infrastructure.providers.media.ass_subtitles import with_ass_subtitles
from autotube.infrastructure.providers.media.ffmpeg_options import FfmpegOptions
from autotube.infrastructure.providers.media.media_commands import compose_command
from autotube.pipelines.kids_story.settings.root import KidsStorySettings
from autotube.pipelines.kids_story.story.model import Story
from autotube.pipelines.kids_story.subtitles.cues import Cue
from autotube.pipelines.kids_story.subtitles.karaoke import karaoke_words
from autotube.pipelines.kids_story.subtitles.layout import subtitle_layout
from autotube.pipelines.kids_story.subtitles.srt import render_srt
from autotube.pipelines.kids_story.subtitles.timeline_cues import cue_rules, timeline_cues
from autotube.pipelines.kids_story.timeline.composition import Sources, composition
from autotube.pipelines.kids_story.timeline.plan import Segment
from autotube.pipelines.kids_story.timeline.variants import planned
from autotube.pipelines.kids_story.timeline.voices import VoiceLine
from tests.fixtures.kids_data import NO_FONTS, story

WORKSPACE = Path("/w")
WORD_STEP = 0.4
STORED_SETTINGS: dict[str, Any] = {
    "episode": {"resolution": "1280x720"},
    "short": {"resolution": "720x1280"},
    "subtitles": {"font_files": NO_FONTS, "burn_in_episode": True},
    "thumbnail": {"font_files": NO_FONTS},
}


def timed_words(text: str) -> tuple[WordTiming, ...]:
    return tuple(
        WordTiming(word=word, start_seconds=index * WORD_STEP, end_seconds=(index + 1) * WORD_STEP)
        for index, word in enumerate(text.split())
    )


def spoken_line(key: str, text: str) -> VoiceLine:
    words = timed_words(text)
    seconds = len(words) * WORD_STEP + 0.2
    return VoiceLine(
        segment=key, filename=f"voice/{key}.wav", seconds=seconds, text=text, words=words
    )


def spoken_lines(draft: Story) -> dict[str, VoiceLine]:
    lines = {
        f"scene-{index}": spoken_line(f"scene-{index}", scene.narration)
        for index, scene in enumerate(draft.scenes)
    }
    lines["intro"] = spoken_line("intro", "Hello friends, story time.")
    lines["hook"] = spoken_line("hook", draft.hook_line)
    return lines


def look_cues(settings: KidsStorySettings, variant: str) -> list[Cue]:
    draft = story()
    voices = spoken_lines(draft)
    segments = planned(draft, voices, settings, variant)
    layout = subtitle_layout(settings, draft.language, variant)
    return timeline_cues(segments, voices, cue_rules(settings.subtitles, layout))


def look_sources(segments: list[Segment], voices: dict[str, VoiceLine], cues: list[Cue]) -> Sources:
    return Sources(
        workspace=WORKSPACE,
        clips={item.visual_key: WORKSPACE / f"{item.visual_key}.mp4" for item in segments},
        voices=voices,
        effects={},
        music=WORKSPACE / "music.wav",
        subtitles=WORKSPACE / "subs.srt",
        subtitle_words=karaoke_words(cues),
    )


def look_segments(settings: KidsStorySettings, variant: str) -> list[Segment]:
    draft = story()
    return planned(draft, spoken_lines(draft), settings, variant)


def look_composition(settings: KidsStorySettings, variant: str = "episode") -> VideoComposition:
    draft = story()
    voices = spoken_lines(draft)
    segments = planned(draft, voices, settings, variant)
    sources = look_sources(segments, voices, look_cues(settings, variant))
    return composition(segments, draft, sources, settings, variant)


def look_srt(settings: KidsStorySettings, variant: str = "episode") -> str:
    return render_srt(look_cues(settings, variant))


def rendered_ass(settings: KidsStorySettings, folder: Path, variant: str = "episode") -> str:
    srt = folder / "subs.srt"
    srt.write_text(look_srt(settings, variant), encoding="utf-8")
    made = look_composition(settings, variant).model_copy(update={"subtitles": srt})
    size = settings.video_size(variant)
    burned = with_ass_subtitles(made, size, folder / "video.mp4", FfmpegOptions().outline_width)
    assert burned.subtitles is not None
    return burned.subtitles.read_text(encoding="utf-8")


def rendered_command(settings: KidsStorySettings, variant: str = "episode") -> list[str]:
    made = look_composition(settings, variant).model_copy(
        update={"subtitles": WORKSPACE / "subs.ass"}
    )
    return compose_command(made, FfmpegOptions(), WORKSPACE / "out.mp4", None, True)

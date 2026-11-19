from __future__ import annotations

from pathlib import Path

from autotube.domain.capabilities import Capability, MediaToolkit, VideoComposition, WordTiming
from autotube.domain.pipeline import NewArtifact, StageContext, StageLog, StageOutcome
from autotube.domain.pipeline_descriptors import StageDescriptor
from autotube.domain.run_enums import ArtifactKind, LogLevel
from autotube.pipelines.narrated_video.artifacts import (
    Role,
    artifact,
    folder,
    latest,
    path_of,
    text,
    with_role,
)
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.stages.logo_check import require_logo
from autotube.pipelines.narrated_video.stages.media_types import JSON, MP4, SRT
from autotube.pipelines.narrated_video.stages.run_settings import kids_settings
from autotube.pipelines.narrated_video.stages.story_loading import load_stories
from autotube.pipelines.narrated_video.subtitles.karaoke import karaoke_words
from autotube.pipelines.narrated_video.subtitles.layout import subtitle_layout
from autotube.pipelines.narrated_video.subtitles.srt import render_srt
from autotube.pipelines.narrated_video.subtitles.timeline_cues import cue_rules, timeline_cues
from autotube.pipelines.narrated_video.timeline.composition import (
    Sources,
    composition,
    timeline_meta,
)
from autotube.pipelines.narrated_video.timeline.cuts import Cut, planned_cuts
from autotube.pipelines.narrated_video.timeline.plan import total_seconds

Captions = tuple[Path | None, tuple[WordTiming, ...]]


def keyed_paths(context: StageContext, role: Role, key: str) -> dict[str, Path]:
    return {
        text(found.meta.get(key)): path_of(context, found)
        for found in with_role(context.artifacts, role)
    }


def measured(media: MediaToolkit, video: Path, planned_seconds: float, log: StageLog) -> float:
    try:
        return media.duration_seconds(video)
    except (OSError, ValueError) as error:
        log(
            f"could not measure {video.name}, using the planned length: {error}",
            LogLevel.WARNING,
        )
        return planned_seconds


def final_video_artifact(
    cut: Cut, video: Path, plan: VideoComposition, seconds: float, has_subtitles: bool
) -> NewArtifact:
    return artifact(
        ArtifactKind.VIDEO,
        video,
        MP4,
        Role.FINAL_VIDEO,
        language=cut.language,
        variant=cut.variant,
        duration_seconds=seconds,
        planned_seconds=total_seconds(cut.segments),
        timeline=timeline_meta(cut.segments),
        title=cut.story.title,
        burned_subtitles=plan.subtitle_style.burn_in and has_subtitles,
    )


def cut_artifact(cut: Cut, path: Path, media_type: str, role: Role) -> NewArtifact:
    return artifact(
        ArtifactKind.TEXT, path, media_type, role, language=cut.language, variant=cut.variant
    )


class AssembleStage:
    @property
    def descriptor(self) -> StageDescriptor:
        return StageDescriptor(
            id="assemble",
            title="Edit the videos",
            description="Puts clips, narration, music, effects and subtitles on one timeline.",
        )

    def run(self, context: StageContext) -> StageOutcome:
        settings = kids_settings(context)
        media = context.providers.resolve(Capability.MEDIA)
        made: list[NewArtifact] = []
        for cut in planned_cuts(load_stories(context), context.artifacts, settings):
            made.extend(self.edited(context, media, settings, cut))
        return StageOutcome(
            artifacts=tuple(made), provider=media.provider_id, message=f"{len(made)} files"
        )

    def subtitles(self, context: StageContext, settings: KidsStorySettings, cut: Cut) -> Captions:
        if not settings.subtitles.enabled:
            return None, ()
        layout = subtitle_layout(settings, cut.language, cut.variant)
        cues = timeline_cues(cut.segments, cut.voices, cue_rules(settings.subtitles, layout))
        path = folder(context, "subtitles") / f"{cut.name}.srt"
        path.write_text(render_srt(cues), encoding="utf-8")
        return path, karaoke_words(cues)

    def sources(self, context: StageContext, cut: Cut, captions: Captions) -> Sources:
        music = latest(context.artifacts, Role.MUSIC, cut.language, cut.variant)
        return Sources(
            workspace=context.workspace,
            clips=keyed_paths(context, Role.CLIP, "visual_key"),
            voices=cut.voices,
            effects=keyed_paths(context, Role.SOUND_EFFECT, "cue"),
            music=path_of(context, music) if music else None,
            subtitles=captions[0],
            subtitle_words=captions[1],
        )

    def edited(
        self, context: StageContext, media: MediaToolkit, settings: KidsStorySettings, cut: Cut
    ) -> list[NewArtifact]:
        captions = self.subtitles(context, settings, cut)
        srt = captions[0]
        plan = composition(
            cut.segments, cut.story, self.sources(context, cut, captions), settings, cut.variant
        )
        require_logo(plan)
        planned_seconds = total_seconds(cut.segments)
        context.log(f"editing the {cut.language} {cut.variant}: {planned_seconds:.1f} s")
        videos = folder(context, "videos")
        video = media.compose_video(plan, videos / f"{cut.name}.mp4")
        plan_path = videos / f"{cut.name}.composition.json"
        plan_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
        seconds = measured(media, video, planned_seconds, context.log)
        made = [
            final_video_artifact(cut, video, plan, seconds, srt is not None),
            cut_artifact(cut, plan_path, JSON, Role.COMPOSITION),
        ]
        if srt is not None:
            made.append(cut_artifact(cut, srt, SRT, Role.CAPTIONS))
        return made

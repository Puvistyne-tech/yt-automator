from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from automator.domain.capabilities import Capability, MediaToolkit
from automator.domain.pipeline import NewArtifact, StageContext, StageOutcome
from automator.domain.pipeline_descriptors import StageDescriptor
from automator.domain.run_enums import ArtifactKind
from automator.pipelines.kids_story.artifacts import (
    VARIANTS,
    Role,
    artifact,
    folder,
    latest,
    path_of,
    text,
    with_role,
)
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.stages.common import JSON, MP4, SRT, kids_settings, load_story
from automator.pipelines.kids_story.story.model import Story
from automator.pipelines.kids_story.subtitles.srt import render_srt
from automator.pipelines.kids_story.subtitles.timeline_cues import cue_rules, timeline_cues
from automator.pipelines.kids_story.timeline.composition import Sources, composition, timeline_meta
from automator.pipelines.kids_story.timeline.plan import Segment, total_seconds
from automator.pipelines.kids_story.timeline.variants import planned
from automator.pipelines.kids_story.timeline.voices import VoiceLine, voice_lines


@dataclass(frozen=True)
class Cut:
    story: Story
    variant: str
    voices: dict[str, VoiceLine]
    segments: list[Segment]

    @property
    def name(self) -> str:
        return f"{self.story.language}-{self.variant}"


def keyed_paths(context: StageContext, role: Role, key: str) -> dict[str, Path]:
    return {
        text(found.meta.get(key)): path_of(context, found)
        for found in with_role(context.artifacts, role)
    }


def measured(media: MediaToolkit, video: Path, planned_seconds: float) -> float:
    try:
        return media.duration_seconds(video)
    except Exception:
        return planned_seconds


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
        for cut in self.cuts(context, settings):
            made.extend(self.edited(context, media, settings, cut))
        return StageOutcome(
            artifacts=tuple(made), provider=media.provider_id, message=f"{len(made)} files"
        )

    def cuts(self, context: StageContext, settings: KidsStorySettings) -> list[Cut]:
        cuts = []
        for language in context.languages:
            story = load_story(context, language)
            voices = voice_lines(context.artifacts, language)
            for variant in VARIANTS:
                segments = planned(story, voices, settings, variant)
                if segments:
                    cuts.append(Cut(story, variant, voices, segments))
        return cuts

    def subtitles(
        self, context: StageContext, settings: KidsStorySettings, cut: Cut
    ) -> Path | None:
        if not settings.subtitles.enabled:
            return None
        cues = timeline_cues(cut.segments, cut.voices, cue_rules(settings.subtitles, cut.variant))
        path = folder(context, "subtitles") / f"{cut.name}.srt"
        path.write_text(render_srt(cues), encoding="utf-8")
        return path

    def sources(self, context: StageContext, cut: Cut, subtitles: Path | None) -> Sources:
        music = latest(context.artifacts, Role.MUSIC, cut.story.language, cut.variant)
        return Sources(
            workspace=context.workspace,
            clips=keyed_paths(context, Role.CLIP, "visual_key"),
            voices=cut.voices,
            effects=keyed_paths(context, Role.SOUND_EFFECT, "cue"),
            music=path_of(context, music) if music else None,
            subtitles=subtitles,
        )

    def edited(
        self, context: StageContext, media: MediaToolkit, settings: KidsStorySettings, cut: Cut
    ) -> list[NewArtifact]:
        language, variant = cut.story.language, cut.variant
        srt = self.subtitles(context, settings, cut)
        plan = composition(
            cut.segments, cut.story, self.sources(context, cut, srt), settings, variant
        )
        seconds = total_seconds(cut.segments)
        context.log(f"editing the {language} {variant}: {seconds:.1f} s")
        videos = folder(context, "videos")
        video = media.compose_video(plan, videos / f"{cut.name}.mp4")
        plan_path = videos / f"{cut.name}.composition.json"
        plan_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
        made = [
            artifact(
                ArtifactKind.VIDEO,
                video,
                MP4,
                Role.FINAL_VIDEO,
                language=language,
                variant=variant,
                duration_seconds=measured(media, video, seconds),
                planned_seconds=seconds,
                timeline=timeline_meta(cut.segments),
                title=cut.story.title,
                burned_subtitles=plan.subtitle_style.burn_in and srt is not None,
            ),
            artifact(
                ArtifactKind.TEXT,
                plan_path,
                JSON,
                Role.COMPOSITION,
                language=language,
                variant=variant,
            ),
        ]
        if srt is not None:
            made.append(
                artifact(
                    ArtifactKind.TEXT, srt, SRT, Role.CAPTIONS, language=language, variant=variant
                )
            )
        return made

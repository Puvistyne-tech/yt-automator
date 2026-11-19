from __future__ import annotations

from autotube.domain.capabilities import Capability, MotionGenerator, MotionRequest
from autotube.domain.pipeline import NewArtifact, StageContext, StageOutcome
from autotube.domain.pipeline_descriptors import StageDescriptor
from autotube.domain.run_enums import ArtifactKind
from autotube.pipelines.narrated_video.art.prompts import motion_prompt
from autotube.pipelines.narrated_video.artifacts import (
    Role,
    artifact,
    folder,
    path_of,
    required,
)
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.stages.media_types import MP4
from autotube.pipelines.narrated_video.stages.run_settings import kids_settings
from autotube.pipelines.narrated_video.stages.story_loading import load_stories
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.styles.resolve import resolve_style
from autotube.pipelines.narrated_video.timeline.cuts import planned_cuts
from autotube.pipelines.narrated_video.timeline.needs import ClipNeed, clip_needs


def motion_request(
    context: StageContext, settings: KidsStorySettings, story: Story, need: ClipNeed
) -> MotionRequest:
    image = required(context.artifacts, Role.VISUAL, visual_key=need.visual_key)
    scene = story.scenes[need.scene] if need.scene is not None else None
    style = resolve_style(settings)
    motion = style.motion
    width, height = settings.video_size(need.variant)
    fps = settings.video_fps(need.variant)
    return MotionRequest(
        image=path_of(context, image),
        prompt=motion_prompt(settings, scene, motion.feel),
        duration_seconds=need.seconds,
        width=width,
        height=height,
        fps=fps,
        camera=scene.camera if scene else motion.card_camera,
        intensity=motion.hero_intensity if scene and scene.hero else motion.intensity,
        held_frame_rate=held_rate(motion.held_frame_rate, fps),
        negative_prompt=style.motion_negative_prompt,
    )


def held_rate(style_rate: int | None, fps: int) -> int | None:
    return style_rate if style_rate is not None and style_rate < fps else None


def clip_name(visual_key: str) -> str:
    return visual_key.replace("@", "-") + ".mp4"


class MotionStage:
    @property
    def descriptor(self) -> StageDescriptor:
        return StageDescriptor(
            id="motion",
            title="Animate the pictures",
            description="Turns every picture into a gently moving clip as long as its narration.",
        )

    def run(self, context: StageContext) -> StageOutcome:
        settings = kids_settings(context)
        stories = load_stories(context)
        needs = clip_needs(planned_cuts(stories, context.artifacts, settings))
        motion = context.providers.resolve(Capability.MOTION)
        story = next(iter(stories.values()))
        made = [self.animated(context, motion, settings, story, need) for need in needs.values()]
        return StageOutcome(
            artifacts=tuple(made), provider=motion.provider_id, message=f"{len(made)} clips"
        )

    def animated(
        self,
        context: StageContext,
        motion: MotionGenerator,
        settings: KidsStorySettings,
        story: Story,
        need: ClipNeed,
    ) -> NewArtifact:
        context.log(f"animating {need.visual_key} for {need.seconds:.1f} s")
        request = motion_request(context, settings, story, need)
        path = motion.animate(request, folder(context, "motion") / clip_name(need.visual_key))
        return artifact(
            ArtifactKind.VIDEO,
            path,
            MP4,
            Role.CLIP,
            variant=need.variant,
            visual_key=need.visual_key,
            scene=need.scene,
            duration_seconds=need.seconds,
            camera=request.camera.value,
            intensity=request.intensity,
            held_frame_rate=request.held_frame_rate,
        )

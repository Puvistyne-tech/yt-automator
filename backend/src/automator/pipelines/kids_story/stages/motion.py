from __future__ import annotations

from automator.domain.capabilities import Capability, MotionGenerator, MotionRequest
from automator.domain.pipeline import NewArtifact, StageContext, StageOutcome
from automator.domain.pipeline_descriptors import StageDescriptor
from automator.domain.run_enums import ArtifactKind
from automator.pipelines.kids_story.art.prompts import motion_prompt
from automator.pipelines.kids_story.artifacts import (
    SHORT,
    Role,
    artifact,
    folder,
    path_of,
    required,
)
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.stages.common import (
    MP4,
    episode_size,
    kids_settings,
    load_stories,
    short_size,
)
from automator.pipelines.kids_story.story.model import Story
from automator.pipelines.kids_story.timeline.needs import ClipNeed, clip_needs
from automator.pipelines.kids_story.timeline.voices import voice_lines


def motion_request(
    context: StageContext, settings: KidsStorySettings, story: Story, need: ClipNeed
) -> MotionRequest:
    image = required(context.artifacts, Role.VISUAL, visual_key=need.visual_key)
    scene = story.scenes[need.scene] if need.scene is not None else None
    visuals = settings.visuals
    intensity = visuals.hero_motion_intensity if scene and scene.hero else visuals.motion_intensity
    width, height = short_size(settings) if need.variant == SHORT else episode_size(settings)
    return MotionRequest(
        image=path_of(context, image),
        prompt=motion_prompt(scene),
        duration_seconds=need.seconds,
        width=width,
        height=height,
        fps=settings.episode.fps,
        camera=scene.camera if scene else visuals.card_camera,
        intensity=intensity,
    )


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
        plans = [(story, voice_lines(context.artifacts, code)) for code, story in stories.items()]
        needs = clip_needs(plans, settings)
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
        )

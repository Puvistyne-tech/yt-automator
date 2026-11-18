from __future__ import annotations

from pathlib import Path

from autotube.domain.capabilities import Capability, TextGenerator
from autotube.domain.pipeline import NewArtifact, StageContext, StageOutcome
from autotube.domain.pipeline_descriptors import StageDescriptor
from autotube.domain.run_enums import ArtifactKind, LogLevel
from autotube.pipelines.kids_story.art.cards import badged_copy
from autotube.pipelines.kids_story.art.prompts import character_prompt, scene_prompt
from autotube.pipelines.kids_story.art.scene_art import Drawing, ScenePainter
from autotube.pipelines.kids_story.artifacts import (
    EPISODE,
    Role,
    artifact,
    folder,
    scene_visual_key,
)
from autotube.pipelines.kids_story.settings.root import KidsStorySettings
from autotube.pipelines.kids_story.stages.art_extras import ExtraArt
from autotube.pipelines.kids_story.stages.media_types import PNG
from autotube.pipelines.kids_story.stages.run_settings import kids_settings
from autotube.pipelines.kids_story.stages.story_loading import art_story
from autotube.pipelines.kids_story.stages.style_record import recorded_style
from autotube.pipelines.kids_story.story.model import Story

SHEET_SEED_OFFSET = 9000


class ArtStage:
    @property
    def descriptor(self) -> StageDescriptor:
        return StageDescriptor(
            id="art",
            title="Draw the pictures",
            description="Character sheets, scene and vertical pictures, cards and thumbnails.",
        )

    def run(self, context: StageContext) -> StageOutcome:
        settings = kids_settings(context)
        style = recorded_style(context, settings)
        story = art_story(context)
        images = context.providers.resolve(Capability.IMAGE)
        painter = ScenePainter(
            images, self.judge(context, settings), settings, folder(context, "art"), context.log
        )
        sheets, made = self.sheets(painter, settings, story)
        chosen: dict[int, Path] = {}
        for index in range(len(story.scenes)):
            context.log(f"drawing scene {index + 1} of {len(story.scenes)}")
            chosen[index], scene_made = self.scene_art(painter, story, index, sheets)
            made.extend(scene_made)
        made.extend(ExtraArt(context, painter, story, chosen).made())
        return StageOutcome(
            artifacts=(style, *made), provider=images.provider_id, message=f"{len(made)} pictures"
        )

    def judge(self, context: StageContext, settings: KidsStorySettings) -> TextGenerator | None:
        if not settings.visuals.use_vision_judge:
            return None
        try:
            return context.providers.resolve(Capability.LLM)
        except LookupError:
            context.log(
                "no language model for picking pictures; using the first candidate",
                LogLevel.WARNING,
            )
            return None

    def sheets(
        self, painter: ScenePainter, settings: KidsStorySettings, story: Story
    ) -> tuple[dict[str, Path], list[NewArtifact]]:
        if not settings.visuals.character_sheets:
            return {}, []
        present = set(story.character_ids)
        size = (settings.visuals.sheet_size, settings.visuals.sheet_size)
        paths: dict[str, Path] = {}
        made: list[NewArtifact] = []
        for number, member in enumerate(m for m in settings.cast if m.id in present):
            prompt = character_prompt(settings, member)
            seed = settings.visuals.base_seed + SHEET_SEED_OFFSET + number
            path = painter.draw(Drawing(prompt, size, seed, f"sheet-{member.id}"))
            paths[member.id] = path
            made.append(
                artifact(
                    ArtifactKind.IMAGE,
                    path,
                    PNG,
                    Role.CHARACTER_SHEET,
                    character=member.id,
                    prompt=prompt,
                )
            )
        return paths, made

    def scene_art(
        self, painter: ScenePainter, story: Story, index: int, sheets: dict[str, Path]
    ) -> tuple[Path, list[NewArtifact]]:
        settings = painter.settings
        scene = story.scenes[index]
        references = tuple(sheets[name] for name in scene.characters if name in sheets)
        paths = painter.candidates(scene, index, settings.video_size(EPISODE), references)
        chosen = painter.pick(scene, paths)
        made = [
            artifact(ArtifactKind.IMAGE, path, PNG, Role.CANDIDATE, scene=index, candidate=number)
            for number, path in enumerate(paths)
        ]
        final = badged_copy(
            paths[chosen], painter.out / f"scene-{index}-badge.png", settings, painter.log
        )
        made.append(
            artifact(
                ArtifactKind.IMAGE,
                final,
                PNG,
                Role.VISUAL,
                variant=EPISODE,
                visual_key=scene_visual_key(index, EPISODE),
                scene=index,
                candidate=chosen,
                prompt=scene_prompt(settings, scene),
                characters=list(scene.characters),
            )
        )
        return paths[chosen], made

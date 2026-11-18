from __future__ import annotations

from pathlib import Path

from automator.domain.capabilities import Capability, TextGenerator
from automator.domain.pipeline import NewArtifact, StageContext, StageOutcome
from automator.domain.pipeline_descriptors import StageDescriptor
from automator.domain.run_enums import ArtifactKind
from automator.pipelines.kids_story.art.cards import lettered_or_plain, lettering_for
from automator.pipelines.kids_story.art.lettering import Placement
from automator.pipelines.kids_story.art.prompts import character_prompt, scene_prompt
from automator.pipelines.kids_story.art.scene_art import Drawing, ScenePainter
from automator.pipelines.kids_story.artifacts import (
    EPISODE,
    Role,
    artifact,
    folder,
    scene_key,
    visual_key,
)
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.stages.art_extras import ExtraArt
from automator.pipelines.kids_story.stages.common import PNG, art_story, episode_size, kids_settings
from automator.pipelines.kids_story.story.model import Story

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
        story = art_story(context)
        images = context.providers.resolve(Capability.IMAGE)
        painter = ScenePainter(
            images, self.judge(context, settings), settings, folder(context, "art"), context.log
        )
        sheets, made = self.sheets(painter, settings, story)
        chosen: dict[int, Path] = {}
        for index in range(len(story.scenes)):
            context.log(f"drawing scene {index + 1} of {len(story.scenes)}")
            scene_made = self.scene_art(painter, story, index, sheets)
            chosen[index] = scene_made[-1].path
            made.extend(scene_made)
        made.extend(ExtraArt(context, painter, story, chosen).made())
        return StageOutcome(
            artifacts=tuple(made), provider=images.provider_id, message=f"{len(made)} pictures"
        )

    def judge(self, context: StageContext, settings: KidsStorySettings) -> TextGenerator | None:
        if not settings.visuals.use_vision_judge:
            return None
        try:
            return context.providers.resolve(Capability.LLM)
        except LookupError:
            context.log("no language model for picking pictures; using the first candidate")
            return None

    def sheets(
        self, painter: ScenePainter, settings: KidsStorySettings, story: Story
    ) -> tuple[dict[str, Path], list[NewArtifact]]:
        if not settings.visuals.character_sheets:
            return {}, []
        present = {name for scene in story.scenes for name in scene.characters}
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
    ) -> list[NewArtifact]:
        settings = painter.settings
        scene = story.scenes[index]
        references = tuple(sheets[name] for name in scene.characters if name in sheets)
        paths = painter.candidates(scene, index, episode_size(settings), references)
        chosen = painter.pick(scene, paths)
        prompt = scene_prompt(settings, scene)
        made = [
            artifact(ArtifactKind.IMAGE, path, PNG, Role.CANDIDATE, scene=index, candidate=number)
            for number, path in enumerate(paths)
        ]
        final = self.badged(painter, paths[chosen], index, story.language)
        made.append(
            artifact(
                ArtifactKind.IMAGE,
                final,
                PNG,
                Role.VISUAL,
                variant=EPISODE,
                visual_key=visual_key(scene_key(index), EPISODE),
                scene=index,
                candidate=chosen,
                prompt=prompt,
                characters=list(scene.characters),
            )
        )
        return made

    def badged(self, painter: ScenePainter, source: Path, index: int, language: str) -> Path:
        visuals = painter.settings.visuals
        if not visuals.overlay_series_badge:
            return source
        lettering = lettering_for(
            painter.settings,
            [painter.settings.series.name.for_language(language)],
            language,
            Placement(visuals.badge_corner.value),
            visuals.badge_size_ratio,
        )
        output = painter.out / f"scene-{index}-badge.png"
        lettered_or_plain(source, output, lettering)
        return output

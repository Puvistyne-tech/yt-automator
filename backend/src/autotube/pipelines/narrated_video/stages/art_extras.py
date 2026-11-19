from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from autotube.domain.pipeline import NewArtifact, StageContext
from autotube.domain.run_enums import ArtifactKind, LogLevel
from autotube.pipelines.narrated_video.art.cards import (
    badged_copy,
    card_lettering,
    lettered_or_plain,
    resized_or_copied,
)
from autotube.pipelines.narrated_video.art.imaging import covered_copy
from autotube.pipelines.narrated_video.art.prompts import scene_prompt, scene_subject
from autotube.pipelines.narrated_video.art.scene_art import Drawing, ScenePainter
from autotube.pipelines.narrated_video.artifacts import (
    EPISODE,
    SHORT,
    Role,
    artifact,
    scene_visual_key,
)
from autotube.pipelines.narrated_video.settings.media import ShortArtMode
from autotube.pipelines.narrated_video.stages.media_types import PNG
from autotube.pipelines.narrated_video.stages.story_loading import load_story
from autotube.pipelines.narrated_video.stages.thumbnail_art import picked_thumbnail
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.timeline.selection import short_scene_indexes
from autotube.pipelines.narrated_video.timeline.variants import INTRO, OUTRO, card_key

PORTRAIT = (9, 16)


@dataclass(frozen=True)
class ExtraArt:
    context: StageContext
    painter: ScenePainter
    story: Story
    episode_visuals: Mapping[int, Path]

    def made(self) -> list[NewArtifact]:
        made = self.thumbnails()
        if self.painter.settings.short.enabled:
            made.extend(self.short_visual(index) for index in self.short_indexes())
        landscape = made[0].path
        for language in self.context.languages:
            made.extend(self.cards(language, landscape))
        return made

    def short_indexes(self) -> list[int]:
        return short_scene_indexes(self.story, self.painter.settings.short)

    def portrait(self, source: Path, name: str, size: tuple[int, int], drawing: Drawing) -> Path:
        visuals = self.painter.settings.visuals
        if visuals.short_art_mode is ShortArtMode.CROP:
            cropped = covered_copy(
                source, self.painter.out / f"{name}.png", size, visuals.crop_focus
            )
            if cropped is not None:
                return cropped
            self.context.log(
                f"could not crop {source.name}; drawing a vertical picture", LogLevel.WARNING
            )
        return self.painter.draw(drawing)

    def short_visual(self, index: int) -> NewArtifact:
        settings = self.painter.settings
        scene = self.story.scenes[index]
        name = f"scene-{index}-short"
        size = settings.video_size(SHORT)
        prompt = scene_prompt(settings, scene)
        drawing = Drawing(
            prompt, size, self.painter.seed(index), name, subject=scene_subject(scene)
        )
        base = self.portrait(self.episode_visuals[index], name, size, drawing)
        path = badged_copy(base, self.painter.out / f"{name}-badge.png", settings, self.context.log)
        return artifact(
            ArtifactKind.IMAGE,
            path,
            PNG,
            Role.VISUAL,
            variant=SHORT,
            visual_key=scene_visual_key(index, SHORT),
            scene=index,
            prompt=drawing.prompt,
            characters=list(scene.characters),
        )

    def thumbnails(self) -> list[NewArtifact]:
        pick = picked_thumbnail(self.painter, self.story, self.context.log)
        height = self.painter.settings.thumbnail.height
        tall_size = (height * PORTRAIT[0] // PORTRAIT[1], height)
        tall_drawing = Drawing(
            pick.prompt, tall_size, pick.seed, "thumbnail-tall", subject=pick.subject
        )
        tall = self.portrait(pick.path, "thumbnail-tall", tall_size, tall_drawing)
        return [
            *(
                artifact(
                    ArtifactKind.IMAGE,
                    path,
                    PNG,
                    Role.THUMBNAIL_ART,
                    variant=variant,
                    prompt=pick.prompt,
                    candidate=pick.chosen,
                )
                for variant, path in ((EPISODE, pick.path), (SHORT, tall))
            ),
            *pick.candidate_artifacts(),
        ]

    def cards(self, language: str, background: Path) -> list[NewArtifact]:
        settings = self.painter.settings
        story = load_story(self.context, language)
        wanted = [
            card
            for card, enabled in (
                (INTRO, settings.episode.intro_card),
                (OUTRO, settings.episode.outro_card),
            )
            if enabled
        ]
        return [self.card(story, card, background) for card in wanted]

    def card(self, story: Story, card: str, background: Path) -> NewArtifact:
        settings = self.painter.settings
        base = resized_or_copied(
            background, self.painter.out / f"card-{card}-base.png", settings.video_size(EPISODE)
        )
        output = self.painter.out / f"card-{card}-{story.language}.png"
        has_text = lettered_or_plain(base, output, card_lettering(settings, story, card))
        return artifact(
            ArtifactKind.IMAGE,
            output,
            PNG,
            Role.VISUAL,
            language=story.language,
            variant=EPISODE,
            visual_key=card_key(card, story.language),
            card=card,
            lettered=has_text,
        )

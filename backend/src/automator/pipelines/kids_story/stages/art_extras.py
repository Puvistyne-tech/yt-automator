from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from automator.domain.pipeline import NewArtifact, StageContext
from automator.domain.run_enums import ArtifactKind, LogLevel
from automator.pipelines.kids_story.art.cards import (
    badged_copy,
    card_lines,
    lettered_or_plain,
    lettering_for,
    resized_or_copied,
)
from automator.pipelines.kids_story.art.imaging import covered_copy
from automator.pipelines.kids_story.art.prompts import (
    scene_prompt,
    scene_subject,
    thumbnail_prompt,
    thumbnail_subject,
)
from automator.pipelines.kids_story.art.scene_art import Drawing, ScenePainter
from automator.pipelines.kids_story.artifacts import (
    EPISODE,
    SHORT,
    Role,
    artifact,
    scene_visual_key,
)
from automator.pipelines.kids_story.settings.base import Placement
from automator.pipelines.kids_story.settings.media import ShortArtMode
from automator.pipelines.kids_story.stages.media_types import PNG
from automator.pipelines.kids_story.stages.story_loading import load_story
from automator.pipelines.kids_story.story.model import Story
from automator.pipelines.kids_story.timeline.selection import short_scene_indexes
from automator.pipelines.kids_story.timeline.variants import INTRO, OUTRO, card_key

THUMBNAIL_SEED_OFFSET = 5000
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
        settings = self.painter.settings
        prompt = thumbnail_prompt(settings, self.story)
        size = (settings.thumbnail.width, settings.thumbnail.height)
        seed = settings.visuals.base_seed + THUMBNAIL_SEED_OFFSET
        subject = thumbnail_subject(self.story)
        wide = self.painter.draw(Drawing(prompt, size, seed, "thumbnail-wide", subject=subject))
        tall_size = (size[1] * PORTRAIT[0] // PORTRAIT[1], size[1])
        tall_drawing = Drawing(prompt, tall_size, seed, "thumbnail-tall", subject=subject)
        tall = self.portrait(wide, "thumbnail-tall", tall_size, tall_drawing)
        return [
            artifact(
                ArtifactKind.IMAGE, wide, PNG, Role.THUMBNAIL_ART, variant=EPISODE, prompt=prompt
            ),
            artifact(
                ArtifactKind.IMAGE, tall, PNG, Role.THUMBNAIL_ART, variant=SHORT, prompt=prompt
            ),
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
        lettering = lettering_for(
            settings,
            card_lines(settings, story, card),
            story.language,
            Placement.CENTER,
            settings.episode.card_text_size_ratio,
        )
        has_text = lettered_or_plain(base, output, lettering)
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

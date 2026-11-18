from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from autotube.domain.pipeline import NewArtifact, StageLog
from autotube.domain.run_enums import ArtifactKind
from autotube.pipelines.kids_story.art.prompts import (
    picture_judge_request,
    thumbnail_prompt,
    thumbnail_subject,
    thumbnail_visual,
)
from autotube.pipelines.kids_story.art.scene_art import Drawing, ScenePainter
from autotube.pipelines.kids_story.artifacts import Role, artifact
from autotube.pipelines.kids_story.stages.media_types import PNG
from autotube.pipelines.kids_story.story.model import Story

THUMBNAIL_SEED_OFFSET = 5000
WIDE_NAME = "thumbnail-wide"


@dataclass(frozen=True)
class ThumbnailPick:
    prompt: str
    seed: int
    subject: str
    candidates: list[Path]
    chosen: int

    @property
    def path(self) -> Path:
        return self.candidates[self.chosen]

    def candidate_artifacts(self) -> list[NewArtifact]:
        if len(self.candidates) < 2:
            return []
        return [
            artifact(ArtifactKind.IMAGE, path, PNG, Role.CANDIDATE, thumbnail=True, candidate=n)
            for n, path in enumerate(self.candidates)
        ]


def candidate_name(number: int) -> str:
    return WIDE_NAME if number == 0 else f"{WIDE_NAME}-c{number}"


def drawn_candidates(painter: ScenePainter, prompt: str, seed: int, subject: str) -> list[Path]:
    thumbnail = painter.settings.thumbnail
    size = (thumbnail.width, thumbnail.height)
    return [
        painter.draw(Drawing(prompt, size, seed + number, candidate_name(number), subject=subject))
        for number in range(thumbnail.candidates)
    ]


def picked_thumbnail(painter: ScenePainter, story: Story, log: StageLog) -> ThumbnailPick:
    settings = painter.settings
    prompt = thumbnail_prompt(settings, story)
    seed = settings.visuals.base_seed + THUMBNAIL_SEED_OFFSET
    subject = thumbnail_subject(story)
    paths = drawn_candidates(painter, prompt, seed, subject)
    characters = sorted(story.character_ids)
    request = picture_judge_request(settings, thumbnail_visual(story), characters, paths)
    chosen = painter.pick_by(request, paths)
    if len(paths) > 1:
        log(f"thumbnail: kept picture {chosen + 1} of {len(paths)}")
    return ThumbnailPick(prompt, seed + chosen, subject, paths, chosen)

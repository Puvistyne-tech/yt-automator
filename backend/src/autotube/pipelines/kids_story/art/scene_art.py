from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from autotube.domain.capabilities import ImageGenerator, ImageRequest, TextGenerator
from autotube.domain.pipeline import StageLog
from autotube.domain.run_enums import LogLevel
from autotube.pipelines.kids_story.art.prompts import (
    judge_request,
    parse_choice,
    scene_prompt,
    scene_subject,
)
from autotube.pipelines.kids_story.settings.root import KidsStorySettings
from autotube.pipelines.kids_story.story.model import StoryScene
from autotube.pipelines.kids_story.styles.resolve import resolve_style

SEED_STRIDE = 100


@dataclass(frozen=True)
class Drawing:
    prompt: str
    size: tuple[int, int]
    seed: int
    name: str
    references: tuple[Path, ...] = ()
    subject: str = ""


@dataclass(frozen=True)
class ScenePainter:
    images: ImageGenerator
    judge: TextGenerator | None
    settings: KidsStorySettings
    out: Path
    log: StageLog

    def draw(self, drawing: Drawing) -> Path:
        style = resolve_style(self.settings)
        request = ImageRequest(
            prompt=drawing.prompt,
            negative_prompt=style.negative_prompt,
            style=style.hints(drawing.subject),
            width=drawing.size[0],
            height=drawing.size[1],
            seed=drawing.seed,
            reference_images=drawing.references,
        )
        return self.images.generate(request, self.out / f"{drawing.name}.png")

    def seed(self, index: int, candidate: int = 0) -> int:
        return self.settings.visuals.base_seed + index * SEED_STRIDE + candidate

    def candidate_count(self, scene: StoryScene) -> int:
        visuals = self.settings.visuals
        return visuals.hero_candidates if scene.hero else visuals.image_candidates

    def candidates(
        self, scene: StoryScene, index: int, size: tuple[int, int], references: tuple[Path, ...]
    ) -> list[Path]:
        prompt = scene_prompt(self.settings, scene)
        return [
            self.draw(
                Drawing(
                    prompt,
                    size,
                    self.seed(index, number),
                    f"scene-{index}-c{number}",
                    references,
                    scene_subject(scene),
                )
            )
            for number in range(self.candidate_count(scene))
        ]

    def pick(self, scene: StoryScene, paths: Sequence[Path]) -> int:
        if self.judge is None or len(paths) < 2:
            return 0
        try:
            answer = self.judge.generate(judge_request(self.settings, scene, paths))
        except Exception as error:
            self.log(
                f"picture judge failed, using the first picture: {error}",
                LogLevel.WARNING,
            )
            return 0
        return parse_choice(answer, len(paths))

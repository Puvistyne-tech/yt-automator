from __future__ import annotations

from autotube.domain.quality import ScoreItem
from autotube.pipelines.narrated_video.scoring.content_items import gate_item
from autotube.pipelines.narrated_video.scoring.inputs import ScoreInputs, ScoreRule
from autotube.pipelines.narrated_video.story.gates import Gate

STRUCTURE_ITEM = "structure"


def structure_item(title: str, gate: Gate) -> ScoreRule:
    def scored(inputs: ScoreInputs) -> ScoreItem | None:
        weight = inputs.settings.quality.weights.structure
        return gate_item(inputs, STRUCTURE_ITEM, title, weight, gate)

    return scored

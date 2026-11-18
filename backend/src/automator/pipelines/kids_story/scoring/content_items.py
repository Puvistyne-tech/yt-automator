from __future__ import annotations

from automator.domain.artifact_selection import text_list
from automator.domain.quality import ScoreItem
from automator.domain.run_parts import Artifact
from automator.pipelines.kids_story.artifacts import Role, text, with_role
from automator.pipelines.kids_story.scoring.inputs import ScoreInputs
from automator.pipelines.kids_story.scoring.measures import FULL, average
from automator.pipelines.kids_story.story.gates import (
    Gate,
    ending_problems,
    reading_level_problems,
)


def gate_item(
    inputs: ScoreInputs, item_id: str, title: str, weight: float, gate: Gate
) -> ScoreItem | None:
    if not inputs.stories:
        return None
    problems = {code: gate(story, inputs.settings) for code, story in inputs.stories.items()}
    per_problem = inputs.settings.quality.points_lost_per_problem
    return ScoreItem(
        id=item_id,
        title=title,
        score=average([max(FULL - per_problem * len(found), 0.0) for found in problems.values()]),
        weight=weight,
        detail="; ".join(f"{code}: {', '.join(found) or 'ok'}" for code, found in problems.items()),
    )


def reading_level(inputs: ScoreInputs) -> ScoreItem | None:
    weight = inputs.settings.quality.weights.reading_level
    return gate_item(inputs, "reading_level", "Reading level", weight, reading_level_problems)


def moral_and_refrain(inputs: ScoreInputs) -> ScoreItem | None:
    weight = inputs.settings.quality.weights.moral_and_refrain
    return gate_item(inputs, "moral_and_refrain", "Moral and refrain", weight, ending_problems)


def consistent(inputs: ScoreInputs, visual: Artifact) -> bool:
    prompt = text(visual.meta.get("prompt"))
    members = inputs.settings.characters(text_list(visual.meta.get("characters")))
    return all(member.visual_descriptor in prompt for member in members)


def character_consistency(inputs: ScoreInputs) -> ScoreItem | None:
    visuals = [
        found
        for found in with_role(inputs.artifacts, Role.VISUAL)
        if isinstance(found.meta.get("characters"), list)
    ]
    if not visuals:
        return None
    good = sum(1 for found in visuals if consistent(inputs, found))
    return ScoreItem(
        id="character_consistency",
        title="Character consistency",
        score=FULL * good / len(visuals),
        weight=inputs.settings.quality.weights.character_consistency,
        detail=f"{good} of {len(visuals)} picture prompts carry every character's fixed look",
    )

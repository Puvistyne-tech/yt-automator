from __future__ import annotations

from automator.domain.quality import ScoreItem
from automator.domain.run_parts import Artifact
from automator.pipelines.kids_story.artifacts import Role, text, with_role
from automator.pipelines.kids_story.scoring.inputs import ScoreInputs
from automator.pipelines.kids_story.scoring.measures import FULL, average
from automator.pipelines.kids_story.story.gates import ending_problems, reading_level_problems

HALF = 50.0


def reading_level(inputs: ScoreInputs) -> ScoreItem | None:
    if not inputs.stories:
        return None
    problems = {
        code: reading_level_problems(story, inputs.settings)
        for code, story in inputs.stories.items()
    }
    return ScoreItem(
        id="reading_level",
        title="Reading level",
        score=average([max(FULL - HALF * len(found), 0.0) for found in problems.values()]),
        weight=inputs.settings.quality.weights.reading_level,
        detail="; ".join(f"{code}: {', '.join(found) or 'ok'}" for code, found in problems.items()),
    )


def moral_and_refrain(inputs: ScoreInputs) -> ScoreItem | None:
    if not inputs.stories:
        return None
    problems = {
        code: ending_problems(story, inputs.settings) for code, story in inputs.stories.items()
    }
    return ScoreItem(
        id="moral_and_refrain",
        title="Moral and refrain",
        score=average([max(FULL - HALF * len(found), 0.0) for found in problems.values()]),
        weight=inputs.settings.quality.weights.moral_and_refrain,
        detail="; ".join(f"{code}: {', '.join(found) or 'ok'}" for code, found in problems.items()),
    )


def consistent(inputs: ScoreInputs, visual: Artifact) -> bool:
    prompt = text(visual.meta.get("prompt"))
    names = visual.meta.get("characters")
    ids = [str(name) for name in names] if isinstance(names, list) else []
    members = [member for name in ids if (member := inputs.settings.character(name)) is not None]
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

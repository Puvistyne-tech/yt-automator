from __future__ import annotations

CAST_PATHS = (
    "cast",
    "story.morals",
    "story.ending_style",
    "story.ending_scenes",
    "story.lead_mode",
    "story.cast_per_episode",
    "series.refrain",
    "visuals.character_sheets",
    "quality.weights.moral_and_refrain",
    "quality.weights.character_consistency",
)
LIST_COUNT_PATHS = ("story.item_count",)
QUIZ_COUNT_PATHS = ("story.quiz_questions", "story.answer_choices")
SCENE_COUNT_PATHS = ("story.scene_count_min", "story.scene_count_max")
DURATION_PATHS = ("story.target_duration_seconds", "story.duration_tolerance_seconds")
COUNTED_PATHS = (*SCENE_COUNT_PATHS, *DURATION_PATHS)

from __future__ import annotations

from autotube.domain.pipeline_templates import TemplateAudience

KIDS_STORY = "kids_story"
PACKAGED_FORMATS: dict[str, tuple[str, TemplateAudience]] = {
    "amazing_facts": ("list", TemplateAudience.GENERAL),
    "daily_motivation": ("explainer", TemplateAudience.GENERAL),
    "fun_facts_for_kids": ("list", TemplateAudience.KIDS),
    "history_in_five_minutes": ("explainer", TemplateAudience.GENERAL),
    "quick_quiz": ("quiz", TemplateAudience.GENERAL),
    "scary_stories": ("story", TemplateAudience.GENERAL),
    "top_ten_countdown": ("countdown", TemplateAudience.GENERAL),
}
BUILTIN_IDS = [KIDS_STORY, *PACKAGED_FORMATS]

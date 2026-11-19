from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from autotube.pipelines.narrated_video.settings.base import (
    LocalizedList,
    LocalizedText,
    SettingsSection,
    localized_list,
    localized_text,
)
from autotube.pipelines.narrated_video.settings.choices import CATEGORY_CHOICES

DESCRIPTION_EN = (
    "{title}\n\n"
    "A gentle story from {series} about {theme}. {tagline}.\n\n"
    "Today's lesson: {moral}\n\n"
    "What do you think happens next?\n{questions}\n\n"
    "Watch together, talk together, and share a smile.\n\n"
    "{hashtags}"
)
DESCRIPTION_TA = (
    "{title}\n\n"
    "{series} வழங்கும் ஒரு இனிய கதை. {tagline}.\n\n"
    "இன்றைய பாடம்: {moral}\n\n"
    "அடுத்து என்ன நடக்கும் என்று நினைக்கிறீர்கள்?\n{questions}\n\n"
    "சேர்ந்து பாருங்கள், சேர்ந்து பேசுங்கள், புன்னகையைப் பகிருங்கள்.\n\n"
    "{hashtags}"
)
FORMAT_PLACEHOLDERS = (
    "{moral}, {characters} and {refrain} for stories, {takeaway} for explainers, {count} and "
    "{items} for lists and countdowns, {question_count} for quizzes"
)
TAGS_EN = [
    "kids stories",
    "stories for kids",
    "moral stories",
    "bedtime stories",
    "animated stories",
]
TAGS_TA = [
    "தமிழ் கதைகள்",
    "குழந்தைகள் கதைகள்",
    "நீதிக் கதைகள்",
    "Tamil kids stories",
]


class YouTubeCategory(StrEnum):
    FILM_AND_ANIMATION = "1"
    ENTERTAINMENT = "24"
    EDUCATION = "27"


class MetadataSettings(SettingsSection):
    title_template: LocalizedText = localized_text(
        "{title} | {series}",
        "{title} | {series}",
        "Episode title",
        "Episode title per language; {title}, {series} and {theme} are filled in, plus the "
        f"format's own: {FORMAT_PLACEHOLDERS}.",
    )
    short_title_template: LocalizedText = localized_text(
        "{title} #Shorts",
        "{title} #Shorts",
        "Short title",
        "Short title per language; {title}, {series}, {theme} and {hook} are filled in, plus the "
        f"format's own: {FORMAT_PLACEHOLDERS}.",
    )
    description_template: LocalizedText = localized_text(
        DESCRIPTION_EN,
        DESCRIPTION_TA,
        "Description",
        "Placeholders: {title} {series} {tagline} {theme} {questions} {hashtags} {hook}. Which "
        "others work depends on the format: stories add {moral} {characters} {refrain}, "
        "explainers add {takeaway}, lists and countdowns add {count} {items}, quizzes add "
        "{question_count}. Any other placeholder is left empty.",
    )
    tags: LocalizedList = localized_list(
        TAGS_EN,
        TAGS_TA,
        "Tags",
        "Search tags added to every upload; tags past YouTube's 500 letter limit are dropped.",
    )
    hashtags: LocalizedList = localized_list(
        ["#KidsStories", "#MoralStories", "#BedtimeStories"],
        ["#தமிழ்கதைகள்", "#KidsStories", "#MoralStories"],
        "Hashtags",
        "Placed where {hashtags} appears in the description; any still missing are added at "
        "the end when the video is uploaded, up to YouTube's 60 hashtags.",
    )
    playlist_title: LocalizedText = localized_text(
        "{series}",
        "{series}",
        "Playlist title",
        "Shown with the episode for reference, with {series} filled in; uploads go to the "
        "target's own playlist.",
    )
    category: YouTubeCategory = Field(
        default=YouTubeCategory.FILM_AND_ANIMATION,
        json_schema_extra=CATEGORY_CHOICES,
        title="Category",
        description="The YouTube category of every upload.",
    )

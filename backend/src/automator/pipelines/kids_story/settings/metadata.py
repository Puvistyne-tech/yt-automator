from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from automator.pipelines.kids_story.settings.base import (
    LocalizedList,
    LocalizedText,
    SettingsSection,
    localized_list,
    localized_text,
)

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
TAGS_EN = [
    "kids stories",
    "stories for kids",
    "moral stories",
    "bedtime stories",
    "animated stories",
    "Kutty Stories",
]
TAGS_TA = [
    "தமிழ் கதைகள்",
    "குழந்தைகள் கதைகள்",
    "நீதிக் கதைகள்",
    "Tamil kids stories",
    "Kutty Stories",
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
        "Placeholders: {title} {series} {moral} {theme}.",
    )
    short_title_template: LocalizedText = localized_text(
        "{title} #Shorts",
        "{title} #Shorts",
        "Short title",
        "Placeholders: {title} {series} {moral} {theme} {hook}.",
    )
    description_template: LocalizedText = localized_text(
        DESCRIPTION_EN,
        DESCRIPTION_TA,
        "Description",
        "Placeholders: {title} {series} {tagline} {moral} {theme} {questions} {hashtags} "
        "{characters} {refrain} {hook}.",
    )
    tags: LocalizedList = localized_list(TAGS_EN, TAGS_TA, "Tags", "Search tags per language.")
    hashtags: LocalizedList = localized_list(
        ["#KidsStories", "#KuttyStories", "#MoralStories"],
        ["#தமிழ்கதைகள்", "#KuttyStories", "#KidsStories"],
        "Hashtags",
        "Added where {hashtags} appears in the description.",
    )
    playlist_title: LocalizedText = localized_text(
        "Kutty Stories",
        "குட்டி கதைகள்",
        "Playlist title",
        "The playlist each episode belongs to, per language.",
    )
    category: YouTubeCategory = Field(
        default=YouTubeCategory.FILM_AND_ANIMATION,
        title="Category",
        description="The YouTube category of every upload.",
    )

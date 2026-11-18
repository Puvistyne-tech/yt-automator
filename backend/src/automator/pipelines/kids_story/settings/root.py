from __future__ import annotations

from pydantic import Field, model_validator

from automator.pipelines.kids_story.settings.base import SettingsSection
from automator.pipelines.kids_story.settings.cast import Character, default_cast
from automator.pipelines.kids_story.settings.media import (
    MusicSettings,
    SoundEffectSettings,
    VisualSettings,
    VoiceSettings,
)
from automator.pipelines.kids_story.settings.metadata import MetadataSettings
from automator.pipelines.kids_story.settings.output import (
    EpisodeSettings,
    ShortSettings,
    ThumbnailSettings,
)
from automator.pipelines.kids_story.settings.quality import QualitySettings
from automator.pipelines.kids_story.settings.series import SafetySettings, SeriesSettings
from automator.pipelines.kids_story.settings.story import StorySettings
from automator.pipelines.kids_story.settings.subtitles import SubtitleSettings


class KidsStorySettings(SettingsSection):
    series: SeriesSettings = Field(
        default_factory=SeriesSettings, title="Series", description="The series bible."
    )
    cast: list[Character] = Field(
        default_factory=default_cast,
        min_length=1,
        title="Cast",
        description="The recurring characters. The first one leads every story.",
    )
    story: StorySettings = Field(
        default_factory=StorySettings, title="Story", description="How stories are written."
    )
    safety: SafetySettings = Field(
        default_factory=SafetySettings, title="Safety", description="Words stories must avoid."
    )
    visuals: VisualSettings = Field(
        default_factory=VisualSettings, title="Pictures", description="Pictures and motion."
    )
    voice: VoiceSettings = Field(
        default_factory=VoiceSettings, title="Voice", description="Narration."
    )
    subtitles: SubtitleSettings = Field(
        default_factory=SubtitleSettings, title="Subtitles", description="Subtitles and captions."
    )
    music: MusicSettings = Field(
        default_factory=MusicSettings, title="Music", description="Background music."
    )
    sound_effects: SoundEffectSettings = Field(
        default_factory=SoundEffectSettings, title="Sound effects", description="Story effects."
    )
    episode: EpisodeSettings = Field(
        default_factory=EpisodeSettings, title="Episode", description="The 16:9 episode."
    )
    short: ShortSettings = Field(
        default_factory=ShortSettings, title="Short", description="The vertical 9:16 Short."
    )
    thumbnail: ThumbnailSettings = Field(
        default_factory=ThumbnailSettings, title="Thumbnail", description="Thumbnail pictures."
    )
    metadata: MetadataSettings = Field(
        default_factory=MetadataSettings, title="Upload details", description="Titles and tags."
    )
    quality: QualitySettings = Field(
        default_factory=QualitySettings, title="Quality checks", description="Scoring."
    )

    @model_validator(mode="after")
    def check_cast(self) -> KidsStorySettings:
        ids = [member.id for member in self.cast]
        if len(ids) != len(set(ids)):
            raise ValueError("character ids must be unique")
        return self

    def character(self, character_id: str) -> Character | None:
        return next((member for member in self.cast if member.id == character_id), None)

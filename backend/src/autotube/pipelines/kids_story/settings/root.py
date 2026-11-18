from __future__ import annotations

from collections.abc import Sequence

from pydantic import Field, model_validator

from autotube.domain.video_look import VideoQuality
from autotube.pipelines.kids_story.artifacts import SHORT
from autotube.pipelines.kids_story.settings.base import SettingsSection
from autotube.pipelines.kids_story.settings.cast import Character, default_cast
from autotube.pipelines.kids_story.settings.legacy_look import migrated_look
from autotube.pipelines.kids_story.settings.look import LookSettings
from autotube.pipelines.kids_story.settings.media import (
    MusicSettings,
    VisualSettings,
    VoiceSettings,
)
from autotube.pipelines.kids_story.settings.metadata import MetadataSettings
from autotube.pipelines.kids_story.settings.output import (
    EpisodeSettings,
    ShortSettings,
    size_of,
)
from autotube.pipelines.kids_story.settings.quality import QualitySettings
from autotube.pipelines.kids_story.settings.series import SafetySettings, SeriesSettings
from autotube.pipelines.kids_story.settings.sound_effects import SoundEffectSettings
from autotube.pipelines.kids_story.settings.story import StorySettings
from autotube.pipelines.kids_story.settings.subtitles import SubtitleSettings
from autotube.pipelines.kids_story.settings.thumbnail import ThumbnailSettings
from autotube.pipelines.kids_story.settings.video_look import FOLLOW_EPISODE_FPS


class KidsStorySettings(SettingsSection):
    series: SeriesSettings = Field(
        default_factory=SeriesSettings,
        title="Series",
        description="Name, refrain and rules shared by every story.",
    )
    look: LookSettings = Field(
        default_factory=LookSettings,
        title="Visual style",
        description="The look of every picture: style, colours, light and detail.",
    )
    cast: list[Character] = Field(
        default_factory=default_cast,
        min_length=1,
        title="Cast",
        description="The recurring characters. The first one leads every story.",
    )
    story: StorySettings = Field(
        default_factory=StorySettings,
        title="Story",
        description="How each story is written, checked and translated.",
    )
    safety: SafetySettings = Field(
        default_factory=SafetySettings,
        title="Safety",
        description="Words and brand names a story must never contain, and what is never drawn.",
    )
    visuals: VisualSettings = Field(
        default_factory=VisualSettings,
        title="Pictures",
        description="Scene pictures, the brand mark and camera motion.",
    )
    voice: VoiceSettings = Field(
        default_factory=VoiceSettings, title="Voice", description="Narrator voice and speed."
    )
    subtitles: SubtitleSettings = Field(
        default_factory=SubtitleSettings,
        title="Subtitles",
        description="Subtitles drawn on the video and uploaded as captions.",
    )
    music: MusicSettings = Field(
        default_factory=MusicSettings,
        title="Music",
        description="The soft music bed under every video.",
    )
    sound_effects: SoundEffectSettings = Field(
        default_factory=SoundEffectSettings,
        title="Sound effects",
        description="Short sounds cued by the story.",
    )
    episode: EpisodeSettings = Field(
        default_factory=EpisodeSettings,
        title="Episode",
        description="Size, pacing, cards and sound of the 16:9 episode.",
    )
    short: ShortSettings = Field(
        default_factory=ShortSettings,
        title="Short",
        description="Whether and how the vertical 9:16 Short is cut.",
    )
    thumbnail: ThumbnailSettings = Field(
        default_factory=ThumbnailSettings,
        title="Thumbnail",
        description="Thumbnail pictures and their lettering.",
    )
    metadata: MetadataSettings = Field(
        default_factory=MetadataSettings,
        title="Upload details",
        description="Titles, descriptions, tags and playlist for every upload.",
    )
    quality: QualitySettings = Field(
        default_factory=QualitySettings,
        title="Quality checks",
        description="How each run is scored before review.",
    )

    @model_validator(mode="before")
    @classmethod
    def migrate_look(cls, data: object) -> object:
        return migrated_look(data)

    @model_validator(mode="after")
    def check_cast(self) -> KidsStorySettings:
        ids = [member.id for member in self.cast]
        if len(ids) != len(set(ids)):
            raise ValueError("character ids must be unique")
        return self

    def character(self, character_id: str) -> Character | None:
        return next((member for member in self.cast if member.id == character_id), None)

    def characters(self, character_ids: Sequence[str]) -> list[Character]:
        return [member for name in character_ids if (member := self.character(name)) is not None]

    def video_size(self, variant: str) -> tuple[int, int]:
        resolution = self.short.resolution if variant == SHORT else self.episode.resolution
        return size_of(resolution)

    def video_fps(self, variant: str) -> int:
        if variant == SHORT and self.short.fps != FOLLOW_EPISODE_FPS:
            return self.short.fps
        return self.episode.fps

    def video_quality(self, variant: str) -> VideoQuality:
        return self.short.video_quality if variant == SHORT else self.episode.video_quality

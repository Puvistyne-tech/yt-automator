from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from autotube.domain.capabilities import Capability, SpeechRequest, SpeechSynthesizer
from autotube.domain.pipeline import NewArtifact, StageContext, StageOutcome
from autotube.domain.pipeline_descriptors import StageDescriptor
from autotube.domain.run_enums import ArtifactKind
from autotube.pipelines.narrated_video.artifacts import Role, artifact, folder, scene_key
from autotube.pipelines.narrated_video.publishing.templates import template_values
from autotube.pipelines.narrated_video.settings.base import LocalizedText
from autotube.pipelines.narrated_video.settings.root import KidsStorySettings
from autotube.pipelines.narrated_video.stages.media_types import WAV
from autotube.pipelines.narrated_video.stages.run_settings import kids_settings
from autotube.pipelines.narrated_video.stages.story_loading import load_story
from autotube.pipelines.narrated_video.stages.voice_check import check_note, checked_speech
from autotube.pipelines.narrated_video.story.model import Story
from autotube.pipelines.narrated_video.story.normalise import speakable
from autotube.pipelines.narrated_video.text.templates import render_template
from autotube.pipelines.narrated_video.timeline.variants import HOOK, INTRO, OUTRO
from autotube.pipelines.narrated_video.timeline.voices import timings_meta

NARRATOR = "narrator"


@dataclass(frozen=True)
class Line:
    segment: str
    text: str
    speaker: str = NARRATOR
    scene: int | None = None


def filled_line(line: LocalizedText, values: Mapping[str, str], language: str) -> str:
    return render_template(line.for_language(language), values)


def lines_to_speak(story: Story, settings: KidsStorySettings) -> list[Line]:
    language, values = story.language, template_values(story, settings)
    lines = [
        Line(scene_key(index), scene.narration, scene.speaker, index)
        for index, scene in enumerate(story.scenes)
    ]
    if settings.voice.include_intro:
        lines.insert(0, Line(INTRO, filled_line(settings.series.intro_line, values, language)))
    if settings.voice.include_outro:
        lines.append(Line(OUTRO, filled_line(settings.series.outro_line, values, language)))
    if settings.short.enabled and settings.short.hook_line and story.hook_line:
        lines.append(Line(HOOK, story.hook_line))
    return [line for line in lines if line.text.strip()]


def voice_for(settings: KidsStorySettings, speaker: str, language: str) -> str:
    member = settings.character(speaker)
    override = member.voice_override.for_language(language) if member else ""
    return override or settings.voice.narrator_voice.for_language(language)


def speech_request(settings: KidsStorySettings, line: Line, language: str) -> SpeechRequest:
    return SpeechRequest(
        text=speakable(line.text, language),
        language=language,
        voice=voice_for(settings, line.speaker, language),
        speed=settings.voice.speed.for_language(language),
    )


class VoiceStage:
    @property
    def descriptor(self) -> StageDescriptor:
        return StageDescriptor(
            id="voice",
            title="Record the narration",
            description="Speaks every scene per language and keeps the word timings.",
        )

    def run(self, context: StageContext) -> StageOutcome:
        settings = kids_settings(context)
        tts = context.providers.resolve(Capability.TTS)
        made: list[NewArtifact] = []
        for language in context.languages:
            story = load_story(context, language)
            lines = lines_to_speak(story, settings)
            context.log(f"recording {len(lines)} lines in {language}")
            made.extend(self.recorded(context, tts, settings, line, language) for line in lines)
        return StageOutcome(
            artifacts=tuple(made), provider=tts.provider_id, message=f"{len(made)} lines recorded"
        )

    def recorded(
        self,
        context: StageContext,
        tts: SpeechSynthesizer,
        settings: KidsStorySettings,
        line: Line,
        language: str,
    ) -> NewArtifact:
        request = speech_request(settings, line, language)
        output = folder(context, "voice") / f"{language}-{line.segment}.wav"
        check = settings.voice.quality_check
        result = checked_speech(tts, request, output, check)
        note = check_note(result, check, f"{language} {line.segment}")
        if note is not None:
            context.log(*note)
        speech = result.speech
        return artifact(
            ArtifactKind.AUDIO,
            speech.path,
            WAV,
            Role.NARRATION,
            language=language,
            segment=line.segment,
            scene=line.scene,
            text=request.text,
            voice=request.voice,
            duration_seconds=speech.duration_seconds,
            timing_source=speech.timing_source.value,
            words=timings_meta(speech.words),
            error_rate=result.error_rate,
            attempts=result.attempts,
        )

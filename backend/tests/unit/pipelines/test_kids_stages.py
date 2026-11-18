from __future__ import annotations

from pathlib import Path

import pytest

from automator.domain.pipeline import Stage
from automator.domain.run_enums import ArtifactKind
from automator.domain.run_parts import Artifact
from automator.pipelines.kids_story.artifacts import MissingArtifactError
from automator.pipelines.kids_story.plugin import KidsStoryPipeline
from automator.pipelines.kids_story.settings.root import KidsStorySettings
from automator.pipelines.kids_story.stages.story import StoryStage
from automator.pipelines.kids_story.stages.voice import VoiceStage
from tests.unit.pipelines.kids_data import StageRig, quick_settings, smart_writer
from tests.unit.pipelines.kids_fakes import FakeProviders, failing_writer

STAGES: tuple[Stage, ...] = tuple(KidsStoryPipeline().stages())


def run_chain(rig: StageRig, until: str | None = None) -> StageRig:
    for stage in STAGES:
        rig.run(stage)
        if stage.descriptor.id == until:
            break
    return rig


def roles(rig: StageRig, kind: ArtifactKind) -> list[tuple[str | None, str | None]]:
    return sorted(
        ((item.language, item.variant) for item in rig.artifacts if item.kind is kind),
        key=str,
    )


def meta_of(rig: StageRig, role: str) -> list[Artifact]:
    return [item for item in rig.artifacts if item.meta.get("role") == role]


BOTH = [("en", "episode"), ("en", "short"), ("ta", "episode"), ("ta", "short")]


def test_full_chain_writes_translates_and_packages_both_languages(tmp_path: Path) -> None:
    writer = smart_writer()
    rig = run_chain(StageRig(tmp_path, providers=FakeProviders(writer=writer)))
    stories = meta_of(rig, "story")
    assert [(item.language, item.meta["source"]) for item in stories] == [
        ("en", "llm"),
        ("ta", "llm"),
    ]
    assert roles(rig, ArtifactKind.THUMBNAIL) == BOTH
    assert roles(rig, ArtifactKind.METADATA) == BOTH
    assert roles(rig, ArtifactKind.SUBTITLE) == BOTH
    finals = [(item.language, item.variant) for item in meta_of(rig, "final_video")]
    assert sorted(finals) == BOTH
    assert all(item.language is None for item in meta_of(rig, "clip"))
    assert any(request.images for request in writer.requests)
    tamil_meta = next(item for item in meta_of(rig, "upload_metadata") if item.language == "ta")
    assert tamil_meta.meta["made_for_kids"] is True and tamil_meta.meta["default_language"] == "ta"


def test_failing_writer_falls_back_to_a_bundled_story(tmp_path: Path) -> None:
    rig = StageRig(tmp_path, providers=FakeProviders(writer=failing_writer()))
    outcome = rig.run(StoryStage())
    assert outcome.provider == "bundled"
    assert {item.meta["source"] for item in meta_of(rig, "story")} == {"bundled"}
    assert any("falling back" in line for line in rig.logs)


def test_missing_writer_and_bundled_only_skip_the_model(tmp_path: Path) -> None:
    assert StageRig(tmp_path / "a").run(StoryStage()).provider == "bundled"
    writer = smart_writer()
    settings = quick_settings(story={"source": "bundled_only"})
    rig = StageRig(tmp_path / "b", settings=settings, providers=FakeProviders(writer=writer))
    assert rig.run(StoryStage()).provider == "bundled" and writer.requests == []


def test_scene_bounds_reject_the_model_story(tmp_path: Path) -> None:
    writer = smart_writer()
    settings = quick_settings(
        story={"scene_count_min": 10, "scene_count_max": 12, "max_attempts": 2}
    )
    rig = StageRig(tmp_path, settings=settings, providers=FakeProviders(writer=writer))
    assert rig.run(StoryStage()).provider == "bundled"
    assert len(writer.requests) == 2 and "use between 10 and 12 scenes" in writer.requests[1].prompt


def test_vision_judge_picks_and_can_be_turned_off(tmp_path: Path) -> None:
    rig = run_chain(
        StageRig(tmp_path / "on", providers=FakeProviders(writer=smart_writer("2"))), "art"
    )
    hero_visuals = [
        item
        for item in meta_of(rig, "visual")
        if item.meta.get("scene") == 0 and item.variant == "episode"
    ]
    assert hero_visuals[0].meta["candidate"] == 1
    writer = smart_writer("2")
    settings = quick_settings(visuals={"use_vision_judge": False})
    off = run_chain(
        StageRig(tmp_path / "off", settings=settings, providers=FakeProviders(writer=writer)), "art"
    )
    assert not any(request.images for request in writer.requests)
    assert {
        item.meta["candidate"] for item in meta_of(off, "visual") if "candidate" in item.meta
    } == {0}


def test_music_disabled_or_missing_leaves_no_bed(tmp_path: Path) -> None:
    settings = quick_settings(music={"enabled": False}, sound_effects={"enabled": False})
    providers = FakeProviders()
    rig = run_chain(StageRig(tmp_path / "off", settings=settings, providers=providers))
    assert (
        meta_of(rig, "music") == []
        and providers.music is not None
        and providers.music.requests == []
    )
    assert all(
        made.music is None and not made.sound_effects
        for made in providers.media.compositions.values()
    )
    missing = FakeProviders(music=None)
    rig = run_chain(StageRig(tmp_path / "none", providers=missing))
    assert meta_of(rig, "music") == [] and any("no music provider" in line for line in rig.logs)


def test_music_and_effects_follow_settings(tmp_path: Path) -> None:
    settings = quick_settings(
        music={"mood_prompt": "soft harp"}, sound_effects={"prompt_template": "tiny {cue}"}
    )
    providers = FakeProviders()
    run_chain(StageRig(tmp_path, settings=settings, providers=providers))
    assert providers.music is not None
    prompts = [request.prompt for request in providers.music.requests]
    assert "soft harp" in prompts and any(prompt.startswith("tiny ") for prompt in prompts)
    episode = providers.media.compositions["en-episode.mp4"]
    assert episode.music is not None and episode.sound_effects


def test_short_disabled_and_single_language(tmp_path: Path) -> None:
    settings = quick_settings(short={"enabled": False})
    providers = FakeProviders()
    rig = run_chain(StageRig(tmp_path, settings=settings, languages=("en",), providers=providers))
    assert roles(rig, ArtifactKind.METADATA) == [("en", "episode")]
    assert not any(
        item.variant == "short" for item in rig.artifacts if item.kind is ArtifactKind.VIDEO
    )
    assert all(request.language == "en" for request in providers.speech.requests)
    assert not any(line.endswith("-hook.wav") for line in (item.filename for item in rig.artifacts))


def test_settings_reach_requests_compositions_and_metadata(tmp_path: Path) -> None:
    settings = quick_settings(
        voice={"narrator_voice": {"en": "warm_en", "ta": "warm_ta"}, "speed": 0.8},
        subtitles={"burn_in_episode": True, "burn_in_short": False},
        metadata={"title_template": {"en": "EN {title}", "ta": "TA {title}"}},
        visuals={"motion_intensity": 0.2},
        story={"theme_mode": "fixed", "fixed_theme": "sharing"},
    )
    providers = FakeProviders()
    rig = run_chain(StageRig(tmp_path, settings=settings, providers=providers))
    voices = {
        (request.language, request.voice, request.speed) for request in providers.speech.requests
    }
    assert voices == {("en", "warm_en", 0.8), ("ta", "warm_ta", 0.8)}
    compositions = providers.media.compositions
    assert compositions["en-episode.mp4"].subtitle_style.burn_in
    assert not compositions["ta-short.mp4"].subtitle_style.burn_in
    titles = {
        item.language: item.meta["title"]
        for item in meta_of(rig, "upload_metadata")
        if item.variant == "episode"
    }
    assert titles == {"en": "EN Kutty and the Golden Mango", "ta": "TA குட்டியும் தங்க மாம்பழமும்"}
    assert {request.intensity for request in providers.motion.requests} >= {0.2}


def test_character_voice_override_reaches_speech(tmp_path: Path) -> None:
    cast = [member.model_dump() for member in quick_settings().cast]
    cast[1]["voice_override"] = {"en": "parrot_voice", "ta": ""}
    settings = KidsStorySettings.model_validate({**quick_settings().model_dump(), "cast": cast})
    rig = StageRig(tmp_path, settings=settings, languages=("en",))
    rig.run(StoryStage())
    story_path = tmp_path / meta_of(rig, "story")[0].filename
    story_path.write_text(
        story_path.read_text().replace('"speaker": "narrator"', '"speaker": "mittu"', 1)
    )
    rig.run(VoiceStage())
    assert rig.providers.speech.requests[1].voice == "parrot_voice"


def test_later_stages_resume_from_artifacts_only(tmp_path: Path) -> None:
    first = run_chain(StageRig(tmp_path), "assemble")
    resumed = StageRig(tmp_path, artifacts=list(first.artifacts), providers=FakeProviders())
    outcome = resumed.run(STAGES[-1])
    assert len(outcome.artifacts) == 12
    with pytest.raises(MissingArtifactError):
        StageRig(tmp_path / "empty").run(VoiceStage())


def test_cards_and_thumbnails_are_lettered_when_a_font_exists(tmp_path: Path) -> None:
    rig = run_chain(StageRig(tmp_path, languages=("en",)))
    cards = [item for item in meta_of(rig, "visual") if "card" in item.meta]
    assert {item.meta["card"] for item in cards} == {"intro", "outro"}
    thumbnails = meta_of(rig, "thumbnail")
    assert all((tmp_path / item.filename).stat().st_size > 0 for item in thumbnails)
    no_fonts = quick_settings(thumbnail={"font_files": {"en": [], "ta": []}})
    plain = run_chain(StageRig(tmp_path / "plain", settings=no_fonts, languages=("en",)))
    assert {item.meta["title_drawn"] for item in meta_of(plain, "thumbnail")} == {False}

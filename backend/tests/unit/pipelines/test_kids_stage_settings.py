from __future__ import annotations

from pathlib import Path

import pytest

from autotube.pipelines.kids_story.settings.root import KidsStorySettings
from autotube.pipelines.kids_story.stages.music import effect_cues
from autotube.pipelines.kids_story.stages.story import StoryStage
from autotube.pipelines.kids_story.stages.voice import VoiceStage
from tests.fixtures.kids_data import (
    StageRig,
    meta_of,
    quick_settings,
    run_chain,
    smart_writer,
    story,
)
from tests.fixtures.kids_fakes import FakeProviders


def test_settings_reach_requests_compositions_and_metadata(tmp_path: Path) -> None:
    settings = quick_settings(
        voice={"narrator_voice": {"en": "warm_en", "ta": "warm_ta"}, "speed": 0.8},
        subtitles={"burn_in_episode": True, "burn_in_short": False},
        metadata={"title_template": {"en": "EN {title}", "ta": "TA {title}"}},
        story={"theme_mode": "fixed", "fixed_theme": "sharing"},
        episode={"fps": 24},
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
    assert {made.fps for made in compositions.values()} == {24}
    assert {request.fps for request in providers.motion.requests} == {24}
    titles = {
        item.language: item.meta["title"]
        for item in meta_of(rig, "upload_metadata")
        if item.variant == "episode"
    }
    assert titles == {"en": "EN Kavin and the Golden Mango", "ta": "TA கவினும் தங்க மாம்பழமும்"}


def speaker_rig(root: Path, override: dict[str, str], languages: tuple[str, ...]) -> StageRig:
    cast = [member.model_dump() for member in quick_settings().cast]
    cast[1]["voice_override"] = override
    base = quick_settings(voice={"narrator_voice": {"en": "narrator_en", "ta": "narrator_ta"}})
    settings = KidsStorySettings.model_validate({**base.model_dump(), "cast": cast})
    rig = StageRig(root, settings=settings, languages=languages)
    rig.run(StoryStage())
    for item in meta_of(rig, "story"):
        path = root / item.filename
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace('"speaker": "narrator"', '"speaker": "mittu"', 1))
    rig.run(VoiceStage())
    return rig


def test_character_voice_override_reaches_speech(tmp_path: Path) -> None:
    rig = speaker_rig(tmp_path, {"en": "parrot_voice", "ta": ""}, ("en", "ta"))
    by_language: dict[str, list[str]] = {}
    for request in rig.providers.speech.requests:
        by_language.setdefault(request.language, []).append(request.voice)
    assert by_language["en"][1] == "parrot_voice"
    assert by_language["ta"][1] == "narrator_ta"


def test_an_unknown_speaker_uses_the_narrator_voice(tmp_path: Path) -> None:
    rig = StageRig(tmp_path, languages=("en",))
    rig.run(StoryStage())
    path = tmp_path / meta_of(rig, "story")[0].filename
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace('"speaker": "narrator"', '"speaker": "dragon"', 1))
    rig.run(VoiceStage())
    assert {request.voice for request in rig.providers.speech.requests} == {""}


def motion_rig(root: Path) -> StageRig:
    settings = quick_settings(
        visuals={"motion_intensity": 0.2, "hero_motion_intensity": 0.9, "card_camera": "rise"},
        look={"use_style_motion": False},
    )
    providers = FakeProviders(writer=smart_writer())
    return run_chain(StageRig(root, settings=settings, providers=providers), "motion")


def test_motion_requests_follow_scene_kind_and_variant(tmp_path: Path) -> None:
    rig = motion_rig(tmp_path)
    clips = meta_of(rig, "clip")
    requests = rig.providers.motion.requests
    pairs = {
        str(clip.meta["visual_key"]): request for clip, request in zip(clips, requests, strict=True)
    }
    assert pairs["scene-0@episode"].intensity == 0.9
    assert pairs["scene-1@episode"].intensity == 0.2
    assert pairs["scene-6@short"].intensity == 0.9
    assert (pairs["scene-0@short"].width, pairs["scene-0@short"].height) == (720, 1280)
    assert (pairs["scene-1@episode"].width, pairs["scene-1@episode"].height) == (1280, 720)
    assert pairs["card-intro-en@episode"].camera.value == "rise"
    assert pairs["card-outro-ta@episode"].camera.value == "rise"
    assert pairs["scene-1@episode"].camera.value == "pan_right"


@pytest.mark.parametrize(
    ("music_on", "effects_on"), [(True, True), (True, False), (False, True), (False, False)]
)
def test_music_and_effects_switch_independently(
    tmp_path: Path, music_on: bool, effects_on: bool
) -> None:
    settings = quick_settings(
        music={"enabled": music_on}, sound_effects={"enabled": effects_on, "volume": 1.4}
    )
    providers = FakeProviders()
    rig = run_chain(StageRig(tmp_path, settings=settings, providers=providers))
    assert bool(meta_of(rig, "music")) is music_on
    assert bool(meta_of(rig, "sound_effect")) is effects_on
    for made in providers.media.compositions.values():
        assert (made.music is not None) is music_on
        assert bool(made.sound_effects) is effects_on
        assert all(clip.volume == 1.4 for clip in made.sound_effects)


def test_music_and_effects_follow_their_prompts(tmp_path: Path) -> None:
    settings = quick_settings(
        music={"mood_prompt": "soft harp"},
        sound_effects={"prompt_template": "tiny {cue} {unknown}", "offset_seconds": 1.1},
    )
    providers = FakeProviders(writer=smart_writer())
    run_chain(StageRig(tmp_path, settings=settings, providers=providers))
    assert providers.music is not None
    prompts = [request.prompt for request in providers.music.requests]
    assert prompts.count("soft harp") == 4
    assert "tiny birds chirping {unknown}" in prompts
    episode = providers.media.compositions["en-episode.mp4"]
    first_scene = episode.visuals[1]
    assert episode.sound_effects[0].start_seconds == pytest.approx(first_scene.start_seconds + 1.1)


def test_missing_music_provider_logs_and_adds_nothing(tmp_path: Path) -> None:
    missing = run_chain(StageRig(tmp_path, providers=FakeProviders(music=None)))
    assert meta_of(missing, "music") == []
    assert any("no music provider" in line for line in missing.book.warnings())


def test_effect_cues_are_unique_and_never_empty() -> None:
    scenes = [
        scene.model_copy(update={"sound_effects": cues})
        for scene, cues in zip(
            story().scenes[:3], [["pop", ""], ["pop", "splash"], ["splash"]], strict=True
        )
    ]
    assert effect_cues({"en": story().model_copy(update={"scenes": scenes})}) == ["pop", "splash"]

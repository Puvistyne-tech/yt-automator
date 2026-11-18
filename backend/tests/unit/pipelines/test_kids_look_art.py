from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops

from autotube.domain.capabilities import TextRequest
from autotube.pipelines.kids_story.art.cards import card_lettering, card_lines, thumbnail_lines
from autotube.pipelines.kids_story.art.lettering import lettered
from autotube.pipelines.kids_story.settings.base import Placement
from tests.fixtures.kids_data import (
    StageRig,
    is_judge,
    is_translation,
    meta_of,
    quick_settings,
    run_chain,
    smart_writer,
    story,
    story_answer,
    tamil_answer,
    with_font,
)
from tests.fixtures.kids_fakes import FakeProviders, FakeWriter


def test_default_card_and_thumbnail_text_match_todays_pictures() -> None:
    settings, draft = quick_settings(), story()
    series, refrain = settings.series.name.en, settings.series.refrain.en
    assert card_lines(settings, draft, "intro") == [series, draft.title]
    assert card_lines(settings, draft, "outro") == [refrain, series]
    assert thumbnail_lines(settings, draft) == [draft.title]


def test_card_and_thumbnail_templates_fill_in_the_story() -> None:
    settings = quick_settings(
        episode={"intro_card_text": {"en": "{title}\n{moral}"}, "outro_card_text": {"en": ""}},
        thumbnail={"text_template": {"en": "{series}: {title}\n{hook}"}},
    )
    draft = story()
    assert card_lines(settings, draft, "intro") == [draft.title, draft.moral]
    assert card_lines(settings, draft, "outro") == []
    assert thumbnail_lines(settings, draft) == [
        f"{settings.series.name.en}: {draft.title}",
        draft.hook_line,
    ]


def test_a_thumbnail_without_text_draws_no_lines() -> None:
    assert thumbnail_lines(quick_settings(thumbnail={"title_text": False}), story()) == []


def test_the_card_text_position_moves_the_letters(tmp_path: Path, font_file: Path) -> None:
    source = tmp_path / "card.png"
    Image.new("RGB", (320, 180), (40, 120, 180)).save(source)
    drawn: list[Image.Image] = []
    for position in ("center", "top_left"):
        settings = with_font(font_file, episode={"card_text_position": position})
        lettering = card_lettering(settings, story(), "intro")
        assert lettering.placement is Placement(position)
        output = tmp_path / f"{position}.png"
        assert lettered(source, output, lettering)
        drawn.append(Image.open(output).convert("RGB"))
    assert ImageChops.difference(drawn[0], drawn[1]).getbbox() is not None


def thumbnail_run(
    root: Path, candidates: int, judge: bool = True, writer: FakeWriter | None = None
) -> StageRig:
    settings = quick_settings(
        thumbnail={"candidates": candidates},
        visuals={"use_vision_judge": judge, "hero_candidates": 1},
    )
    providers = FakeProviders(writer=writer or smart_writer("2"))
    return run_chain(StageRig(root, settings=settings, providers=providers), "art")


def judge_offline(request: TextRequest) -> str:
    if is_judge(request):
        raise RuntimeError("vision offline")
    return tamil_answer() if is_translation(request) else story_answer()


def thumbnail_art(rig: StageRig) -> dict[str | None, Path]:
    return {item.variant: Path(item.filename) for item in meta_of(rig, "thumbnail_art")}


def test_several_thumbnails_are_drawn_and_the_judge_picks_one(tmp_path: Path) -> None:
    rig = thumbnail_run(tmp_path, 3)
    wide = [r for r in rig.providers.images.requests if (r.width, r.height) == (640, 360)]
    assert len({request.seed for request in wide}) == 3
    assert thumbnail_art(rig)["episode"].name == "thumbnail-wide-c1.png"
    assert "thumbnail: kept picture 2 of 3" in rig.logs
    writer = rig.providers.writer
    assert writer is not None
    judged = [request for request in writer.requests if is_judge(request)]
    assert any(len(request.images) == 3 for request in judged)


def test_one_thumbnail_keeps_todays_file_and_asks_no_judge(tmp_path: Path) -> None:
    rig = thumbnail_run(tmp_path, 1)
    assert thumbnail_art(rig)["episode"].name == "thumbnail-wide.png"
    assert not any("thumbnail:" in line for line in rig.logs)


def test_without_a_judge_the_first_thumbnail_is_kept(tmp_path: Path) -> None:
    rig = thumbnail_run(tmp_path, 2, judge=False)
    assert thumbnail_art(rig)["episode"].name == "thumbnail-wide.png"
    assert "thumbnail: kept picture 1 of 2" in rig.logs


def test_a_failing_thumbnail_judge_keeps_the_first_picture(tmp_path: Path) -> None:
    rig = thumbnail_run(tmp_path, 3, writer=FakeWriter(judge_offline))
    assert thumbnail_art(rig)["episode"].name == "thumbnail-wide.png"
    assert any("picture judge failed" in line for line in rig.book.warnings())
    assert "thumbnail: kept picture 1 of 3" in rig.logs


def test_the_short_can_animate_at_its_own_frame_rate(tmp_path: Path) -> None:
    providers = FakeProviders(writer=smart_writer())
    rig = StageRig(tmp_path, settings=quick_settings(short={"fps": 24}), providers=providers)
    run_chain(rig, "motion")
    rates = {(r.width, r.height): r.fps for r in rig.providers.motion.requests}
    assert rates == {(1280, 720): 30, (720, 1280): 24}

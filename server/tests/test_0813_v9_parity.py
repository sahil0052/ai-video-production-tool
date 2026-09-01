from pathlib import Path
from types import SimpleNamespace
from typing import get_args

import cv2
import numpy as np

from app.editor.training_caption_planner import (
    PlannedCaptionPage,
    PlannedCaptionToken,
)
from app.models import CaptionPage, CaptionToken
from app.production_models import StoryProfile
from build_0813_backtest_v8 import build_blueprint as backtest_blueprint
from build_0813_lotsize_v8 import build_blueprint as lot_size_blueprint
from build_0813_ppi_v8 import build_blueprint as ppi_blueprint
import build_0813_v8_pipeline as pipeline
from build_0813_v8_pipeline import MUSIC
from ffmpeg_plan_renderer import build_ass_script


def _contains_presenter(shot) -> bool:
    return shot.source_role == "presenter" or bool(
        shot.metadata.get("contains_presenter")
    )


def _maximum_presenter_gap_ms(blueprint) -> int:
    presenter_ranges = [
        (shot.start_ms, shot.end_ms)
        for shot in blueprint.shots
        if _contains_presenter(shot)
    ]
    boundaries = [(0, 0), *presenter_ranges, (blueprint.duration_ms,) * 2]
    return max(
        right[0] - left[1]
        for left, right in zip(boundaries, boundaries[1:])
    )


def _role_ratio(blueprint, source_role: str) -> float:
    duration = sum(
        shot.end_ms - shot.start_ms
        for shot in blueprint.shots
        if shot.source_role == source_role
    )
    return duration / blueprint.duration_ms


def test_every_story_opens_with_a_presenter_anchor() -> None:
    for blueprint in (
        ppi_blueprint(),
        backtest_blueprint(),
        lot_size_blueprint(),
    ):
        assert _contains_presenter(blueprint.shots[0]), blueprint.story_id


def test_presenter_returns_before_the_edit_feels_characterless() -> None:
    for blueprint in (
        ppi_blueprint(),
        backtest_blueprint(),
        lot_size_blueprint(),
    ):
        assert _maximum_presenter_gap_ms(blueprint) <= 11_000, (
            blueprint.story_id
        )


def test_flat_graphics_are_a_supporting_role_not_the_visual_foundation() -> None:
    for blueprint in (
        ppi_blueprint(),
        backtest_blueprint(),
        lot_size_blueprint(),
    ):
        assert _role_ratio(blueprint, "deterministic-graphic") <= 0.20, (
            blueprint.story_id
        )


def test_music_map_does_not_select_the_known_low_scoring_tracks() -> None:
    assert MUSIC["backtest"]["path"].name != "feedback-dreams-588.mp3"
    assert MUSIC["lot-size"]["path"].name != "relax-beat-292.mp3"
    assert MUSIC["ppi"]["gain_db"] <= -30.0


def test_ffmpeg_caption_fallback_uses_the_measured_reference_font() -> None:
    script = build_ass_script(
        {
            "caption_pages": [],
            "kinetic_text_cues": [],
            "visual_layers": [],
        }
    )

    assert "Share Tech Mono" in script


def test_production_schema_accepts_all_v9_story_profiles() -> None:
    supported = set(get_args(StoryProfile))

    assert {
        "ppi-training-v9",
        "backtest-training-v9",
        "lot-size-training-v9",
    } <= supported


def _write_test_video(path: Path, color: tuple[int, int, int]) -> None:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        30,
        (320, 480),
    )
    assert writer.isOpened()
    frame = np.full((480, 320, 3), color, dtype=np.uint8)
    for _ in range(45):
        writer.write(frame)
    writer.release()


def test_presenter_split_renderer_builds_a_real_horizontal_composite(
    tmp_path: Path,
) -> None:
    renderer = getattr(pipeline, "_render_presenter_split", None)
    assert callable(renderer)
    top = tmp_path / "top.mp4"
    presenter = tmp_path / "presenter.mp4"
    output = tmp_path / "composite.mp4"
    _write_test_video(top, (20, 40, 220))
    _write_test_video(presenter, (30, 210, 40))

    renderer(
        top=top,
        presenter=presenter,
        output=output,
        duration_ms=1_000,
        top_source_start_ms=0,
        presenter_source_start_ms=0,
    )

    capture = cv2.VideoCapture(str(output))
    ok, frame = capture.read()
    capture.release()
    assert ok
    assert frame.shape[:2] == (1920, 1080)
    assert np.mean(frame[:900], axis=(0, 1)).tolist() != np.mean(
        frame[1100:],
        axis=(0, 1),
    ).tolist()


def test_reference_storyboards_restore_dark_bright_visual_rhythm() -> None:
    ppi = ppi_blueprint()
    backtest = backtest_blueprint()
    lot_size = lot_size_blueprint()

    assert ppi.shots[20].metadata["contains_presenter"] is True
    assert ppi.shots[22].asset_id == "pexels-32953312"
    assert ppi.shots[24].asset_id == "graphic-zero-balance"
    assert backtest.shots[5].asset_id == "graphic-backtest-practice"
    assert backtest.shots[6].asset_id == "mt5-strategy-tester"
    assert backtest.shots[12].asset_id == "graphic-delay-slippage"
    assert backtest.shots[14].asset_id == "graphic-overfit-unseen-bright"
    assert backtest.shots[3].metadata["dark_context"] is True
    assert backtest.shots[8].asset_id == "graphic-perfect-prices"
    assert backtest.shots[11].metadata["product_grade"] == "balanced"
    assert lot_size.shots[3].asset_id == "graphic-unit-price"
    assert lot_size.shots[4].asset_id == "graphic-different-total"
    assert lot_size.shots[20].asset_id == "graphic-entry-lot-risk"
    assert lot_size.shots[8].metadata["contains_presenter"] is True
    assert all(
        shot.metadata.get("product_grade") == "balanced"
        for shot in lot_size.shots
        if shot.source_role == "real-product"
    )


def test_real_product_grade_preserves_dark_reference_contrast() -> None:
    dark = pipeline.visual_effects_for_shot(
        SimpleNamespace(
            source_role="real-product",
            metadata={"dark_ui": True},
        )
    )
    regular = pipeline.visual_effects_for_shot(
        SimpleNamespace(source_role="real-product", metadata={})
    )

    assert dark["brightness"] <= 0.8
    assert dark["contrast"] >= 1.1
    assert regular["brightness"] <= 0.92


def test_hook_caption_is_removed_and_split_caption_moves_above_face() -> None:
    token = PlannedCaptionToken(
        text="caption",
        start_ms=0,
        end_ms=400,
    )
    pages = [
        PlannedCaptionPage(
            start_ms=0,
            end_ms=500,
            tokens=(token,),
            family="technical-mono",
            anchor="center-74",
            transition="hard-cut",
            max_width=500,
            font_size=33,
            timeline_duration_ms=50_680,
        ),
        PlannedCaptionPage(
            start_ms=17_600,
            end_ms=18_200,
            tokens=(
                PlannedCaptionToken(
                    text="fixed spread",
                    start_ms=17_600,
                    end_ms=18_000,
                ),
            ),
            family="technical-mono",
            anchor="center-74",
            transition="hard-cut",
            max_width=500,
            font_size=33,
            timeline_duration_ms=50_680,
        ),
    ]

    refined = pipeline.refine_captions_for_shots(
        backtest_blueprint(),
        pages,
    )

    assert len(refined) == 1
    assert refined[0].anchor == "upper-46"


def test_upper_split_caption_anchor_is_a_supported_contract() -> None:
    page = CaptionPage(
        start_ms=0,
        end_ms=500,
        tokens=[CaptionToken(text="SAFE", start_ms=0, end_ms=400)],
        family="technical-mono",
        anchor="upper-46",
        transition="hard-cut",
        max_width=500,
    )

    assert page.anchor == "upper-46"


def test_ppi_mix_protects_the_short_word_deepgram_previously_missed() -> None:
    assert "15.45" in pipeline.music_speech_protection_filter("ppi")
    assert pipeline.music_speech_protection_filter("backtest") == ""

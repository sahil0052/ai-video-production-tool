from __future__ import annotations

import importlib

import pytest

from build_0813_v8_common import V8Shot
from build_0813_v8_pipeline import (
    normalized_video_crop,
    transform_keyframes_for_shot,
    visual_effects_for_shot,
)


@pytest.mark.parametrize(
    ("module_name", "story_id", "duration_ms", "cut_range"),
    [
        ("build_0813_ppi_v8", "ppi", 47_830, (31, 36)),
        (
            "build_0813_backtest_v8",
            "backtest",
            50_680,
            (19, 22),
        ),
        (
            "build_0813_lotsize_v8",
            "lot-size",
            50_550,
            (20, 25),
        ),
    ],
)
def test_story_blueprints_are_bespoke_and_contiguous(
    module_name: str,
    story_id: str,
    duration_ms: int,
    cut_range: tuple[int, int],
) -> None:
    module = importlib.import_module(module_name)
    blueprint = module.build_blueprint()

    assert blueprint.story_id == story_id
    assert blueprint.duration_ms == duration_ms
    assert cut_range[0] <= len(blueprint.shots) <= cut_range[1]
    assert blueprint.shots[0].start_ms == 0
    assert blueprint.shots[-1].end_ms == duration_ms
    assert all(
        left.end_ms == right.start_ms
        for left, right in zip(
            blueprint.shots,
            blueprint.shots[1:],
        )
    )
    assert all(shot.primary_subject for shot in blueprint.shots)
    assert all(shot.action for shot in blueprint.shots)
    assert all(
        shot.reference_role.startswith("reference-")
        or shot.reference_role == "profit-bricks-brand"
        for shot in blueprint.shots
    )
    assert all(
        shot.treatment not in {"vertical-split", "persistent-pip"}
        for shot in blueprint.shots
    )
    assert len({shot.treatment_class for shot in blueprint.shots}) >= 6


def test_shot_contract_rejects_free_form_reference_role() -> None:
    with pytest.raises(ValueError, match="reference_role"):
        V8Shot(
            id="bad-shot",
            start_ms=0,
            end_ms=1_000,
            narration_phrase="test",
            source_role="licensed-context",
            reference_role="training references",
            primary_subject="screen",
            action="changes",
            treatment="full-frame",
            treatment_class="tactile-context",
            asset_id="asset",
            caption_family="technical-mono",
        )


def test_no_treatment_repeats_more_than_twice() -> None:
    for module_name in (
        "build_0813_ppi_v8",
        "build_0813_backtest_v8",
        "build_0813_lotsize_v8",
    ):
        shots = importlib.import_module(module_name).build_blueprint().shots
        assert all(
            not (
                first.treatment_class
                == second.treatment_class
                == third.treatment_class
            )
            for first, second, third in zip(
                shots,
                shots[1:],
                shots[2:],
            )
        )


def test_presenter_share_matches_reference_profiles() -> None:
    for module_name in (
        "build_0813_ppi_v8",
        "build_0813_backtest_v8",
        "build_0813_lotsize_v8",
    ):
        blueprint = importlib.import_module(module_name).build_blueprint()
        presenter_ms = sum(
            shot.end_ms - shot.start_ms
            for shot in blueprint.shots
            if shot.source_role == "presenter"
        )
        ratio = presenter_ms / blueprint.duration_ms
        assert 0.14 <= ratio <= 0.20


def test_story_references_are_locked() -> None:
    ppi = importlib.import_module("build_0813_ppi_v8").build_blueprint()
    backtest = importlib.import_module(
        "build_0813_backtest_v8"
    ).build_blueprint()
    lot_size = importlib.import_module(
        "build_0813_lotsize_v8"
    ).build_blueprint()

    assert (ppi.primary_reference, ppi.secondary_reference) == (13, 10)
    assert (backtest.primary_reference, backtest.secondary_reference) == (
        10,
        4,
    )
    assert (lot_size.primary_reference, lot_size.secondary_reference) == (
        10,
        5,
    )


def test_compiled_motion_uses_each_bespoke_shot_zoom() -> None:
    blueprint = importlib.import_module(
        "build_0813_ppi_v8"
    ).build_blueprint()
    shot = blueprint.shots[0]

    keyframes = transform_keyframes_for_shot(
        shot,
        duration_ms=shot.end_ms - shot.start_ms,
    )

    assert keyframes[0]["scale"] == shot.zoom
    assert keyframes[-1]["scale"] > shot.zoom


def test_ppi_hook_uses_literal_ingredient_and_cup_footage() -> None:
    ppi = importlib.import_module("build_0813_ppi_v8").build_blueprint()

    assert [shot.asset_id for shot in ppi.shots[:3]] == [
        "pexels-27093700",
        "pexels-29817236",
        "pexels-13850344",
    ]


def test_ppi_forecast_sequence_uses_distinct_source_crops() -> None:
    ppi = importlib.import_module("build_0813_ppi_v8").build_blueprint()
    evidence_crops = [
        shot.metadata.get("evidence_crop")
        for shot in ppi.shots
        if 17_700 <= shot.start_ms < 22_850
    ]

    assert evidence_crops == ["forecast", "forecast-detail", "actual"]


def test_real_product_crop_uses_requested_vertical_focus() -> None:
    crop = normalized_video_crop(
        aspect=16 / 9,
        role="real-product",
        crop_x=0.5,
        crop_y=0.8,
    )

    assert crop["height"] < 0.55
    assert crop["width"] < 0.18
    assert crop["y"] > 0.5


def test_backtest_early_product_macros_keep_native_dark_ui() -> None:
    backtest = importlib.import_module(
        "build_0813_backtest_v8"
    ).build_blueprint()
    early_product = [backtest.shots[index] for index in (2, 7, 8, 10)]
    later_product = backtest.shots[17]

    assert all(
        visual_effects_for_shot(shot)["brightness"] == 1.0
        for shot in early_product
    )
    assert visual_effects_for_shot(later_product)["brightness"] == 1.16


def test_lot_size_repeated_beats_have_distinct_visual_states() -> None:
    lot_size = importlib.import_module(
        "build_0813_lotsize_v8"
    ).build_blueprint()

    assert (
        abs(lot_size.shots[8].crop_x - lot_size.shots[9].crop_x)
        >= 0.2
    )
    assert (
        lot_size.shots[12].asset_id
        == "graphic-relative-impact-large"
    )
    assert (
        abs(lot_size.shots[21].crop_x - lot_size.shots[22].crop_x)
        >= 0.2
    )
    assert visual_effects_for_shot(lot_size.shots[0])["brightness"] == 1.0

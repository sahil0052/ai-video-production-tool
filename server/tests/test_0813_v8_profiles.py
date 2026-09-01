from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.editor.training_reference_profiles import profile_for_story
from app.production_models import VisualLayerSpec
from production_editor import build_parser


def test_ppi_uses_news_evidence_profile() -> None:
    profile = profile_for_story("ppi")

    assert profile.primary_reference == 13
    assert profile.secondary_reference == 10
    assert profile.presenter_ratio == (0.14, 0.20)
    assert profile.hard_cut_count == (31, 36)
    assert profile.median_shot_ms == (1_000, 1_500)
    assert profile.caption_coverage == (0.68, 0.75)


def test_backtest_and_lot_size_do_not_inherit_social_kinetic() -> None:
    backtest = profile_for_story("backtest")
    lot_size = profile_for_story("lot-size")

    assert backtest.primary_reference == 10
    assert backtest.secondary_reference == 4
    assert lot_size.primary_reference == 10
    assert lot_size.secondary_reference == 5
    assert backtest.caption_mode == "technical-reference"
    assert lot_size.caption_mode == "technical-product"
    assert backtest.presenter_ratio[1] <= 0.20
    assert lot_size.presenter_ratio[1] <= 0.20


def test_free_form_story_profile_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown V8 story profile"):
        profile_for_story("training references")


def test_visual_layer_uses_specific_reference_role() -> None:
    layer = VisualLayerSpec(
        id="layer",
        shot_id="shot",
        start_ms=0,
        end_ms=1_000,
        source_role="direct-evidence",
        asset_id="evidence",
        source_start_ms=0,
        source_end_ms=1_000,
        reference_role="reference-13-evidence-excerpt",
    )
    assert layer.reference_role == "reference-13-evidence-excerpt"

    with pytest.raises(ValidationError, match="reference_role"):
        VisualLayerSpec(
            id="bad-layer",
            shot_id="shot",
            start_ms=0,
            end_ms=1_000,
            source_role="direct-evidence",
            asset_id="evidence",
            source_start_ms=0,
            source_end_ms=1_000,
            reference_role="training references",
        )


def test_production_cli_accepts_v8_story_profiles_and_review() -> None:
    parser = build_parser()
    planned = parser.parse_args(
        [
            "plan",
            "source.mp4",
            "output",
            "--story-profile",
            "ppi-training-v8",
            "--voice-policy",
            "natural-1x",
            "--asset-policy",
            "evidence-first-free",
            "--flow-operation-budget",
            "0",
        ]
    )
    reviewed = parser.parse_args(["review", "output"])

    assert planned.story_profile == "ppi-training-v8"
    assert planned.voice_policy == "natural-1x"
    assert reviewed.command == "review"

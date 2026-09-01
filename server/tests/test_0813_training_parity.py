from __future__ import annotations

from pathlib import Path
from statistics import median
from types import SimpleNamespace

import cv2
import numpy as np
import pytest


def _0813_plan() -> SimpleNamespace:
    return SimpleNamespace(
        reference_profile="technical-reference",
        story_profile="cpi-inflation-training",
        source_filename="0813.mp4",
        voice_policy="reference-compressed",
    )


def test_0813_review_profile_matches_primary_training_reference() -> None:
    from app.editor import production_assembly

    thresholds = production_assembly._review_thresholds_for_plan(
        _0813_plan()
    )

    assert thresholds["cut_min"] == 34
    assert thresholds["cut_max"] == 40
    assert thresholds["median_min_ms"] == 900
    assert thresholds["median_max_ms"] == 1400
    assert thresholds["darkness_min"] == 0.38
    assert thresholds["darkness_max"] == 0.56
    assert thresholds["luminance_min"] == 78
    assert thresholds["luminance_max"] == 92
    assert thresholds["saturation_min"] == 64
    assert thresholds["saturation_max"] == 80
    assert thresholds["real_direct_min"] == 0.55
    assert thresholds["cut_audio_alignment_min"] == 80
    assert thresholds["composition_parity"] is True
    assert thresholds["audio_pulse_min"] == 98
    assert thresholds["audio_pulse_max"] == 106


def test_0813_master_normalizes_color_metadata_and_applies_reference_grade() -> None:
    from app.editor import production_assembly

    video_filter = production_assembly._production_video_filter(_0813_plan())

    assert video_filter == (
        "setparams=range=tv:color_primaries=bt709:"
        "color_trc=bt709:colorspace=bt709,"
        "curves=all='0/0.03 0.06/0.10 0.34/0.29 "
        "0.60/0.54 0.89/0.885 1/0.98',"
        "eq=brightness=0.012:saturation=1.32,"
        "unsharp=5:5:0.45:5:5:0"
    )

    command = production_assembly.build_production_master_command(
        executable=Path("ffmpeg.exe"),
        rendered=Path("rendered.mp4"),
        output=Path("edited.mp4"),
        measurement={
            "input_i": -17.0,
            "input_tp": -3.0,
            "input_lra": 2.8,
            "input_thresh": -27.0,
            "target_offset": 0.0,
        },
        duration_seconds=45.55,
        video_filter=video_filter,
    )

    assert command[command.index("-color_primaries") + 1] == "bt709"
    assert command[command.index("-color_trc") + 1] == "bt709"
    assert command[command.index("-colorspace") + 1] == "bt709"


def test_0813_schedule_uses_reference_13_pacing_and_cpi_onset_cut() -> None:
    import build_0813_training_parity as build

    durations = [
        end - start
        for start, end in zip(build.BOUNDARIES[:-1], build.BOUNDARIES[1:])
    ]

    assert len(build.SHOT_ROLES) == 38
    assert len(build.BOUNDARIES) == 39
    assert build.BLS_OVERVIEW_END_MS == 5_570
    assert build.BLS_OVERVIEW_END_MS in build.BOUNDARIES
    assert 6_960 in build.BOUNDARIES
    assert 14_880 in build.BOUNDARIES
    assert 11_220 in build.BOUNDARIES
    assert 13_020 in build.BOUNDARIES
    assert 18_660 in build.BOUNDARIES
    assert 21_990 in build.BOUNDARIES
    assert 27_530 in build.BOUNDARIES
    assert 28_900 in build.BOUNDARIES
    assert 31_400 in build.BOUNDARIES
    assert 34_180 in build.BOUNDARIES
    assert 43_220 in build.BOUNDARIES
    assert 900 <= median(durations) <= 1_400


def test_0813_audio_uses_original_dialogue_and_keeps_sfx_outside_speech() -> None:
    import build_0813_training_parity as build

    base_audio = {
        "dialogue_asset_id": "dialogue-processed",
        "music_gain_automation": [
            {
                "start_ms": 0,
                "end_ms": 45_550,
                "gain_db": -5.0,
                "reason": "old",
            }
        ],
        "speech_protection_windows": [
            {"start_ms": 29_795, "end_ms": 30_015, "word": "hua"},
            {"start_ms": 30_195, "end_ms": 30_415, "word": "lekin"},
        ],
    }

    audio = build.build_audio_spec(base_audio)
    question = next(
        cue for cue in audio["sfx_cues"] if cue["id"] == "question-turn"
    )
    monthly = next(
        cue for cue in audio["sfx_cues"] if cue["id"] == "monthly-proof"
    )
    yearly = next(
        cue for cue in audio["sfx_cues"] if cue["id"] == "yearly-proof"
    )

    assert audio["dialogue_asset_id"] == "dialogue-original"
    assert audio["true_peak_dbtp"] == -1.2
    basket = next(
        cue for cue in audio["sfx_cues"] if cue["id"] == "basket-proof"
    )
    shelter = next(
        cue for cue in audio["sfx_cues"] if cue["id"] == "shelter-proof"
    )

    assert basket["start_ms"] == 9_250
    assert monthly["start_ms"] == 11_090
    assert yearly["start_ms"] == 13_620
    assert shelter["start_ms"] == 25_720
    assert {cue["id"] for cue in audio["sfx_cues"]} == {
        "hook-settle",
        "official-source",
        "basket-proof",
        "monthly-proof",
        "yearly-proof",
        "shelter-proof",
        "question-turn",
        "cta-lift",
    }
    assert basket["asset_id"] == "sfx-snap"
    assert basket["gain_db"] == -8.0
    assert basket["volume"] == 0.35
    assert monthly["asset_id"] == "sfx-proof"
    assert monthly["source_start_ms"] == 340
    assert monthly["gain_db"] == -12.0
    assert monthly["volume"] == 0.25
    assert yearly["asset_id"] == "sfx-proof"
    assert yearly["source_start_ms"] == 260
    assert yearly["gain_db"] == -10.5
    assert yearly["volume"] == 0.3
    assert shelter["asset_id"] == "sfx-snap"
    assert shelter["gain_db"] == -8.0
    assert shelter["volume"] == 0.35
    assert question["start_ms"] == 30_040
    for cue in (
        basket,
        monthly,
        yearly,
        shelter,
        question,
    ):
        assert all(
            not (
                cue["start_ms"] < window["end_ms"]
                and cue["start_ms"] + cue["duration_ms"]
                > window["start_ms"]
            )
            for window in audio["speech_protection_windows"]
        )


def test_0813_caption_positions_avoid_faces_and_evidence_text() -> None:
    import render_0813_training_parity as render

    assert render.caption_y(0) == 1_860
    assert render.caption_y(1_680) == 1_860
    assert render.caption_y(16_427) == 1_790
    assert render.caption_y(18_629) == 1_790
    assert render.caption_y(27_639) == 1_650
    assert render.caption_y(34_121) == 1_650
    assert render.caption_y(34_122) == 1_760
    assert render.caption_y(35_241) == 1_760


def test_0813_night_grade_preserves_shadow_detail() -> None:
    import render_0813_training_parity as render

    assert render.NIGHT_EQ == (
        "brightness=-0.035:contrast=1.08:saturation=0.82"
    )


def test_0813_alternates_static_evidence_holds_with_pushes() -> None:
    import render_0813_training_parity as render

    assert render.reference_image_push(4, 0.018) == 0
    assert render.reference_image_push(10, 0.025) == 0
    assert render.reference_image_push(12, 0.025) == 0
    assert render.reference_image_push(19, 0.025) == 0
    assert render.reference_image_push(23, 0.025) == 0
    assert render.reference_image_push(25, 0.022) == 0
    assert render.reference_image_push(29, 0.020) == 0
    assert render.reference_image_push(37, 0.018) == 0
    assert render.reference_image_push(11, 0.018) == 0.018
    assert render.reference_image_push(24, 0.022) == 0.022


def test_0813_uses_reviewed_real_gasoline_footage() -> None:
    import build_0813_training_parity as build

    assert build.SELECTED_FUEL_WIDE_ID == "25397939"
    assert build.SELECTED_FUEL_ACTION_ID == "16567388"
    assert build.REMOTE_ASSETS[
        "pexels-gas-station-wide-25397939.mp4"
    ].endswith("11900984_1080_1920_24fps.mp4")
    assert build.REMOTE_ASSETS[
        "pexels-gasoline-action-16567388.mp4"
    ].endswith("16567388-hd_1080_1920_30fps.mp4")

    layers = build.build_layers()
    by_shot = {
        layer["shot_id"]: layer
        for layer in layers
        if layer["id"].startswith("base-shot-")
    }
    assert by_shot["shot-17"]["asset_id"] == "licensed-gas-station-wide"
    assert by_shot["shot-18"]["asset_id"] == "licensed-gasoline-action"
    assert next(
        layer for layer in layers if layer["id"] == "grid-petrol"
    )["asset_id"] == "licensed-gas-station-wide"


def _bright_uniform_ratio(path: Path) -> float:
    frame = cv2.imread(str(path))
    assert frame is not None
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    ratios: list[float] = []
    for y in range(0, gray.shape[0], 120):
        for x in range(0, gray.shape[1], 120):
            tile = gray[y : y + 120, x : x + 120]
            if tile.size == 0:
                continue
            ratios.append(
                float(np.mean(tile) >= 210 and np.std(tile) <= 14)
            )
    return float(np.mean(ratios))


def test_0813_evidence_cards_fill_the_frame_with_source_pixels() -> None:
    import build_0813_training_parity as build

    evidence = build.build_evidence_graphics()

    assert _bright_uniform_ratio(evidence["bls-monthly"]) <= 0.35
    assert _bright_uniform_ratio(evidence["bls-yearly"]) <= 0.35
    assert _bright_uniform_ratio(evidence["bls-shelter"]) <= 0.35


def test_0813_news_composition_gate_matches_reference_13() -> None:
    from app.editor.production_audit import (
        evaluate_news_reference_composition,
    )

    passing = evaluate_news_reference_composition(
        {
            "edge_density_mean": 0.082,
            "near_static_pair_ratio": 0.155,
            "low_motion_pair_ratio": 0.289,
            "bright_uniform_blank_p90": 0.29,
            "dark_uniform_blank_mean": 0.243,
            "occupied_local_detail_mean": 0.559,
        }
    )
    failing = evaluate_news_reference_composition(
        {
            "edge_density_mean": 0.086,
            "near_static_pair_ratio": 0.051,
            "low_motion_pair_ratio": 0.112,
            "bright_uniform_blank_p90": 0.545,
            "dark_uniform_blank_mean": 0.295,
            "occupied_local_detail_mean": 0.541,
        }
    )

    assert passing["automated_pass"] is True
    assert failing["automated_pass"] is False
    failed = {
        check["name"]
        for check in failing["checks"]
        if not check["passed"]
    }
    assert failed == {
        "intentional-static-holds",
        "low-motion-discipline",
        "bright-blank-space",
    }


def test_0813_music_is_time_calibrated_to_reference_pulse() -> None:
    import build_0813_training_parity as build

    assert build.MUSIC_ATEMPO == 1.04
    assert (
        f"atempo={build.MUSIC_ATEMPO:.2f}"
        in build.music_filter_chain()
    )


def test_0813_pulse_measurement_rejects_sparse_sfx_transients() -> None:
    from app.editor.production_assembly import (
        _clip_sparse_transients_for_pulse,
    )

    samples = np.ones(10_000, dtype=np.float64)
    samples[-20:] = 100
    clipped = _clip_sparse_transients_for_pulse(samples)

    assert float(np.max(clipped)) < 100
    assert float(np.max(np.abs(clipped))) == pytest.approx(1.0)


def test_0813_pulse_uses_rendered_pre_master_mix_when_available(
    tmp_path: Path,
) -> None:
    from app.editor.production_assembly import (
        _rendered_bed_pulse_source,
    )

    edited = tmp_path / "edited.mp4"
    edited.touch()
    assert _rendered_bed_pulse_source(edited) == edited

    mix = tmp_path / "audio-mix.wav"
    mix.touch()
    assert _rendered_bed_pulse_source(edited) == mix


def test_reference_cut_alignment_uses_reference_db_onset_detector() -> None:
    from app.editor.qc import _measure_reference_cut_onsets

    samples = np.full(3_000, 0.001, dtype=np.float32)
    samples[1_000:1_020] = 1
    samples[2_000:2_020] = 1

    assert _measure_reference_cut_onsets(
        samples,
        sample_rate=1_000,
        event_times_ms=[1_000, 2_000, 2_500],
    ) == pytest.approx(66.666666, abs=0.01)


def test_0813_mastering_uses_linear_gain_to_preserve_mix_dynamics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from app.editor import production_assembly

    captured: dict[str, object] = {}

    monkeypatch.setattr(
        production_assembly,
        "render_production_audio_mix",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        production_assembly,
        "measure_loudness_for_master",
        lambda *_args, **_kwargs: SimpleNamespace(
            input_i=-17.0,
            input_tp=-3.0,
            input_lra=3.5,
            input_thresh=-27.0,
            target_offset=0.0,
        ),
    )

    def capture_command(**kwargs: object) -> list[str]:
        captured.update(kwargs)
        return ["ffmpeg.exe"]

    monkeypatch.setattr(
        production_assembly,
        "build_production_master_command",
        capture_command,
    )
    monkeypatch.setattr(
        production_assembly,
        "_run_command",
        lambda *_args, **_kwargs: None,
    )

    production_assembly.master_production_render(
        plan=_0813_plan(),
        rendered=tmp_path / "rendered.mp4",
        output=tmp_path / "edited.mp4",
        duration_seconds=45.55,
        target_lufs=-14.2,
        target_true_peak=-1.0,
        target_lra=2.6,
    )

    audio_filter = str(captured["audio_filter"])
    assert audio_filter.startswith("volume=")
    assert "alimiter=" in audio_filter
    assert "loudnorm=" not in audio_filter


def test_caption_tokens_inherit_source_word_boundaries() -> None:
    import build_0813_training_parity as build

    source_words = [
        {"start": 0.10, "end": 0.22},
        {"start": 0.30, "end": 0.55},
        {"start": 0.80, "end": 1.10},
        {"start": 1.25, "end": 1.60},
    ]

    tokens = build.source_aligned_tokens(
        source_words=source_words,
        display_words=["PETROL", "KHARCHA", "KAM"],
    )

    assert tokens[0]["start_ms"] == 100
    assert tokens[-1]["end_ms"] == 1_600
    assert [token["end_ms"] - token["start_ms"] for token in tokens] != [
        500,
        500,
        500,
    ]


def test_0813_caption_groups_never_reuse_a_source_word() -> None:
    import build_0813_training_parity as build

    for left, right in zip(
        build.CAPTION_GROUPS,
        build.CAPTION_GROUPS[1:],
    ):
        assert left[1] < right[0]


from __future__ import annotations

import json
from pathlib import Path
from statistics import median

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
TRANSCRIPT = (
    ROOT
    / "storage"
    / "deliverables"
    / "0813-production-v3-live-footage"
    / "analysis"
    / "transcript-deepgram.json"
)


def test_ppi_rebuild_is_isolated_and_uses_the_new_take() -> None:
    import build_0813_ppi_live as build

    assert build.SOURCE == Path(r"D:\Downloads\0813 (1).mp4")
    assert build.OUTPUT.name == "0813-production-v7-semantic-visuals"
    assert build.DURATION_MS == 46_000


def test_storyboard_uses_live_video_at_reference_news_pacing() -> None:
    import build_0813_ppi_live as build

    durations = [
        end - start
        for start, end in zip(
            build.BOUNDARIES[:-1],
            build.BOUNDARIES[1:],
            strict=True,
        )
    ]

    assert 14 <= len(build.SHOT_SPECS) <= 17
    assert len(build.BOUNDARIES) == len(build.SHOT_SPECS) + 1
    assert build.BOUNDARIES[0] == 0
    assert build.BOUNDARIES[-1] == build.DURATION_MS
    assert 2_300 <= median(durations) <= 3_200
    assert all(700 <= duration <= 5_900 for duration in durations)
    assert all(shot["kind"] == "video" for shot in build.SHOT_SPECS)
    assert all(shot["visual_job"] for shot in build.SHOT_SPECS)


def test_ppi_uses_presenter_for_interpretation_not_generic_factory_broll() -> None:
    import build_0813_ppi_live as build

    by_role = {
        shot["editorial_role"]: shot
        for shot in build.SHOT_SPECS
    }

    assert by_role["zero-not-uniform"]["asset_id"] == "presenter-edl"
    assert by_role["opposite-directions"]["asset_id"] == "presenter-edl"
    assert by_role["robot-market-lesson"]["asset_id"] == "presenter-edl"
    assert len(
        [
            shot
            for shot in build.SHOT_SPECS
            if shot["asset_id"] == "pexels-7222345"
        ]
    ) <= 1


def test_semantic_visual_report_rejects_repetition_and_long_presenter_gaps() -> None:
    import review_0813_ppi_live as review

    report = review.semantic_visual_report(
        [
            {
                "id": "shot-01",
                "start_ms": 0,
                "end_ms": 2_000,
                "asset_id": "presenter-edl",
                "visual_job": "presenter-explanation",
            },
            {
                "id": "shot-02",
                "start_ms": 2_000,
                "end_ms": 4_500,
                "asset_id": "stock-a",
                "visual_job": "literal-action",
            },
            {
                "id": "shot-03",
                "start_ms": 4_500,
                "end_ms": 7_000,
                "asset_id": "stock-a",
                "visual_job": "literal-action",
            },
        ],
        duration_ms=7_000,
    )

    assert report["passed"] is False
    assert report["repeated_non_presenter_assets"] == ["stock-a"]
    assert report["longest_presenter_free_run_ms"] == 5_000


def test_exact_fact_overlays_are_small_and_evidence_backed() -> None:
    import build_0813_ppi_live as build

    exact = {
        "FORECAST +0.2%",
        "ACTUAL 0.0%",
        "GOODS -0.7%",
        "SERVICES +0.2%",
    }
    overlays = build.fact_overlay_specs()

    assert overlays
    assert all(item["transparent"] for item in overlays)
    assert all(
        item["width"] * item["height"] <= 1080 * 1920 * 0.28
        for item in overlays
    )
    for item in overlays:
        if item["text"] in exact:
            assert item["evidence_id"]


def test_caption_pages_are_word_aligned_and_reference_sized() -> None:
    import build_0813_ppi_live as build
    from caption_transliteration_0813 import romanize_word

    transcript = json.loads(TRANSCRIPT.read_text(encoding="utf-8"))
    pages = build.build_caption_pages(
        transcript,
        build.dialogue_edl(),
    )

    assert len(pages) >= 40
    assert all(350 <= page["end_ms"] - page["start_ms"] <= 1_300 for page in pages)
    assert all(len(page["text"].split()) <= 4 for page in pages)
    assert all(page["family"] == "modern-outline" for page in pages)
    assert all(page["font_size"] in range(52, 61) for page in pages)
    assert all(page["max_width"] <= 900 for page in pages)
    assert all(
        left["end_ms"] <= right["start_ms"]
        for left, right in zip(pages, pages[1:])
    )
    covered_indices: list[int] = []
    for page in pages:
        start = int(page["source_word_start"])
        end = int(page["source_word_end"])
        expected = [
            romanize_word(str(transcript["words"][index]["word"])).upper()
            for index in range(start, end + 1)
        ]
        assert str(page["text"]).split() == expected
        covered_indices.extend(range(start, end + 1))
    assert covered_indices == list(range(len(transcript["words"])))


def test_caption_accuracy_gate_rejects_paraphrases() -> None:
    import review_0813_ppi_live as review

    transcript = json.loads(TRANSCRIPT.read_text(encoding="utf-8"))
    exact_page = {
        "id": "caption-001",
        "source_word_start": 0,
        "source_word_end": 0,
        "text": "SOCHIYE,",
    }
    paraphrased_page = {
        **exact_page,
        "text": "THINK ABOUT IT",
    }

    assert review.caption_accuracy_report(
        transcript,
        [exact_page],
        expected_word_count=1,
    )["passed"] is True
    failed = review.caption_accuracy_report(
        transcript,
        [paraphrased_page],
        expected_word_count=1,
    )
    assert failed["passed"] is False
    assert failed["text_mismatches"]


def test_audio_cues_never_overlap_protected_word_onsets() -> None:
    import build_0813_ppi_live as build

    transcript = json.loads(TRANSCRIPT.read_text(encoding="utf-8"))
    audio = build.build_audio_plan(
        transcript,
        build.dialogue_edl(),
    )

    assert 7 <= len(audio["sfx_cues"]) <= 10
    assert audio["music_base_gain_db"] <= -25
    assert audio["music_duck_db"] >= 5
    for cue in audio["sfx_cues"]:
        assert all(
            not (
                cue["start_ms"] < window["end_ms"]
                and cue["start_ms"] + cue["duration_ms"] > window["start_ms"]
            )
            for window in audio["speech_protection_windows"]
        )


def test_evidence_covers_every_visible_number() -> None:
    import build_0813_ppi_live as build

    evidence = {item["id"]: item for item in build.evidence_items()}

    assert evidence["bls-july-2026-ppi"]["status"] == "verified"
    assert "unchanged" in evidence["bls-july-2026-ppi"]["visible_excerpt"].lower()
    assert "-0.7" in evidence["bls-july-2026-ppi"]["visible_excerpt"]
    assert "+0.2" in evidence["bls-july-2026-ppi"]["visible_excerpt"]
    assert evidence["forecast-july-2026-ppi"]["status"] == "verified"
    assert "+0.2" in evidence["forecast-july-2026-ppi"]["visible_excerpt"]
    assert evidence["dollar-reaction-july-2026-ppi"]["status"] == "verified"


def test_dialogue_edl_is_contiguous_and_preserves_all_speech() -> None:
    import build_0813_ppi_live as build

    edl = build.dialogue_edl()

    assert len(edl) == 22
    assert edl[0].output_start_ms == 0
    assert edl[-1].output_end_ms == build.DURATION_MS
    assert all(
        left.output_end_ms == right.output_start_ms
        for left, right in zip(edl, edl[1:])
    )
    assert all(segment.playback_rate == 1 for segment in edl)


def test_renderer_uses_face_safe_captions_without_vertical_splits() -> None:
    import render_0813_ppi_live as render

    render.load_build_module("build_0813_ppi_live")
    assert render.caption_anchor_y(0) == 1_810
    assert render.caption_anchor_y(2_500) == 1_545
    assert render.caption_anchor_y(44_900) == 1_520
    assert render.secondary_layout_for_shot(1, has_secondary=True) == (
        "presenter-bottom"
    )
    assert render.secondary_layout_for_shot(13, has_secondary=True) == (
        "alternating-full"
    )
    assert render.secondary_layout_for_shot(2, has_secondary=False) is None


def test_modern_caption_card_has_no_opaque_pill_and_uses_yellow_emphasis() -> None:
    import render_0813_ppi_live as render

    render.load_build_module("build_0813_ppi_live")
    image = render.render_caption_card(
        {
            "text": "AUR PAPER CUP WALE",
            "start_ms": 2_000,
            "font_size": 58,
            "max_width": 900,
        }
    )
    pixels = np.asarray(image)
    alpha = pixels[:, :, 3]
    y, x = np.where(alpha > 0)
    yellow = (
        (pixels[:, :, 0] > 220)
        & (pixels[:, :, 1] > 155)
        & (pixels[:, :, 2] < 120)
        & (alpha > 0)
    )

    assert x.size > 0
    assert int(y.max() - y.min()) >= 48
    occupied = alpha[y.min() : y.max() + 1, x.min() : x.max() + 1] > 0
    assert float(np.mean(occupied)) < 0.94
    assert int(np.count_nonzero(yellow)) > 20


def test_caption_review_accepts_the_modern_900_pixel_safe_width() -> None:
    import review_0813_ppi_live as review

    failures = review._caption_failures(
        {
            "caption_pages": [
                {
                    "id": "caption-modern",
                    "start_ms": 1_000,
                    "end_ms": 1_700,
                    "text": "MODERN CAPTION",
                    "max_width": 900,
                }
            ]
        }
    )

    assert failures == []


def test_presenter_frames_are_locked_to_the_global_dialogue_clock() -> None:
    import render_0813_ppi_live as render

    start_frame, end_frame = render.frame_range_for_interval(7_952, 9_400)

    assert (start_frame, end_frame) == (239, 282)
    assert render.resolve_source_start_ms(
        asset_id="presenter-edl",
        configured_source_start_ms=6_400,
        timeline_start_frame=start_frame,
    ) == 7_967


def test_global_frame_ranges_end_at_exactly_46_seconds() -> None:
    import build_0813_ppi_live as build
    import render_0813_ppi_live as render

    ranges = [
        render.frame_range_for_interval(start, end)
        for start, end in zip(
            build.BOUNDARIES[:-1],
            build.BOUNDARIES[1:],
            strict=True,
        )
    ]

    assert ranges[0][0] == 0
    assert ranges[-1][1] == 1_380
    assert all(
        left[1] == right[0]
        for left, right in zip(ranges, ranges[1:])
    )


def test_ppi_story_matches_the_presenter_led_reference_balance() -> None:
    import render_0813_ppi_live as render

    render.load_build_module("build_0813_ppi_live")
    coverage = render.presenter_coverage_metrics()

    assert 0.58 <= coverage["presenter_pixel_ratio"] <= 0.68
    assert 0.32 <= coverage["visual_pixel_ratio"] <= 0.42
    assert coverage["longest_without_presenter_ms"] <= 3_800


def test_presenter_sync_audit_uses_the_global_render_clock() -> None:
    import render_0813_ppi_live as render

    render.load_build_module("build_0813_ppi_live")
    audit = render.presenter_sync_metrics()

    assert audit["presenter_segments"]
    assert audit["max_presenter_sync_offset_ms"] <= 1000 / render.FPS
    assert all(
        abs(segment["effective_sync_offset_ms"]) <= 1000 / render.FPS
        for segment in audit["presenter_segments"]
    )
    assert all(
        segment["effective_source_start_ms"]
        == segment["rendered_timeline_start_ms"]
        for segment in audit["presenter_segments"]
    )


def test_audio_mix_preserves_the_opening_and_uses_real_ducking() -> None:
    import render_0813_ppi_live as render

    graph = render.audio_filter_graph(sfx_count=3)

    assert "sidechaincompress=" in graph
    assert "atrim=start=" not in graph
    assert "[0:a]aresample=48000" in graph
    assert "afftdn=" not in graph
    assert "deesser=" not in graph
    assert "acompressor=" not in graph
    assert "lowpass=" not in graph
    assert "alimiter=" in graph


def test_loudness_parser_ignores_ffmpeg_text_metadata() -> None:
    import render_0813_ppi_live as render

    parsed = render.parse_loudness_payload(
        {
            "input_i": "-17.20",
            "input_tp": "-2.10",
            "input_lra": "3.40",
            "input_thresh": "-27.30",
            "target_offset": "0.10",
            "normalization_type": "dynamic",
        }
    )

    assert parsed == {
        "input_i": -17.2,
        "input_tp": -2.1,
        "input_lra": 3.4,
        "input_thresh": -27.3,
        "target_offset": 0.1,
    }


def test_review_token_normalization_keeps_numbers_and_hinglish() -> None:
    import review_0813_ppi_live as review

    assert review.normalized_tokens("Goods -0.7%, PPI!") == [
        "goods",
        "0.7",
        "ppi",
    ]
    assert review.normalized_tokens("सोचिए, confirmation ज़रूरी है") == [
        "सोचिए",
        "confirmation",
        "ज़रूरी",
        "है",
    ]


def test_release_gate_blocks_missing_opening_or_exact_facts() -> None:
    import review_0813_ppi_live as review

    passing = review.evaluate_release(
        {
            "decode_ok": True,
            "width": 1080,
            "height": 1920,
            "fps": 30.0,
            "duration_seconds": 46.03,
            "integrated_lufs": -14.2,
            "true_peak_dbtp": -1.1,
            "black_frame_ratio": 0.0,
            "dark_frame_ratio": 0.08,
            "mean_luminance": 98.0,
            "caption_failures": [],
            "caption_accuracy_passed": True,
            "semantic_visuals_passed": True,
            "visual_uniqueness_passed": True,
            "live_video_ratio": 1.0,
            "presenter_pixel_ratio": 0.62,
            "visual_pixel_ratio": 0.38,
            "longest_without_presenter_ms": 3_500,
            "max_presenter_sync_offset_ms": 0.0,
            "audio_alignment_offset_ms": 0.0,
            "asr_similarity": 0.995,
            "missing_protected_tokens": [],
            "unsupported_visible_facts": [],
        }
    )
    failing = review.evaluate_release(
        {
            **passing["metrics"],
            "presenter_pixel_ratio": 0.22,
            "max_presenter_sync_offset_ms": 1_552,
            "missing_protected_tokens": ["सोचिए", "0.7"],
        }
    )

    assert passing["automated_pass"] is True
    assert failing["automated_pass"] is False


def test_release_gate_blocks_each_balance_and_sync_regression() -> None:
    import review_0813_ppi_live as review

    baseline = {
        "decode_ok": True,
        "width": 1080,
        "height": 1920,
        "fps": 30.0,
        "duration_seconds": 46.0,
        "integrated_lufs": -14.2,
        "true_peak_dbtp": -1.1,
        "black_frame_ratio": 0.0,
        "dark_frame_ratio": 0.08,
        "mean_luminance": 98.0,
        "caption_failures": [],
        "caption_accuracy_passed": True,
        "semantic_visuals_passed": True,
        "visual_uniqueness_passed": True,
        "live_video_ratio": 1.0,
        "presenter_pixel_ratio": 0.62,
        "visual_pixel_ratio": 0.38,
        "longest_without_presenter_ms": 3_500,
        "max_presenter_sync_offset_ms": 0.0,
        "audio_alignment_offset_ms": 0.0,
        "asr_similarity": 0.995,
        "missing_protected_tokens": [],
        "unsupported_visible_facts": [],
    }
    regressions = {
        "presenter-balance": {"presenter_pixel_ratio": 0.45},
        "visual-balance": {"visual_pixel_ratio": 0.55},
        "presenter-free-run": {"longest_without_presenter_ms": 4_800},
        "semantic-visuals": {"semantic_visuals_passed": False},
        "visual-uniqueness": {"visual_uniqueness_passed": False},
        "presenter-sync": {"max_presenter_sync_offset_ms": 934},
        "audio-alignment": {"audio_alignment_offset_ms": 70},
        "dark-frame-share": {"dark_frame_ratio": 0.41},
        "mean-luminance": {"mean_luminance": 66.9},
    }

    for failed_check, changes in regressions.items():
        report = review.evaluate_release({**baseline, **changes})
        checks = {
            item["name"]: item["passed"]
            for item in report["checks"]
        }
        assert report["automated_pass"] is False
        assert checks[failed_check] is False


def test_presenter_sync_artifact_records_measured_release_fields() -> None:
    import review_0813_ppi_live as review

    artifact = review.build_presenter_sync_audit(
        presenter_metrics={
            "presenter_pixel_ratio": 0.62,
            "visual_pixel_ratio": 0.38,
            "longest_without_presenter_ms": 3_500,
            "max_presenter_sync_offset_ms": 0.0,
            "presenter_segments": [{"shot_number": 1}],
        },
        audio_alignment_offset_ms=17,
    )

    assert artifact["presenter_pixel_ratio"] == 0.62
    assert artifact["visual_pixel_ratio"] == 0.38
    assert artifact["audio_alignment_offset_ms"] == 17
    assert artifact["balance_passed"] is True
    assert artifact["presenter_sync_passed"] is True
    assert artifact["audio_alignment_passed"] is True


def test_mastering_uses_linear_gain_with_aac_peak_headroom() -> None:
    import render_0813_ppi_live as render

    filter_chain = render.linear_master_filter(
        {
            "input_i": -13.73,
            "input_tp": -0.44,
            "input_lra": 3.5,
            "input_thresh": -23.79,
            "target_offset": 0.45,
        }
    )

    assert filter_chain.startswith("volume=-0.470dB")
    assert "alimiter=limit=0.820000:level=0" in filter_chain
    assert "loudnorm=" not in filter_chain


def test_mastering_can_compensate_for_post_limiter_loudness_shortfall() -> None:
    import render_0813_ppi_live as render

    correction = render.master_loudness_correction_db(-15.0)
    filter_chain = render.linear_master_filter(
        {
            "input_i": -13.73,
            "input_tp": -0.44,
        },
        correction_db=correction,
    )

    assert correction == 0.8
    assert filter_chain.startswith("volume=0.330dB")
    assert "loudnorm=" not in filter_chain


def test_robot_zero_is_qualitative_not_an_evidence_number() -> None:
    import review_0813_ppi_live as review

    assert review.overlay_requires_evidence(
        {"id": "forecast", "text": "FORECAST +0.2%"}
    )
    assert not review.overlay_requires_evidence(
        {
            "id": "robot-market",
            "text": "ROBOT READS 0 · MARKET READS WHY",
        }
    )

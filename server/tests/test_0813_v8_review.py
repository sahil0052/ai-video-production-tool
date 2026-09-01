from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from review_0813_v8 import (
    calculate_envelope_correlation,
    caption_family_review_times,
    compare_asr_word_sequences,
    compare_transcript_payloads,
    evaluate_story,
    evaluate_treatment_diversity,
    faster_whisper_segments_to_payload,
    protected_terms_for_story,
    words_from_transcript_payload,
)


def test_v7_profile_is_blocked_for_reference_10() -> None:
    report = evaluate_story(
        story_id="backtest",
        metrics={
            "presenter_ratio": 0.668,
            "caption_coverage": 0.988,
            "caption_families": ["modern-outline"],
            "technical_caption_share": 0.0,
            "treatment_classes": 4,
            "hard_cuts": 15,
            "median_shot_ms": 2_900,
        },
    )

    assert report["automated_pass"] is False
    assert "presenter-ratio" in report["failed_checks"]
    assert "caption-coverage" in report["failed_checks"]
    assert "caption-family" in report["failed_checks"]


def test_unique_files_do_not_substitute_for_treatment_diversity() -> None:
    report = evaluate_treatment_diversity(
        asset_ids=[f"asset-{index}" for index in range(8)],
        treatments=["generic-stock"] * 8,
    )

    assert report["passed"] is False
    assert report["unique_assets"] == 8
    assert report["unique_treatments"] == 1


def test_reference_profile_metrics_can_pass_but_still_require_human_review() -> None:
    report = evaluate_story(
        story_id="lot-size",
        metrics={
            "presenter_ratio": 0.17,
            "caption_coverage": 0.71,
            "caption_families": [
                "technical-mono",
                "outlined-demo",
                "compact-pill",
            ],
            "technical_caption_share": 0.72,
            "treatment_classes": 8,
            "hard_cuts": 23,
            "median_shot_ms": 1_900,
            "dark_ratio": 0.36,
            "mean_luminance": 86.0,
            "luminance_p10": 15.0,
            "luminance_p90": 225.0,
            "mean_saturation": 72.0,
            "integrated_lufs": -14.2,
            "true_peak_dbtp": -1.2,
            "channels": 2,
            "acoustic_asr": True,
            "asr_retention": 1.0,
            "missing_protected_terms": [],
            "audio_delay_ms": 0,
            "envelope_correlation": 0.98,
            "speech_band_distance_db": 4.0,
        },
    )

    assert report["automated_pass"] is True
    assert report["human_approved"] is False
    assert report["state"] == "awaiting-final-approval"


def test_missing_acoustic_voice_audit_blocks_release() -> None:
    report = evaluate_story(
        story_id="lot-size",
        metrics={
            "presenter_ratio": 0.17,
            "caption_coverage": 0.71,
            "caption_families": [
                "technical-mono",
                "outlined-demo",
                "compact-pill",
            ],
            "technical_caption_share": 0.72,
            "treatment_classes": 8,
            "hard_cuts": 23,
            "median_shot_ms": 1_900,
            "dark_ratio": 0.36,
            "mean_luminance": 86.0,
            "luminance_p10": 15.0,
            "luminance_p90": 225.0,
            "mean_saturation": 72.0,
            "integrated_lufs": -14.2,
            "true_peak_dbtp": -1.2,
            "channels": 2,
        },
    )

    assert report["automated_pass"] is False
    assert "acoustic-asr" in report["failed_checks"]
    assert "audio-delay" in report["failed_checks"]
    assert "envelope-correlation" in report["failed_checks"]
    assert "speech-band-distance" in report["failed_checks"]


def test_flat_tonal_range_blocks_reference_profile() -> None:
    report = evaluate_story(
        story_id="lot-size",
        metrics={
            "presenter_ratio": 0.17,
            "caption_coverage": 0.71,
            "caption_families": [
                "technical-mono",
                "outlined-demo",
                "compact-pill",
            ],
            "technical_caption_share": 0.72,
            "treatment_classes": 8,
            "hard_cuts": 23,
            "median_shot_ms": 1_900,
            "dark_ratio": 0.36,
            "mean_luminance": 86.0,
            "luminance_p10": 15.0,
            "luminance_p90": 150.0,
            "mean_saturation": 72.0,
            "integrated_lufs": -14.2,
            "true_peak_dbtp": -1.2,
            "channels": 2,
            "acoustic_asr": True,
            "asr_retention": 1.0,
            "missing_protected_terms": [],
            "audio_delay_ms": 0,
            "envelope_correlation": 0.98,
            "speech_band_distance_db": 4.0,
        },
    )

    assert report["automated_pass"] is False
    assert "luminance-p90" in report["failed_checks"]


def test_asr_retention_handles_mixed_hindi_english_and_numbers() -> None:
    source = ["सोचिए,", "PPI", "0.2", "Thank", "you."]
    exact = compare_asr_word_sequences(
        source,
        source,
        protected_terms=["सोचिए", "ppi", "0.2", "thank", "you"],
    )
    missing = compare_asr_word_sequences(
        source,
        ["सोचिए,", "0.2", "Thank", "you."],
        protected_terms=["सोचिए", "ppi", "0.2", "thank", "you"],
    )

    assert exact["retention_ratio"] == 1.0
    assert exact["missing_protected_terms"] == []
    assert missing["retention_ratio"] < 1.0
    assert missing["missing_protected_terms"] == ["ppi"]


def test_envelope_correlation_tolerates_quiet_music_bed() -> None:
    sample_rate = 48_000
    time = np.arange(sample_rate * 3) / sample_rate
    envelope = 0.25 + 0.75 * np.square(np.sin(2 * np.pi * 1.7 * time))
    source = envelope * np.sin(2 * np.pi * 220 * time)
    quiet_bed = 0.015 * np.sin(2 * np.pi * 73 * time)

    correlation = calculate_envelope_correlation(
        source,
        0.82 * source + quiet_bed,
        sample_rate=sample_rate,
        delay_ms=0,
    )

    assert correlation >= 0.95


def test_transcript_payload_words_support_source_and_deepgram_shapes() -> None:
    source_words = words_from_transcript_payload(
        {"words": [{"word": "Do"}, {"word": "you"}]}
    )
    final_words = words_from_transcript_payload(
        {
            "results": {
                "channels": [
                    {
                        "alternatives": [
                            {
                                "words": [
                                    {"punctuated_word": "Do"},
                                    {"word": "you"},
                                ]
                            }
                        ]
                    }
                ]
            }
        }
    )

    assert source_words == ["Do", "you"]
    assert final_words == ["Do", "you"]


def test_protected_terms_include_openings_numbers_product_and_cta() -> None:
    terms = protected_terms_for_story(
        "lot-size",
        [
            "Do",
            "you",
            "know?",
            "Lot",
            "size",
            "100",
            "pizzas.",
            "Risk",
            "matters.",
            "Follow",
            "Thank",
            "you.",
        ],
    )

    assert {
        "do",
        "lot",
        "size",
        "100",
        "risk",
        "follow",
        "thank",
        "you",
    } <= set(terms)


def test_acoustic_asr_compares_source_and_final_with_same_payload_shape() -> None:
    source = {
        "results": {
            "channels": [
                {
                    "alternatives": [
                        {
                            "words": [
                                {"word": "PPI"},
                                {"word": "works"},
                                {"word": "Thank"},
                                {"word": "you"},
                            ]
                        }
                    ]
                }
            ]
        }
    }
    final = {
        "results": {
            "channels": [
                {
                    "alternatives": [
                        {
                            "words": [
                                {"word": "PPI"},
                                {"word": "works"},
                                {"word": "Thank"},
                                {"word": "you"},
                            ]
                        }
                    ]
                }
            ]
        }
    }

    report = compare_transcript_payloads("ppi", source, final)

    assert report["retention_ratio"] == 1.0
    assert report["missing_protected_terms"] == []


def test_faster_whisper_segments_keep_word_timestamps() -> None:
    payload = faster_whisper_segments_to_payload(
        [
            SimpleNamespace(
                text=" PPI works.",
                words=[
                    SimpleNamespace(
                        word=" PPI",
                        start=0.1,
                        end=0.4,
                        probability=0.98,
                    ),
                    SimpleNamespace(
                        word=" works.",
                        start=0.4,
                        end=0.8,
                        probability=0.96,
                    ),
                ],
            )
        ],
        language="hi",
    )

    assert payload["words"] == [
        {
            "word": "PPI",
            "punctuated_word": "PPI",
            "start": 0.1,
            "end": 0.4,
            "confidence": 0.98,
        },
        {
            "word": "works.",
            "punctuated_word": "works.",
            "start": 0.4,
            "end": 0.8,
            "confidence": 0.96,
        },
    ]


def test_offline_asr_is_diagnostic_not_reported_as_missing_speech() -> None:
    report = evaluate_story(
        story_id="lot-size",
        metrics={
            "presenter_ratio": 0.17,
            "caption_coverage": 0.71,
            "caption_families": [
                "technical-mono",
                "outlined-demo",
                "compact-pill",
            ],
            "technical_caption_share": 0.72,
            "treatment_classes": 8,
            "hard_cuts": 23,
            "median_shot_ms": 1_900,
            "dark_ratio": 0.36,
            "mean_luminance": 86.0,
            "luminance_p10": 15.0,
            "luminance_p90": 225.0,
            "mean_saturation": 72.0,
            "integrated_lufs": -14.2,
            "true_peak_dbtp": -1.2,
            "channels": 2,
            "acoustic_asr": False,
            "asr_diagnostic_only": True,
            "asr_method": "faster-whisper-small-v2:acoustic-word-sequence",
            "asr_retention": 0.82,
            "missing_protected_terms": ["lot", "risk"],
            "audio_delay_ms": 0,
            "envelope_correlation": 0.98,
            "speech_band_distance_db": 4.0,
        },
    )

    assert report["automated_pass"] is False
    assert "acoustic-asr" in report["failed_checks"]
    assert "asr-retention" not in report["failed_checks"]
    assert "protected-words" not in report["failed_checks"]


def test_single_unprotected_asr_variance_can_pass_with_exact_audio_continuity() -> None:
    report = evaluate_story(
        story_id="ppi",
        metrics={
            "presenter_ratio": 0.18,
            "caption_coverage": 0.71,
            "caption_families": [
                "technical-mono",
                "documentary-clean",
                "compact-pill",
            ],
            "technical_caption_share": 0.5,
            "treatment_classes": 12,
            "hard_cuts": 33,
            "median_shot_ms": 1_300,
            "dark_ratio": 0.28,
            "mean_luminance": 90,
            "luminance_p10": 18,
            "luminance_p90": 225,
            "mean_saturation": 65,
            "integrated_lufs": -14.2,
            "true_peak_dbtp": -1.5,
            "channels": 2,
            "acoustic_asr": True,
            "asr_retention": 150 / 151,
            "asr_missing_tokens": ["है"],
            "missing_protected_terms": [],
            "audio_delay_ms": 5,
            "envelope_correlation": 0.9998,
            "speech_band_distance_db": 0.6,
        },
    )

    assert report["automated_pass"] is True
    assert "asr-retention" not in report["failed_checks"]


def test_multiple_asr_misses_still_block_even_with_good_audio_continuity() -> None:
    report = evaluate_story(
        story_id="ppi",
        metrics={
            "presenter_ratio": 0.18,
            "caption_coverage": 0.71,
            "caption_families": [
                "technical-mono",
                "documentary-clean",
                "compact-pill",
            ],
            "technical_caption_share": 0.5,
            "treatment_classes": 12,
            "hard_cuts": 33,
            "median_shot_ms": 1_300,
            "dark_ratio": 0.28,
            "mean_luminance": 90,
            "luminance_p10": 18,
            "luminance_p90": 225,
            "mean_saturation": 65,
            "integrated_lufs": -14.2,
            "true_peak_dbtp": -1.5,
            "channels": 2,
            "acoustic_asr": True,
            "asr_retention": 149 / 151,
            "asr_missing_tokens": ["है", "था"],
            "missing_protected_terms": [],
            "audio_delay_ms": 5,
            "envelope_correlation": 0.9998,
            "speech_band_distance_db": 0.6,
        },
    )

    assert report["automated_pass"] is False
    assert "asr-retention" in report["failed_checks"]


def test_caption_review_uses_first_visible_midpoint_per_family() -> None:
    pages = [
        {
            "start_ms": 0,
            "end_ms": 800,
            "family": "technical-mono",
        },
        {
            "start_ms": 800,
            "end_ms": 1_400,
            "family": "technical-mono",
        },
        {
            "start_ms": 1_400,
            "end_ms": 2_200,
            "family": "outlined-demo",
        },
    ]

    assert caption_family_review_times(pages) == {
        "technical-mono": 400,
        "outlined-demo": 1_800,
    }

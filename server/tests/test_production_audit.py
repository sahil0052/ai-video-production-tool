import importlib
import importlib.util

import cv2
import numpy as np
import pytest

from app.models import ShotSpec


def _audit_module():
    spec = importlib.util.find_spec("app.editor.production_audit")
    assert spec is not None
    return importlib.import_module("app.editor.production_audit")


def test_frame_sample_summary_reports_reference_tonal_range() -> None:
    audit = _audit_module()
    result = audit.summarize_frame_samples(
        luminance_values=[10.0, 12.0, 20.0, 230.0, 240.0, 245.0],
        saturation_values=[50.0, 55.0, 60.0, 65.0, 70.0, 75.0],
        motion_values=[1.0, 2.0, 3.0],
        dark_threshold=55,
        bright_threshold=180,
    )

    assert result["dark_frame_ratio"] == pytest.approx(0.5)
    assert result["bright_frame_ratio"] == pytest.approx(0.5)
    assert result["luminance_p10"] == pytest.approx(11.0)
    assert result["luminance_p90"] == pytest.approx(242.5)
    assert result["mean_saturation"] == pytest.approx(62.5)


def test_reference_max_frame_gates_use_rendered_metrics() -> None:
    audit = _audit_module()
    result = audit.evaluate_reference_max_frame_metrics(
        {
            "rendered_cut_count": 21,
            "median_shot_ms": 1580,
            "motion_score": 5.4,
            "dark_frame_ratio": 0.42,
            "mean_luminance": 94.0,
            "mean_saturation": 69.0,
            "real_source_ratio": 0.70,
            "procedural_ratio": 0.20,
            "visual_source_count": 7,
        }
    )

    assert result["automated_pass"] is True
    assert all(check["passed"] for check in result["checks"])


def test_reference_max_frame_gates_block_metadata_only_quality() -> None:
    audit = _audit_module()
    result = audit.evaluate_reference_max_frame_metrics(
        {
            "rendered_cut_count": 13,
            "median_shot_ms": 2970,
            "motion_score": 3.18,
            "dark_frame_ratio": 0.595,
            "mean_luminance": 65.7,
            "mean_saturation": 126.7,
            "real_source_ratio": 0.20,
            "procedural_ratio": 0.70,
            "visual_source_count": 3,
        }
    )

    assert result["automated_pass"] is False
    assert {
        check["name"]
        for check in result["checks"]
        if not check["passed"]
    } >= {
        "rendered-cuts",
        "median-shot",
        "motion",
        "darkness",
        "luminance",
        "saturation",
        "real-source-coverage",
        "procedural-share",
        "visual-source-diversity",
    }


def test_v3_frame_gates_allow_designed_visual_share() -> None:
    audit = _audit_module()
    result = audit.evaluate_reference_max_v3_frame_metrics(
        {
            "rendered_cut_count": 27,
            "median_shot_ms": 1460,
            "motion_score": 5.8,
            "dark_frame_ratio": 0.31,
            "mean_luminance": 96.0,
            "mean_saturation": 67.0,
            "real_source_ratio": 0.48,
            "procedural_ratio": 0.43,
            "visual_source_count": 12,
        }
    )

    assert result["automated_pass"] is True
    assert {
        check["name"] for check in result["checks"]
    }.isdisjoint({"real-source-coverage", "procedural-share"})


def test_source_coverage_counts_real_pixels_not_treatment_names() -> None:
    audit = _audit_module()
    shots = [
        ShotSpec(
            id="presenter",
            start_ms=0,
            end_ms=1000,
            role="hook",
            layout="presenter",
            treatment="presenter",
            caption_family="compact-pill",
            source_kind="presenter",
            reference_role="primary-10",
        ),
        ShotSpec(
            id="capture-a",
            start_ms=1000,
            end_ms=4000,
            role="demonstration",
            layout="asset-full",
            treatment="crop-a",
            caption_family="technical-mono",
            source_kind="screen-recording",
            reference_role="primary-10",
            asset_id="capture-metaeditor-a",
        ),
        ShotSpec(
            id="capture-b",
            start_ms=4000,
            end_ms=6500,
            role="evidence",
            layout="asset-full",
            treatment="page-crop",
            caption_family="documentary-clean",
            source_kind="direct-source",
            reference_role="primary-10",
            asset_id="capture-evidence-a",
        ),
        ShotSpec(
            id="diagram",
            start_ms=6500,
            end_ms=8000,
            role="contrast",
            layout="graphic",
            treatment="wrong-rule",
            caption_family="technical-mono",
            source_kind="procedural",
            reference_role="secondary-4",
            asset_id="diagram-wrong-rule",
        ),
    ]

    coverage = audit.calculate_source_coverage(shots, duration_ms=8000)

    assert coverage["real_source_ratio"] == pytest.approx(0.8125)
    assert coverage["procedural_ratio"] == pytest.approx(0.1875)
    assert coverage["visual_source_count"] == 4


def test_visual_language_distribution_measures_editorial_roles() -> None:
    audit = _audit_module()
    shots = [
        ShotSpec(
            id="cinematic",
            start_ms=0,
            end_ms=2000,
            role="hook",
            layout="asset-full",
            treatment="cinematic-monitor",
            caption_family="technical-mono",
            source_kind="licensed-footage",
            reference_role="primary-10",
            visual_category="cinematic-broll",
            primary_subject="physical monitor",
            source_family="coverr-monitor",
        ),
        ShotSpec(
            id="designed",
            start_ms=2000,
            end_ms=6000,
            role="explanation",
            layout="graphic",
            treatment="pipeline",
            caption_family="technical-mono",
            source_kind="procedural",
            reference_role="primary-10",
            visual_category="designed-explanation",
            primary_subject="read decide execute pipeline",
            source_family="pipeline-design",
        ),
        ShotSpec(
            id="evidence",
            start_ms=6000,
            end_ms=8000,
            role="evidence",
            layout="asset-full",
            treatment="evidence-excerpt",
            caption_family="documentary-clean",
            source_kind="direct-source",
            reference_role="supporting",
            visual_category="edited-evidence",
            primary_subject="verified result excerpt",
            source_family="mql5-result",
        ),
        ShotSpec(
            id="product",
            start_ms=8000,
            end_ms=9000,
            role="demonstration",
            layout="asset-full",
            treatment="risk-input-macro",
            caption_family="technical-mono",
            source_kind="screen-recording",
            reference_role="supporting",
            visual_category="product-macro",
            primary_subject="risk input",
            source_family="mt5-risk-input",
            simultaneous_actions=1,
        ),
        ShotSpec(
            id="presenter",
            start_ms=9000,
            end_ms=10000,
            role="cta",
            layout="presenter",
            treatment="presenter-ending",
            caption_family="compact-pill",
            source_kind="presenter",
            reference_role="primary-10",
            visual_category="presenter",
            primary_subject="presenter",
            source_family="presenter",
        ),
    ]

    result = audit.calculate_visual_language_distribution(
        shots,
        duration_ms=10_000,
    )

    assert result["ratios"]["cinematic-broll"] == pytest.approx(0.20)
    assert result["ratios"]["designed-explanation"] == pytest.approx(0.40)
    assert result["ratios"]["edited-evidence"] == pytest.approx(0.20)
    assert result["ratios"]["literal-desktop-ui"] == 0
    assert result["missing_primary_subjects"] == []
    assert result["software_multi_action_shots"] == []
    assert result["max_consecutive_source_repeats"] == 1


def test_v3_visual_language_gates_block_desktop_tutorials() -> None:
    audit = _audit_module()
    evaluation = audit.evaluate_reference_max_visual_language(
        {
            "ratios": {
                "literal-desktop-ui": 0.62,
                "designed-explanation": 0.08,
                "cinematic-broll": 0.02,
                "edited-evidence": 0.15,
            },
            "missing_primary_subjects": ["scene-3"],
            "software_multi_action_shots": ["scene-4"],
            "full_page_overview_violations": ["scene-5"],
            "max_consecutive_source_repeats": 5,
        }
    )

    assert evaluation["automated_pass"] is False
    assert {
        check["name"]
        for check in evaluation["checks"]
        if not check["passed"]
    } >= {
        "literal-desktop-ui",
        "designed-explanation",
        "cinematic-broll",
        "primary-subjects",
        "single-software-action",
        "evidence-overview-duration",
        "source-repetition",
    }


def test_asr_retention_flags_missing_sentence_openings_and_numbers() -> None:
    audit = _audit_module()
    report = audit.compare_asr_tokens(
        source_text=(
            "Do you know what a Forex Trading Robot is? "
            "In 2008 an Expert Advisor earned $110,000."
        ),
        final_text=(
            "you know what a Forex Trading Robot is? "
            "In an Expert Advisor earned dollars."
        ),
        protected_terms=["Do", "Forex Trading Robot", "2008", "$110,000"],
    )

    assert report["retention_ratio"] < 0.99
    assert "do" in report["missing_tokens"]
    assert "2008" in report["missing_tokens"]
    assert report["protected_terms_ok"] is False


def test_asr_retention_excludes_only_missing_unaligned_source_tokens() -> None:
    audit = _audit_module()
    report = audit.compare_asr_tokens(
        source_text="But what if the rules are wrong?",
        final_text="But if the rules are wrong.",
        protected_terms=[],
        unverifiable_source_tokens=["what"],
    )

    assert report["raw_source_token_count"] == 7
    assert report["source_token_count"] == 6
    assert report["retained_token_count"] == 6
    assert report["ignored_unaligned_source_tokens"] == ["what"]
    assert report["retention_ratio"] == 1


def test_asr_content_retention_normalizes_harmless_transcription_variants() -> None:
    audit = _audit_module()
    report = audit.compare_asr_tokens(
        source_text=(
            "This wasn't a huge loss. "
            "Profit Bricks used controlled automation."
        ),
        final_text=(
            "This was not a big loss. "
            "Profit Bricks used control automation."
        ),
        protected_terms=["Profit Bricks"],
    )

    assert report["raw_retention_ratio"] < 1
    assert report["content_retention_ratio"] == 1
    assert report["missing_content_tokens"] == []
    assert report["protected_terms_ok"] is True


def test_asr_protected_terms_accept_explicit_review_aliases() -> None:
    audit = _audit_module()
    report = audit.compare_asr_tokens(
        source_text="Night Capital processed 40 lakhs of orders.",
        final_text="Night Capital processed 40 lakhs of orders.",
        protected_terms=["Knight Capital", "40 lakh"],
        protected_term_aliases={
            "Knight Capital": ["Night Capital"],
            "40 lakh": ["40 lakhs"],
        },
    )

    assert report["protected_terms_ok"] is True
    assert report["missing_protected_terms"] == []


def test_measure_frame_audit_reads_every_rendered_frame(tmp_path) -> None:
    audit = _audit_module()
    video = tmp_path / "frames.avi"
    writer = cv2.VideoWriter(
        str(video),
        cv2.VideoWriter_fourcc(*"MJPG"),
        2,
        (108, 192),
    )
    assert writer.isOpened()
    for value in [20, 40, 80, 120, 160, 200]:
        frame = np.full((192, 108, 3), value, dtype=np.uint8)
        frame[:, :20, 2] = min(255, value + 30)
        writer.write(frame)
    writer.release()

    metrics = audit.measure_frame_audit(video)

    assert metrics["frame_count"] == 6
    assert metrics["sampled_frame_count"] == 6
    assert metrics["mean_luminance"] > 0
    assert metrics["mean_saturation"] > 0
    assert metrics["motion_score"] > 0


def test_composition_parity_measures_blank_space_and_static_holds(
    tmp_path,
) -> None:
    audit = _audit_module()
    video = tmp_path / "composition.avi"
    writer = cv2.VideoWriter(
        str(video),
        cv2.VideoWriter_fourcc(*"MJPG"),
        10,
        (180, 320),
    )
    assert writer.isOpened()
    dark = np.full((320, 180, 3), 12, dtype=np.uint8)
    for _ in range(10):
        writer.write(dark)
    for offset in range(10):
        bright = np.full((320, 180, 3), 238, dtype=np.uint8)
        cv2.rectangle(
            bright,
            (20 + offset * 2, 100),
            (100 + offset * 2, 180),
            (40, 40, 40),
            -1,
        )
        writer.write(bright)
    writer.release()

    report = audit.measure_composition_parity(video)

    assert report["sample_fps"] == 10
    assert report["bright_uniform_blank_mean"] > 0.2
    assert report["dark_uniform_blank_mean"] > 0.2
    assert report["near_static_pair_ratio"] > 0.3
    assert report["occupied_local_detail_mean"] < 0.5
    assert report["edge_density_mean"] < 0.1


def test_training_parity_composition_gates_accept_reference_like_metrics():
    audit = _audit_module()

    result = audit.evaluate_training_parity_composition(
        {
            "edge_density_mean": 0.0733,
            "near_static_pair_ratio": 0.4102,
            "bright_uniform_blank_p90": 0.415,
            "dark_uniform_blank_mean": 0.3609,
        }
    )

    assert result["automated_pass"] is True
    assert all(check["passed"] for check in result["checks"])


def test_training_parity_composition_gates_reject_v7_like_metrics():
    audit = _audit_module()

    result = audit.evaluate_training_parity_composition(
        {
            "edge_density_mean": 0.1173,
            "near_static_pair_ratio": 0.0,
            "bright_uniform_blank_p90": 0.4935,
            "dark_uniform_blank_mean": 0.1597,
        }
    )

    assert result["automated_pass"] is False
    assert {
        check["name"]
        for check in result["checks"]
        if not check["passed"]
    } == {
        "local-edge-density",
        "intentional-static-holds",
        "bright-blank-space",
        "dark-negative-space",
    }


def test_audio_pulse_estimator_recovers_documentary_90_bpm() -> None:
    audit = _audit_module()
    sample_rate = 48_000
    duration_seconds = 20
    samples = np.zeros(sample_rate * duration_seconds, dtype=np.float64)
    beat_interval = round(sample_rate * 60 / 90)
    pulse = np.hanning(960) * 12_000
    for start in range(0, samples.size - pulse.size, beat_interval):
        samples[start : start + pulse.size] += pulse

    estimate = audit.estimate_audio_pulse_bpm(
        samples,
        sample_rate=sample_rate,
        bpm_min=80,
        bpm_max=105,
    )

    assert 89 <= estimate <= 91


def test_estimate_audio_delay_detects_small_alignment_offset() -> None:
    audit = _audit_module()
    sample_rate = 1000
    source = np.zeros(3000, dtype=np.float32)
    source[500:800] = np.linspace(0, 1, 300)
    final = np.pad(source, (70, 0))[: source.size]

    delay_ms = audit.estimate_audio_delay_ms(
        source,
        final,
        sample_rate=sample_rate,
    )

    assert 60 <= delay_ms <= 80


def test_audio_continuity_report_blocks_uncorrected_delay() -> None:
    audit = _audit_module()
    sample_rate = 1000
    source = np.zeros(3000, dtype=np.float32)
    source[400:900] = np.sin(np.linspace(0, 16 * np.pi, 500))
    final = np.pad(source, (70, 0))[: source.size]

    report = audit.build_audio_continuity_report(
        source,
        final,
        sample_rate=sample_rate,
        allowed_delay_ms=20,
    )

    assert 60 <= report["estimated_delay_ms"] <= 80
    assert report["delay_passed"] is False
    assert report["duration_delta_ms"] == 0
    assert report["spectral_continuity_db"] >= 0


def test_audio_continuity_allows_one_codec_frame_of_tail_difference() -> None:
    audit = _audit_module()
    sample_rate = 1000
    source = np.sin(np.linspace(0, 20 * np.pi, 3000)).astype(np.float32)
    final = source[:-36]

    report = audit.build_audio_continuity_report(
        source,
        final,
        sample_rate=sample_rate,
        allowed_delay_ms=20,
    )

    assert report["duration_delta_ms"] == -36
    assert report["duration_passed"] is True


def test_audio_continuity_measures_speech_band_not_intentional_high_end_mix() -> None:
    audit = _audit_module()
    sample_rate = 48_000
    sample_count = sample_rate * 4
    frequencies = np.fft.rfftfreq(sample_count, 1 / sample_rate)
    random = np.random.default_rng(4)

    def band_noise(low: float, high: float, amplitude: float):
        signal = random.normal(0, 1, sample_count)
        spectrum = np.fft.rfft(signal)
        spectrum[(frequencies < low) | (frequencies > high)] = 0
        filtered = np.fft.irfft(spectrum, n=sample_count)
        return filtered / np.max(np.abs(filtered)) * amplitude

    source = band_noise(200, 7000, 10_000)
    final = source + band_noise(10_000, 22_000, 2000)

    report = audit.build_audio_continuity_report(
        source,
        final,
        sample_rate=sample_rate,
    )

    assert report["delay_passed"] is True
    assert report["spectral_band_hz"] == [200, 8000]
    assert report["spectral_passed"] is True

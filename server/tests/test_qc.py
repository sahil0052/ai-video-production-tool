import numpy as np

from app.editor import qc
from app.editor.planning import build_edit_plan
from app.editor.qc import (
    _caption_page_overflows,
    _is_black_frame,
    _major_visual_event_times,
    _measure_cut_onsets,
    evaluate_qc,
)
from app.models import (
    CaptionPage,
    CaptionToken,
    QCMeasurements,
    TimelineMapSegment,
    TranscriptSegment,
    TranscriptWord,
    VideoMetadata,
)


def make_plan():
    words = [
        TranscriptWord(
            start=index * 0.25,
            end=(index + 1) * 0.25,
            text=text,
            confidence=0.95,
        )
        for index, text in enumerate(
            ["This", "AI", "chip", "is", "much", "faster", "today"]
        )
    ]
    return build_edit_plan(
        source_filename="source.mp4",
        metadata=VideoMetadata(
            width=720,
            height=1280,
            fps=30,
            frame_count=60,
            duration_seconds=2,
        ),
        transcript=[
            TranscriptSegment(
                start=0,
                end=1.75,
                text=" ".join(word.text for word in words),
                words=words,
            )
        ],
    )


def test_evaluate_qc_passes_a_social_ready_edit() -> None:
    plan = make_plan()
    measurements = QCMeasurements(
        integrated_lufs=-14.1,
        true_peak_dbtp=-1.2,
        longest_silence_ms=80,
        black_frame_ratio=0,
        freeze_frame_ratio=0.01,
        cuts_per_minute=42,
        median_shot_ms=1400,
        cut_onset_percent=78,
        caption_overflow_count=0,
        meaningful_visual_coverage=0.66,
    )

    report = evaluate_qc(plan, measurements)

    assert report.passed is True
    assert report.style_score >= 80
    assert all(check.passed for check in report.checks)


def test_evaluate_qc_fails_dead_frames_and_bad_audio() -> None:
    plan = make_plan()
    measurements = QCMeasurements(
        integrated_lufs=-18,
        true_peak_dbtp=0,
        longest_silence_ms=500,
        black_frame_ratio=0.08,
        freeze_frame_ratio=0.2,
        cuts_per_minute=8,
        median_shot_ms=6000,
        cut_onset_percent=20,
        caption_overflow_count=2,
        meaningful_visual_coverage=0.1,
    )

    report = evaluate_qc(plan, measurements)

    assert report.passed is False
    assert report.style_score < 80
    assert {check.name for check in report.checks if not check.passed} >= {
        "loudness",
        "true_peak",
        "silence",
        "black_frames",
        "caption_overflow",
        "meaningful_visuals",
    }


def test_evaluate_qc_rejects_presenter_only_visual_coverage() -> None:
    plan = make_plan()
    measurements = QCMeasurements(
        integrated_lufs=-14.2,
        true_peak_dbtp=-1.2,
        longest_silence_ms=80,
        black_frame_ratio=0,
        freeze_frame_ratio=0,
        cuts_per_minute=40,
        median_shot_ms=1400,
        cut_onset_percent=80,
        caption_overflow_count=0,
        meaningful_visual_coverage=0.12,
    )

    report = evaluate_qc(plan, measurements)
    checks = {check.name: check for check in report.checks}

    assert "meaningful_visuals" in checks
    assert checks["meaningful_visuals"].passed is False
    assert report.passed is False


def test_evaluate_qc_requires_major_cuts_near_audio_onsets() -> None:
    plan = make_plan()
    measurements = QCMeasurements(
        integrated_lufs=-14.2,
        true_peak_dbtp=-1.2,
        longest_silence_ms=80,
        black_frame_ratio=0,
        freeze_frame_ratio=0,
        cuts_per_minute=40,
        median_shot_ms=1400,
        cut_onset_percent=60,
        caption_overflow_count=0,
        meaningful_visual_coverage=0.65,
    )

    report = evaluate_qc(plan, measurements)

    assert next(
        check for check in report.checks if check.name == "cut_onsets"
    ).passed is False
    assert report.passed is False


def test_evaluate_qc_rejects_excessive_static_frame_ratio() -> None:
    plan = make_plan()
    measurements = QCMeasurements(
        integrated_lufs=-14.2,
        true_peak_dbtp=-1.2,
        longest_silence_ms=80,
        black_frame_ratio=0,
        freeze_frame_ratio=0.2,
        cuts_per_minute=40,
        median_shot_ms=1400,
        cut_onset_percent=80,
        caption_overflow_count=0,
        meaningful_visual_coverage=0.65,
    )

    report = evaluate_qc(plan, measurements)

    assert next(
        check for check in report.checks if check.name == "freeze_frames"
    ).passed is False
    assert report.passed is False


def test_cut_onset_measurement_allows_a_100ms_sync_window() -> None:
    sample_rate = 1000
    samples = np.zeros(sample_rate, dtype=np.float32)
    samples[100:180] = 0.1
    samples[300:380] = 0.2
    samples[580:700] = 1.0

    percentage = _measure_cut_onsets(
        samples,
        sample_rate,
        event_times_ms=[500],
    )

    assert percentage == 100


def test_measure_cut_onsets_for_video_uses_rendered_event_times(
    monkeypatch,
    tmp_path,
) -> None:
    measure_video = getattr(qc, "measure_cut_onsets_for_video", None)
    assert measure_video is not None

    sample_rate = 1000
    samples = np.zeros(sample_rate, dtype=np.float32)
    samples[100:180] = 0.1
    samples[300:380] = 0.2
    samples[580:700] = 1.0
    monkeypatch.setattr(
        qc,
        "_extract_audio",
        lambda _path: (samples, sample_rate),
    )

    assert measure_video(tmp_path / "edited.mp4", [500]) == 100


def test_major_onset_events_exclude_speech_only_timeline_cuts() -> None:
    plan = make_plan().model_copy(
        update={
            "timeline": [
                TimelineMapSegment(
                    source_start_ms=0,
                    source_end_ms=100,
                    output_start_ms=0,
                    output_end_ms=100,
                ),
                TimelineMapSegment(
                    source_start_ms=200,
                    source_end_ms=300,
                    output_start_ms=100,
                    output_end_ms=200,
                ),
            ]
        }
    )

    events = _major_visual_event_times(plan)

    assert 100 not in events


def test_black_frame_detection_preserves_dark_editorial_graphics() -> None:
    dark_graphic = np.full((170, 96), 4, dtype=np.uint8)
    dark_graphic[20:30, 20:40] = 220

    assert _is_black_frame(dark_graphic) is False
    assert _is_black_frame(np.full((170, 96), 4, dtype=np.uint8)) is True


def test_caption_overflow_heuristic_respects_wrapping_families() -> None:
    tokens = [
        CaptionToken(
            text=text,
            start_ms=index * 100,
            end_ms=(index + 1) * 100,
            highlighted=False,
            confidence=0.99,
        )
        for index, text in enumerate(
            ["in", "the", "Automated", "Trading", "Championship,"]
        )
    ]
    documentary = CaptionPage(
        start_ms=0,
        end_ms=500,
        tokens=tokens,
        family="documentary-clean",
        anchor="center-71",
        transition="hard-cut",
        max_width=920,
    )
    compact = documentary.model_copy(
        update={
            "family": "compact-pill",
            "anchor": "center-76",
            "max_width": 900,
        }
    )

    assert _caption_page_overflows(documentary) is False
    assert _caption_page_overflows(compact) is True

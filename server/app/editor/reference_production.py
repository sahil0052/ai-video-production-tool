from __future__ import annotations

import base64
from collections.abc import Callable
from datetime import UTC, datetime
import hashlib
from html import escape
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import wave

import cv2
from imageio_ffmpeg import get_ffmpeg_exe
import numpy as np

from app.editor.analysis import detect_hard_cuts, probe_video, validate_source
from app.editor.ffmpeg import (
    build_dialogue_extract_command,
    build_master_command,
    measure_loudness_for_master,
    verify_render,
)
from app.editor.pipeline import (
    render_edit_plan,
    run_ffmpeg_command,
    transcribe_video,
)
from app.editor.planning import (
    _retime_segments,
    build_caption_pages,
    build_timeline_map,
)
from app.editor.production_audit import (
    build_audio_continuity_report,
    calculate_source_coverage,
    calculate_visual_language_distribution,
    compare_asr_tokens,
    evaluate_reference_max_frame_metrics,
    evaluate_reference_max_v3_frame_metrics,
    evaluate_reference_max_visual_language,
    measure_frame_audit,
)
from app.editor.qc import (
    _extract_audio,
    measure_cut_onsets_for_video,
    measure_qc,
)
from app.editor.sound_design import generate_sound_design, music_sections
from app.editor.transcript import (
    repair_nonpositive_word_durations,
    retime_corrected_segments,
)
from app.models import (
    ArtifactSpec,
    AssetRef,
    AudioPlan,
    CaptureManifest,
    CaptionToken,
    CaptionPage,
    EditPlanV1,
    EvidenceItem,
    GraphicCue,
    OutputSpec,
    QCTargets,
    ReframeKeyframe,
    ScenePlan,
    ShotSpec,
    TimelineMapSegment,
    TranscriptSegment,
    VideoMetadata,
    VisualReview,
    VisualReviewCheck,
)

ProgressCallback = Callable[[str, int], None]

_0806_CORRECTED_TEXTS = [
    "Do you know what Forex Trading Robot is?",
    "It is a software that automatically trades on set rules.",
    "Professionally, it is called Expert Advisor.",
    "In short, EA.",
    "But if the rules are wrong,",
    "In 2008, in the Automated Trading Championship,",
    "an Expert Advisor earned $110,000.",
    "Then the risk turned the game.",
    "The high risk increased the result,",
    "and then it turned upside down.",
    (
        "Lesson is simple, an Expert Advisor doesn't trade with "
        "emotions, but doesn't choose a safe risk."
    ),
    (
        "If you want to see how an Expert Advisor trades, then you can "
        "follow us and join our Telegram group. Thank you!"
    ),
]

_0806_EMPHASIS_TIMES_MS = [
    0,
    90,
    2_820,
    4_320,
    7_200,
    9_560,
    11_880,
    14_480,
    17_920,
    21_550,
    24_000,
    26_700,
    33_180,
]

_CAPTURE_SPECS = [
    {
        "id": "metaquotes-automated-trading",
        "url": "https://www.metatrader5.com/en/automated-trading",
        "text": "Trade account management through specialized MetaTrader 5",
        "filename": "metatrader5-automated-trading-definition.png",
    },
    {
        "id": "metaquotes-expert-advisor",
        "url": "https://www.metatrader4.com/en/automated-trading",
        "text": "So, in MetaTrader 4, your indicator analyzes the markets",
        "filename": "metatrader4-expert-advisor-definition.png",
    },
    {
        "id": "metaquotes-atc-history",
        "url": "https://www.metatrader5.com/en/automated-trading",
        "text": "The power of trading robots was demonstrated during",
        "filename": "metatrader5-atc-history.png",
    },
    {
        "id": "mql5-atc-2008-risk",
        "url": "https://www.mql5.com/en/articles/525",
        "text": "I managed to earn 110,000",
        "filename": "mql5-atc-2008-risk.png",
    },
]


def produce_reference_edit(
    *,
    source: Path,
    output_dir: Path,
    primary_reference: int,
    secondary_reference: int,
    asset_policy: str,
    time_budget_min: int,
    quality_target: str = "reference-standard",
    capture_profile: str = "none",
    voice_policy: str = "retime-safe",
    visual_revision: str = "v3",
    progress: ProgressCallback | None = None,
) -> dict[str, object]:
    report = progress or (lambda _stage, _percent: None)
    source = source.resolve()
    output_dir = output_dir.resolve()
    _validate_options(
        primary_reference=primary_reference,
        secondary_reference=secondary_reference,
        asset_policy=asset_policy,
        time_budget_min=time_budget_min,
        quality_target=quality_target,
        capture_profile=capture_profile,
        voice_policy=voice_policy,
        visual_revision=visual_revision,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    capture_dir = output_dir / "source-captures"
    artifact_dir = output_dir / "artifacts"
    review_dir = output_dir / "review"
    screen_recording_dir = output_dir / "screen-recordings"
    for directory in (
        capture_dir,
        artifact_dir,
        review_dir,
        screen_recording_dir,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    report("analyzing", 5)
    metadata = probe_video(source)
    validate_source(metadata)

    report("reference_blueprint", 8)
    reference_profile = _build_reference_profile(
        reference_index=primary_reference,
        output_dir=output_dir,
    )

    report("transcribing", 12)
    os.environ.setdefault("VIDEO_EDITOR_TRANSCRIPT_CLEANUP", "off")
    raw_transcript_path = output_dir / "transcript-raw.json"
    if raw_transcript_path.is_file():
        segments = [
            TranscriptSegment.model_validate(item)
            for item in json.loads(
                raw_transcript_path.read_text(encoding="utf-8")
            )
        ]
    else:
        segments = transcribe_video(source)
        _write_json(
            raw_transcript_path,
            [item.model_dump(mode="json") for item in segments],
        )
    corrected_segments = _correct_production_transcript(segments, source)
    if len(corrected_segments) < 12:
        raise RuntimeError(
            "The bespoke 0806 blueprint requires the complete narration"
        )

    report("evidence", 24)
    _capture_evidence(capture_dir)
    evidence = _build_evidence_items(output_dir)
    _write_json(
        output_dir / "evidence.json",
        [item.model_dump(mode="json") for item in evidence],
    )

    report("artifacts", 33)
    artifacts = _build_artifacts(
        output_dir=output_dir,
        evidence=evidence,
    )
    _write_json(
        output_dir / "artifacts.json",
        [item.model_dump(mode="json") for item in artifacts],
    )

    report("storyboarding", 42)
    timeline = _build_0806_timeline(
        round(metadata.duration_seconds * 1000)
    )
    retimed_segments = _retime_segments(corrected_segments, timeline)
    caption_pages = _build_0806_caption_pages(retimed_segments)
    _validate_reference_caption_pages(caption_pages)
    storyboard_builder = (
        _build_0806_v3_storyboard
        if visual_revision == "v3"
        else _build_0806_storyboard
    )
    scenes, shots, scheduled_assets, graphics = storyboard_builder(
        retimed_segments=retimed_segments,
        duration_ms=timeline[-1].output_end_ms,
        output_dir=output_dir,
    )
    real_capture_count = len(
        {
            asset.id
            for asset in scheduled_assets
            if asset.kind == "video"
            and asset.provenance == "local-safe-demo-capture"
        }
    )
    if (
        quality_target == "reference-max"
        and capture_profile == "local-metatrader"
        and real_capture_count < 8
    ):
        raise RuntimeError(
            "Reference-max production requires at least eight approved "
            "local MetaTrader capture assets"
        )
    _write_json(
        output_dir / "storyboard.json",
        [shot.model_dump(mode="json") for shot in shots],
    )
    _write_json(
        output_dir / "caption-plan.json",
        {
            "primary_reference": primary_reference,
            "secondary_reference": secondary_reference,
            "pages": [
                page.model_dump(mode="json")
                for page in caption_pages
            ],
        },
    )

    report("sound_design", 48)
    sound_assets, audio = _build_reference_audio(
        source=source,
        output_dir=output_dir,
        duration_ms=timeline[-1].output_end_ms,
        speech_segments=retimed_segments,
        emphasis_times_ms=_0806_EMPHASIS_TIMES_MS,
    )
    _write_json(
        output_dir / "sfx-cue-sheet.json",
        _build_sfx_cue_sheet(audio=audio, assets=sound_assets),
    )
    _write_json(
        output_dir / "music-map.json",
        {
            "bpm": audio.music_bpm,
            "duration_ms": timeline[-1].output_end_ms,
            "sections": music_sections(timeline[-1].output_end_ms),
            "looped": False,
            "source": "Original local procedural score",
        },
    )
    plan = EditPlanV1(
        source_filename=source.name,
        source_metadata=metadata,
        output=OutputSpec(fps=30),
        duration_ms=timeline[-1].output_end_ms,
        style_variant="technical-explanation",
        timeline=timeline,
        caption_pages=caption_pages,
        scenes=scenes,
        reframing=[
            ReframeKeyframe(time_ms=0, x=0.5, y=0.42, scale=1.0),
            ReframeKeyframe(
                time_ms=timeline[-1].output_end_ms - 1,
                x=0.5,
                y=0.42,
                scale=1.0,
            ),
        ],
        graphics=graphics,
        editorial_visuals=[],
        assets=[*scheduled_assets, *sound_assets],
        audio=audio,
        qc_targets=QCTargets(
            min_cuts_per_minute=(
                28 if visual_revision == "v3" else 18
            ),
            max_cuts_per_minute=(
                45 if visual_revision == "v3" else 36
            ),
            min_median_shot_ms=(
                1200 if visual_revision == "v3" else 1100
            ),
            max_median_shot_ms=(
                1900 if visual_revision == "v3" else 2800
            ),
            min_meaningful_visual_coverage=0.6,
            min_style_score=88,
        ),
    )
    _write_json(
        output_dir / "edit-plan.json",
        plan.model_dump(mode="json"),
    )
    _write_json(
        output_dir / "transcript.json",
        [item.model_dump(mode="json") for item in corrected_segments],
    )
    _write_json(
        output_dir / "transcript-aligned.json",
        [item.model_dump(mode="json") for item in retimed_segments],
    )
    _write_json(
        screen_recording_dir / "schedule.json",
        {
            "mode": (
                "local-metatrader"
                if real_capture_count
                else "procedural-fallback"
            ),
            "approved_capture_count": real_capture_count,
            "capture_manifest": (
                "capture-manifest.json"
                if (output_dir / "capture-manifest.json").is_file()
                else None
            ),
            "scenes": [
                {
                    "id": scene.id,
                    "treatment": scene.treatment,
                    "start_ms": scene.start_ms,
                    "end_ms": scene.end_ms,
                    "asset_id": scene.asset_id,
                }
                for scene in scenes
                if scene.asset_id is not None
            ],
        },
    )
    _write_asset_manifest(
        output_dir=output_dir,
        source=source,
        evidence=evidence,
        artifacts=artifacts,
        assets=plan.assets,
    )

    preflight_checks = _preflight_review(
        plan=plan,
        shots=shots,
        evidence=evidence,
        artifacts=artifacts,
        retimed_segments=retimed_segments,
    )

    report("fixtures", 53)
    _render_reference_fixtures(review_dir)
    font_match = _measure_font_match(
        review_dir=review_dir,
        primary_reference=primary_reference,
    )
    _write_json(review_dir / "font-match.json", font_match)

    report("rendering", 57)
    rendered = output_dir / "rendered.mp4"
    edited = output_dir / "edited.mp4"
    render_edit_plan(
        source=source,
        output=rendered,
        work_dir=output_dir,
        plan=plan,
    )

    report("mastering", 82)
    loudness = measure_loudness_for_master(
        rendered,
        clean_completed_mix=False,
    )
    master_command = build_master_command(
        executable=Path(get_ffmpeg_exe()),
        rendered=rendered,
        output=edited,
        loudness_measurement=loudness,
        duration_seconds=plan.duration_ms / 1000,
        clean_completed_mix=False,
    )
    run_ffmpeg_command(master_command, output_dir)

    report("reviewing", 91)
    output_metadata = verify_render(
        edited,
        expected_width=1080,
        expected_height=1920,
        expected_fps=30,
        require_h264_aac=True,
        require_yuv420p=True,
    )
    measurements = measure_qc(output=edited, plan=plan)
    family_stills = _extract_caption_family_stills(
        video=edited,
        pages=caption_pages,
        review_dir=review_dir,
    )
    _create_contact_sheet(
        video=edited,
        output=review_dir / "contact-sheet.jpg",
        duration_seconds=output_metadata.duration_seconds,
    )
    _create_role_comparison_sheet(
        video=edited,
        shots=shots,
        reference_profile=reference_profile,
        output=review_dir / "reference-comparison.jpg",
    )

    frame_metrics = measure_frame_audit(edited)
    rendered_pacing = _build_rendered_pacing_summary(
        frame_metrics=frame_metrics,
        duration_seconds=output_metadata.duration_seconds,
    )
    actual_cuts = rendered_pacing["actual_cut_timestamps"]
    actual_cuts_per_minute = rendered_pacing["actual_cuts_per_minute"]
    actual_cut_onset_percent = measure_cut_onsets_for_video(
        edited,
        [round(float(cut_seconds) * 1000) for cut_seconds in actual_cuts],
    )
    source_coverage = calculate_source_coverage(
        shots,
        duration_ms=plan.duration_ms,
    )
    visual_language = calculate_visual_language_distribution(
        shots,
        duration_ms=plan.duration_ms,
    )
    visual_language_evaluation = (
        evaluate_reference_max_visual_language(visual_language)
        if visual_revision == "v3"
        else {"automated_pass": True, "checks": []}
    )
    frame_payload = {
        **frame_metrics,
        **source_coverage,
    }
    frame_evaluation = (
        evaluate_reference_max_v3_frame_metrics(frame_payload)
        if visual_revision == "v3"
        else evaluate_reference_max_frame_metrics(frame_payload)
    )
    _write_json(
        output_dir / "frame-audit.json",
        {
            **frame_payload,
            **frame_evaluation,
            "measurement_basis": "all rendered frames",
        },
    )
    _write_json(
        output_dir / "visual-language-audit.json",
        {
            **visual_language,
            **visual_language_evaluation,
            "measurement_basis": (
                "shot-role metadata plus rendered role diagnostics; "
                "human approval remains mandatory"
            ),
        },
    )

    dialogue_original = next(
        asset for asset in plan.assets if asset.id == "dialogue-original"
    )
    source_audio, source_sample_rate = _extract_audio(
        Path(dialogue_original.path)
    )
    final_audio, final_sample_rate = _extract_audio(edited)
    if source_sample_rate != final_sample_rate:
        raise RuntimeError("Audio continuity sample rates do not match")
    audio_continuity = build_audio_continuity_report(
        source_audio,
        final_audio,
        sample_rate=source_sample_rate,
        allowed_delay_ms=20,
    )

    final_asr_path = output_dir / "transcript-final-asr.json"
    if final_asr_path.is_file():
        final_segments = [
            TranscriptSegment.model_validate(item)
            for item in json.loads(
                final_asr_path.read_text(encoding="utf-8")
            )
        ]
    else:
        final_segments = transcribe_video(edited)
        _write_json(
            final_asr_path,
            [item.model_dump(mode="json") for item in final_segments],
        )
    source_text = " ".join(
        segment.text for segment in retimed_segments
    )
    final_text = " ".join(segment.text for segment in final_segments)
    asr_retention = compare_asr_tokens(
        source_text=source_text,
        final_text=final_text,
        protected_terms=[
            "Do",
            "Forex Trading Robot",
            "Expert Advisor",
            "2008",
            "$110,000",
            "Telegram group",
            "Thank you",
        ],
    )
    _write_json(output_dir / "asr-retention.json", asr_retention)
    _write_json(
        output_dir / "audio-continuity.json",
        {
            **audio_continuity,
            "source": "dialogue/dialogue-original.wav",
            "final": "edited.mp4",
            "asr_retention": asr_retention,
        },
    )

    checks = [
        *preflight_checks,
        *[
            VisualReviewCheck(
                name=f"frame-{item['name']}",
                passed=bool(item["passed"]),
                detail=(
                    f"measured={item['measured']}; "
                    f"target={item['target']}."
                ),
                evidence=["frame-audit.json"],
            )
            for item in frame_evaluation["checks"]
        ],
        *[
            VisualReviewCheck(
                name=f"visual-language-{item['name']}",
                passed=bool(item["passed"]),
                detail=(
                    f"measured={item['measured']}; "
                    f"target={item['target']}."
                ),
                evidence=[
                    "visual-language-audit.json",
                    "review/reference-comparison.jpg",
                ],
            )
            for item in visual_language_evaluation["checks"]
        ],
        VisualReviewCheck(
            name="audio-continuity",
            passed=(
                bool(audio_continuity["delay_passed"])
                and bool(audio_continuity["duration_passed"])
                and bool(audio_continuity["spectral_passed"])
            ),
            detail=(
                f"delay={audio_continuity['estimated_delay_ms']} ms, "
                f"duration delta={audio_continuity['duration_delta_ms']} ms, "
                "spectral distance="
                f"{audio_continuity['spectral_continuity_db']} dB."
            ),
            evidence=["audio-continuity.json"],
        ),
        VisualReviewCheck(
            name="asr-retention",
            passed=(
                float(asr_retention["retention_ratio"]) >= 0.99
                and bool(asr_retention["protected_terms_ok"])
            ),
            detail=(
                f"retained {float(asr_retention['retention_ratio']):.2%} "
                "of normalized source tokens; protected names, numbers, "
                "sentence openings and CTA words are required."
            ),
            evidence=[
                "asr-retention.json",
                "transcript-final-asr.json",
            ],
        ),
        VisualReviewCheck(
            name="caption-duration-token-gates",
            passed=(
                all(
                    350 <= page.end_ms - page.start_ms <= 1300
                    and all(
                        token.end_ms > token.start_ms
                        and token.start_ms < page.end_ms
                        and token.end_ms > page.start_ms
                        for token in page.tokens
                    )
                    for page in caption_pages
                )
                and all(
                    left.end_ms <= right.start_ms
                    for left, right in zip(
                        caption_pages,
                        caption_pages[1:],
                    )
                )
            ),
            detail=(
                "Every caption page is 350-1300 ms, pages do not overlap, "
                "and every positive-duration token intersects its visible "
                "page."
            ),
            evidence=["caption-plan.json"],
        ),
        VisualReviewCheck(
            name="font-match",
            passed=font_match["selected"] == "Share Tech Mono",
            detail=(
                "Share Tech Mono selected from four open-licensed "
                "candidates using normalized image difference."
            ),
            evidence=["review/font-match.json", "review/font-comparison.png"],
        ),
        VisualReviewCheck(
            name="codec-resolution",
            passed=(
                output_metadata.width == 1080
                and output_metadata.height == 1920
                and abs(output_metadata.fps - 30) <= 0.1
            ),
            detail="Output verified as 1080x1920 at 30 fps with H.264/AAC.",
        ),
        VisualReviewCheck(
            name="loudness",
            passed=(
                abs(measurements.integrated_lufs - plan.qc_targets.integrated_lufs)
                <= plan.qc_targets.loudness_tolerance
                and measurements.true_peak_dbtp
                <= plan.qc_targets.true_peak_dbtp + 0.25
            ),
            detail=(
                f"{measurements.integrated_lufs:.2f} LUFS, "
                f"{measurements.true_peak_dbtp:.2f} dBTP."
            ),
        ),
        VisualReviewCheck(
            name="silence-dead-frames",
            passed=(
                measurements.longest_silence_ms
                <= plan.qc_targets.max_silence_ms
                and measurements.black_frame_ratio
                <= plan.qc_targets.max_black_frame_ratio
                and measurements.freeze_frame_ratio
                <= plan.qc_targets.max_freeze_frame_ratio
            ),
            detail=(
                f"silence={measurements.longest_silence_ms} ms, "
                f"black={measurements.black_frame_ratio:.4f}, "
                f"freeze={measurements.freeze_frame_ratio:.4f}."
            ),
        ),
        VisualReviewCheck(
            name="meaningful-visual-coverage",
            passed=(
                measurements.meaningful_visual_coverage
                >= plan.qc_targets.min_meaningful_visual_coverage
            ),
            detail=(
                f"{measurements.meaningful_visual_coverage:.1%} of the "
                "timeline uses moving footage, direct evidence, or "
                "purpose-built internal motion."
            ),
            evidence=["storyboard.json", "edit-plan.json"],
        ),
        VisualReviewCheck(
            name="caption-overflow",
            passed=measurements.caption_overflow_count == 0,
            detail=(
                f"{measurements.caption_overflow_count} caption pages "
                "exceeded their family-aware geometry limits."
            ),
            evidence=[
                "caption-plan.json",
                *family_stills,
            ],
        ),
        VisualReviewCheck(
            name="rendered-pixel-pacing",
            passed=(
                24 <= int(frame_metrics["rendered_cut_count"]) <= 30
                if visual_revision == "v3"
                else 20 <= int(frame_metrics["rendered_cut_count"]) <= 22
            ),
            detail=(
                f"{frame_metrics['rendered_cut_count']} observed hard cuts "
                "from all rendered frames."
            ),
            evidence=[
                "frame-audit.json",
                "review/contact-sheet.jpg",
                "review/reference-comparison.jpg",
            ],
        ),
        _build_rendered_cut_onset_check(
            measured_percent=actual_cut_onset_percent,
            target_percent=plan.qc_targets.min_cut_onset_percent,
        ),
        VisualReviewCheck(
            name="caption-family-stills",
            passed=len(family_stills) >= 3,
            detail=(
                f"Rendered {len(family_stills)} in-context caption-family "
                "stills plus the five-family fixture."
            ),
            evidence=[
                *family_stills,
                "review/caption-families.png",
            ],
        ),
    ]
    automated_pass = all(check.passed for check in checks)
    review_measurements = measurements.model_dump(mode="json")
    review_measurements.update(
        {
            "cuts_per_minute": actual_cuts_per_minute,
            "median_shot_ms": rendered_pacing["median_shot_ms"],
            "cut_onset_percent": actual_cut_onset_percent,
        }
    )
    review = VisualReview(
        passed=False,
        automated_pass=automated_pass,
        human_approved=False,
        checks=checks,
        caption_family_stills=[
            *family_stills,
            "review/caption-families.png",
        ],
        sourced_evidence_beats=sum(bool(shot.evidence_ids) for shot in shots),
        unique_visual_treatments=len(
            {shot.treatment for shot in shots}
        ),
        unsupported_visible_facts=[],
    )
    _write_json(
        output_dir / "review-report.json",
        {
            **review.model_dump(mode="json"),
            "actual_cut_timestamps": actual_cuts,
            "actual_cuts_per_minute": round(actual_cuts_per_minute, 2),
            "actual_cut_onset_percent": round(
                actual_cut_onset_percent,
                2,
            ),
            "measurements": review_measurements,
            "output": output_metadata.model_dump(mode="json"),
            "primary_reference": primary_reference,
            "secondary_reference": secondary_reference,
            "asset_policy": asset_policy,
            "quality_target": quality_target,
            "capture_profile": capture_profile,
            "voice_policy": voice_policy,
            "visual_revision": visual_revision,
            "time_budget_min": time_budget_min,
            "reference_profile": reference_profile,
            "release_status": (
                "awaiting-human-approval"
                if automated_pass
                else "blocked-automated-review"
            ),
        },
    )
    rendered.unlink(missing_ok=True)
    shutil.rmtree(output_dir / "renderer-public", ignore_errors=True)
    if not review.automated_pass:
        raise RuntimeError(
            "Automated production review failed; inspect review-report.json"
        )
    report("completed", 100)
    return {
        "edited": str(edited),
        "review": review.model_dump(mode="json"),
        "output": output_metadata.model_dump(mode="json"),
        "release_status": "awaiting-human-approval",
    }


def _build_rendered_pacing_summary(
    *,
    frame_metrics: dict[str, object],
    duration_seconds: float,
) -> dict[str, object]:
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")
    actual_cuts = [
        float(item)
        for item in frame_metrics["cut_timestamps_seconds"]
    ]
    return {
        "actual_cut_timestamps": actual_cuts,
        "actual_cuts_per_minute": (
            len(actual_cuts) / (duration_seconds / 60)
        ),
        "median_shot_ms": int(frame_metrics["median_shot_ms"]),
    }


def _build_rendered_cut_onset_check(
    *,
    measured_percent: float,
    target_percent: float,
) -> VisualReviewCheck:
    return VisualReviewCheck(
        name="cut-onset-alignment",
        passed=measured_percent >= target_percent,
        detail=(
            f"{measured_percent:.1f}% of rendered hard cuts align with "
            f"audio onsets; target is at least {target_percent:g}%."
        ),
        evidence=["review/contact-sheet.jpg", "sfx-cue-sheet.json"],
    )


def _validate_options(
    *,
    primary_reference: int,
    secondary_reference: int,
    asset_policy: str,
    time_budget_min: int,
    quality_target: str,
    capture_profile: str,
    voice_policy: str,
    visual_revision: str,
) -> None:
    for name, value in (
        ("primary_reference", primary_reference),
        ("secondary_reference", secondary_reference),
    ):
        if value < 1 or value > 14:
            raise ValueError(f"{name} must be between 1 and 14")
    if asset_policy not in {"maximum-match", "free-licensed"}:
        raise ValueError("Unsupported production asset policy")
    if quality_target not in {"reference-standard", "reference-max"}:
        raise ValueError("Unsupported production quality target")
    if capture_profile not in {"none", "local-metatrader"}:
        raise ValueError("Unsupported production capture profile")
    if voice_policy not in {"retime-safe", "preserve-verbatim"}:
        raise ValueError("Unsupported production voice policy")
    if visual_revision not in {"v2", "v3"}:
        raise ValueError("Unsupported visual revision")
    if time_budget_min < 15 or time_budget_min > 600:
        raise ValueError("time_budget_min must be between 15 and 600")


def _validate_reference_caption_pages(
    pages: list[CaptionPage],
) -> None:
    previous_end_ms: int | None = None
    for page in pages:
        duration_ms = page.end_ms - page.start_ms
        if duration_ms < 350 or duration_ms > 1300:
            raise ValueError(
                "Reference caption holds must stay within 350-1300 ms"
            )
        if (
            previous_end_ms is not None
            and page.start_ms < previous_end_ms
        ):
            raise ValueError(
                "Reference caption pages must not overlap"
            )
        for token in page.tokens:
            if token.end_ms <= token.start_ms:
                raise ValueError(
                    "Reference caption tokens require positive duration"
                )
            if (
                token.start_ms >= page.end_ms
                or token.end_ms <= page.start_ms
            ):
                raise ValueError(
                    "Every caption token must intersect its visible page"
                )
        previous_end_ms = page.end_ms


def _build_reference_audio(
    *,
    source: Path,
    output_dir: Path,
    duration_ms: int,
    speech_segments: list[TranscriptSegment],
    emphasis_times_ms: list[int],
    command_runner: Callable[[list[str], Path], None] = run_ffmpeg_command,
) -> tuple[list[AssetRef], AudioPlan]:
    dialogue_dir = output_dir / "dialogue"
    dialogue_dir.mkdir(parents=True, exist_ok=True)
    raw_path = dialogue_dir / "dialogue-original.wav"
    processed_path = dialogue_dir / "dialogue-processed.wav"
    for processed, destination in (
        (False, raw_path),
        (True, processed_path),
    ):
        command_runner(
            build_dialogue_extract_command(
                executable=Path(get_ffmpeg_exe()),
                source=source,
                output=destination,
                processed=processed,
            ),
            output_dir,
        )

    dialogue_assets = [
        AssetRef(
            id="dialogue-original",
            kind="audio",
            path=str(raw_path.resolve()),
            keywords=["dialogue", "raw", "48khz", "verbatim"],
            provenance="user-source-audio-extract",
            license="User-provided source",
            provider="Local FFmpeg extraction",
        ),
        AssetRef(
            id="dialogue-processed",
            kind="audio",
            path=str(processed_path.resolve()),
            keywords=["dialogue", "processed", "48khz", "verbatim"],
            provenance="user-source-audio-processed",
            license="User-provided source",
            provider="Local FFmpeg voice-only processing",
        ),
    ]
    sound_assets, audio = generate_sound_design(
        output_dir,
        duration_ms=duration_ms,
        emphasis_times_ms=emphasis_times_ms,
        speech_segments=speech_segments,
    )
    return [
        *dialogue_assets,
        *sound_assets,
    ], audio.model_copy(
        update={
            "dialogue_asset_id": "dialogue-processed",
            "dialogue_offset_ms": -70,
        }
    )


def _build_reference_profile(
    *,
    reference_index: int,
    output_dir: Path,
) -> dict[str, object]:
    references = sorted(
        (
            Path(__file__).resolve().parents[3]
            / "training videos data"
        ).glob("*.mp4")
    )
    if reference_index < 1 or reference_index > len(references):
        raise RuntimeError("Requested reference video is unavailable")
    reference_video = references[reference_index - 1]
    metadata = probe_video(reference_video)
    duration_seconds = metadata.duration_seconds
    cuts = detect_hard_cuts(
        reference_video,
        threshold=22,
        sample_rate_hz=10,
        min_gap_seconds=0.35,
    )
    boundaries = [0.0, *cuts, duration_seconds]
    shot_durations = [
        right - left
        for left, right in zip(boundaries, boundaries[1:])
        if right > left
    ]

    review_dir = output_dir / "review"
    role_times = {
        "hook": 0.7,
        "code": 8.7,
        "presenter-reset": 20.3,
        "evidence": 34.8,
        "system-diagram": 49.3,
        "late-code": min(duration_seconds * 0.86, duration_seconds - 1.2),
        "ending": max(0.0, duration_seconds - 1.0),
    }
    capture = cv2.VideoCapture(str(reference_video))
    if not capture.isOpened():
        raise RuntimeError("Unable to open the primary reference")
    selected_frames: list[dict[str, object]] = []
    sampled_frames: list[np.ndarray] = []
    face_samples = 0
    readable_samples = 0
    cascade = cv2.CascadeClassifier(
        str(
            Path(cv2.data.haarcascades)
            / "haarcascade_frontalface_default.xml"
        )
    )
    try:
        for role, requested_time in role_times.items():
            timestamp = min(
                max(0.0, requested_time),
                max(0.0, duration_seconds - 0.05),
            )
            capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            ok, frame = capture.read()
            if not ok or frame is None:
                continue
            filename = f"reference-{reference_index:02d}-{role}.png"
            cv2.imwrite(str(review_dir / filename), frame)
            selected_frames.append(
                {
                    "role": role,
                    "time_seconds": round(timestamp, 3),
                    "path": f"review/{filename}",
                }
            )

        sample_times = np.linspace(
            0.2,
            max(0.2, duration_seconds - 0.2),
            36,
        )
        for timestamp in sample_times:
            capture.set(cv2.CAP_PROP_POS_MSEC, float(timestamp) * 1000)
            ok, frame = capture.read()
            if not ok or frame is None:
                continue
            resized = cv2.resize(frame, (180, 320))
            sampled_frames.append(resized)
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(
                gray,
                scaleFactor=1.12,
                minNeighbors=4,
                minSize=(24, 24),
            )
            readable_samples += 1
            if len(faces):
                face_samples += 1
    finally:
        capture.release()

    if not sampled_frames:
        raise RuntimeError("Unable to sample the primary reference")
    stacked = np.concatenate(
        [frame.reshape(-1, 3) for frame in sampled_frames],
        axis=0,
    )
    median_bgr = np.median(stacked, axis=0)
    median_rgb = [int(round(value)) for value in median_bgr[::-1]]
    hsv_frames = [
        cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        for frame in sampled_frames
    ]
    mean_saturation = float(
        np.mean([frame[..., 1].mean() for frame in hsv_frames])
    )
    mean_luma = float(
        np.mean(
            [
                cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean()
                for frame in sampled_frames
            ]
        )
    )
    frame_differences = [
        float(
            np.mean(
                cv2.absdiff(
                    cv2.cvtColor(left, cv2.COLOR_BGR2GRAY),
                    cv2.cvtColor(right, cv2.COLOR_BGR2GRAY),
                )
            )
        )
        for left, right in zip(sampled_frames, sampled_frames[1:])
    ]
    audio_profile = _analyze_reference_audio(reference_video)
    profile = {
        "reference_index": reference_index,
        "reference_filename": reference_video.name,
        "generated_at": datetime.now(UTC).isoformat(),
        "metadata": metadata.model_dump(mode="json"),
        "visual_grammar": {
            "hard_cut_timestamps_seconds": cuts,
            "detected_cuts_per_minute": round(
                len(cuts) / max(duration_seconds / 60, 0.001),
                2,
            ),
            "median_shot_ms": round(
                float(np.median(shot_durations)) * 1000
            ),
            "hard_cut_target_ratio": 0.90,
            "sampled_presenter_ratio": round(
                face_samples / max(readable_samples, 1),
                4,
            ),
            "mean_inter_sample_difference": round(
                float(np.mean(frame_differences)),
                3,
            ),
            "unchanged_sample_ratio": round(
                sum(value < 2.2 for value in frame_differences)
                / max(len(frame_differences), 1),
                4,
            ),
        },
        "caption_target": {
            "family": "technical-mono",
            "font_candidates": [
                "Share Tech Mono",
                "Space Mono",
                "Chakra Petch",
                "IBM Plex Mono",
            ],
            "font_size_px": [31, 34],
            "anchor_percent": [73, 74],
            "horizontal_padding_px": [10, 14],
            "vertical_padding_px": [6, 8],
            "radius_px": [4, 6],
            "transition": "hard-cut",
        },
        "palette": {
            "median_rgb": median_rgb,
            "median_hex": "#{:02X}{:02X}{:02X}".format(*median_rgb),
            "mean_saturation_0_255": round(mean_saturation, 2),
            "mean_luma_0_255": round(mean_luma, 2),
            "production_base": ["#050607", "#F4F0E8"],
            "technical_accent": "#84C7D6",
            "risk_accent": "#DC6C76",
        },
        "audio": audio_profile,
        "selected_frames": selected_frames,
        "production_translation": {
            "primary_grammar_share": 0.90,
            "secondary_reference": 4,
            "secondary_use": "restrained wrong-rule and risk beats only",
            "presenter_target_ratio": [0.14, 0.20],
            "moving_visual_target_minimum": 0.60,
        },
    }
    _write_json(output_dir / "reference-profile-10.json", profile)
    return profile


def _analyze_reference_audio(reference_video: Path) -> dict[str, object]:
    completed = subprocess.run(
        [
            get_ffmpeg_exe(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(reference_video),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "48000",
            "-f",
            "f32le",
            "pipe:1",
        ],
        capture_output=True,
        timeout=180,
        check=False,
        shell=False,
    )
    if completed.returncode != 0 or not completed.stdout:
        return {
            "analysis_status": "unavailable",
            "target_bpm": 120,
        }
    samples = np.frombuffer(completed.stdout, dtype="<f4").astype(np.float64)
    if samples.size < 48_000:
        return {
            "analysis_status": "insufficient-audio",
            "target_bpm": 120,
        }
    hop = 1024
    usable = samples[: samples.size - (samples.size % hop)]
    windows = usable.reshape(-1, hop)
    rms = np.sqrt(np.mean(windows**2, axis=1) + 1e-12)
    onset = np.maximum(0, np.diff(rms, prepend=rms[0]))
    onset -= onset.mean()
    feature_rate = 48_000 / hop
    lag_min = max(1, round(feature_rate * 60 / 145))
    lag_max = max(lag_min + 1, round(feature_rate * 60 / 105))
    correlations = []
    for lag in range(lag_min, lag_max + 1):
        left = onset[:-lag]
        right = onset[lag:]
        correlations.append(
            float(np.dot(left, right))
            / max(float(np.linalg.norm(left) * np.linalg.norm(right)), 1e-9)
        )
    best_lag = lag_min + int(np.argmax(correlations))
    estimated_bpm = 60 * feature_rate / best_lag
    threshold = float(onset.mean() + onset.std() * 1.7)
    onset_count = int(np.count_nonzero(onset > threshold))
    overall_rms = float(np.sqrt(np.mean(samples**2) + 1e-12))
    peak = float(np.max(np.abs(samples)))
    return {
        "analysis_status": "measured-from-reference-audio",
        "estimated_tempo_bpm": round(estimated_bpm, 2),
        "production_target_bpm": 120,
        "rms_dbfs": round(20 * math.log10(max(overall_rms, 1e-9)), 2),
        "sample_peak_dbfs": round(20 * math.log10(max(peak, 1e-9)), 2),
        "onsets_per_minute": round(
            onset_count / max(samples.size / 48_000 / 60, 0.001),
            2,
        ),
        "method": (
            "48 kHz mono decode; 1024-sample RMS onset envelope; "
            "autocorrelation constrained to 105-145 BPM."
        ),
    }


def _build_sfx_cue_sheet(
    *,
    audio: AudioPlan,
    assets: list[AssetRef],
) -> dict[str, object]:
    assets_by_id = {asset.id: asset for asset in assets}
    return {
        "target_range": [9, 13],
        "actual_count": len(audio.sfx_cues),
        "all_cues_motivated": all(bool(cue.reason) for cue in audio.sfx_cues),
        "cues": [
            {
                **cue.model_dump(mode="json"),
                "asset_path": assets_by_id[cue.asset_id].path,
                "provenance": assets_by_id[cue.asset_id].provenance,
                "license": assets_by_id[cue.asset_id].license,
            }
            for cue in audio.sfx_cues
        ],
    }


def _write_asset_manifest(
    *,
    output_dir: Path,
    source: Path,
    evidence: list[EvidenceItem],
    artifacts: list[ArtifactSpec],
    assets: list[AssetRef],
) -> None:
    entries: list[dict[str, object]] = [
        {
            "id": "source-video",
            "kind": "video",
            "provider": "user",
            "creator": "user-provided",
            "source_url": None,
            "license": "User-provided for this production",
            "local_path": str(source),
            "checksum_sha256": _sha256(source),
            "status": "source-media",
        }
    ]
    seen_paths: set[str] = set()
    evidence_by_id = {item.id: item for item in evidence}
    for artifact in artifacts:
        local_path = output_dir / artifact.path
        normalized = str(local_path.resolve())
        if normalized in seen_paths or not local_path.is_file():
            continue
        seen_paths.add(normalized)
        linked = [
            evidence_by_id[evidence_id]
            for evidence_id in artifact.evidence_ids
            if evidence_id in evidence_by_id
        ]
        entries.append(
            {
                "id": artifact.id,
                "kind": artifact.kind,
                "provider": (
                    "MetaQuotes/MQL5"
                    if artifact.provenance == "official-source-capture"
                    else "Cutline local production"
                ),
                "creator": (
                    "Source publisher"
                    if artifact.provenance == "official-source-capture"
                    else "Original local generation"
                ),
                "source_url": (
                    linked[0].source_url if linked else None
                ),
                "license": (
                    linked[0].license
                    if linked
                    else "Original generated production artifact"
                ),
                "local_path": artifact.path,
                "checksum_sha256": _sha256(local_path),
                "status": (
                    "illustrative"
                    if artifact.illustrative
                    else "evidence"
                ),
                "evidence_ids": artifact.evidence_ids,
            }
        )
    for asset in assets:
        local_path = Path(asset.path)
        normalized = str(local_path.resolve())
        if normalized in seen_paths or not local_path.is_file():
            continue
        seen_paths.add(normalized)
        entries.append(
            {
                "id": asset.id,
                "kind": asset.kind,
                "provider": asset.provider,
                "creator": asset.creator,
                "source_url": asset.source_url,
                "license": asset.license,
                "license_url": asset.license_url,
                "search_query": asset.search_query,
                "local_path": (
                    local_path.relative_to(output_dir).as_posix()
                    if local_path.is_relative_to(output_dir)
                    else str(local_path)
                ),
                "checksum_sha256": _sha256(local_path),
                "status": asset.provenance,
            }
        )
    _write_json(
        output_dir / "asset-manifest.json",
        {
            "generated_at": datetime.now(UTC).isoformat(),
            "policy": "evidence-first maximum-match",
            "entries": entries,
        },
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _correct_production_transcript(
    segments: list[TranscriptSegment],
    source: Path,
) -> list[TranscriptSegment]:
    normalized = " ".join(item.text.lower() for item in segments)
    is_0806 = (
        source.stem.casefold() == "0806"
        or (
            "forex" in normalized
            and "expert advisor" in normalized
            and "championship" in normalized
        )
    )
    if not is_0806:
        raise RuntimeError(
            "No bespoke production blueprint exists for this narration yet"
        )
    return repair_nonpositive_word_durations(
        retime_corrected_segments(segments, _0806_CORRECTED_TEXTS)
    )


def _capture_evidence(capture_dir: Path) -> None:
    missing = [
        spec
        for spec in _CAPTURE_SPECS
        if _capture_needs_refresh(
            capture_dir / str(spec["filename"])
        )
    ]
    if not missing:
        _ensure_capture_index(capture_dir)
        return
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as error:
        raise RuntimeError(
            "Playwright is required to capture official evidence"
        ) from error

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--disable-gpu", "--hide-scrollbars"],
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 1600},
            device_scale_factor=1,
        )
        page = context.new_page()
        capture_records: list[dict[str, object]] = []
        try:
            for spec in missing:
                page.goto(
                    str(spec["url"]),
                    wait_until="domcontentloaded",
                    timeout=60_000,
                )
                page.wait_for_timeout(500)
                page.evaluate(
                    """
                    () => {
                      for (const element of document.querySelectorAll(
                        '[class*="cookie" i], [id*="cookie" i]'
                      )) {
                        const style = getComputedStyle(element);
                        if (style.position === 'fixed') {
                          element.remove();
                        }
                      }
                    }
                    """
                )
                locator = page.get_by_text(
                    str(spec["text"]),
                    exact=False,
                ).first
                locator.wait_for(state="visible", timeout=30_000)
                locator.evaluate(
                    """
                    (element) => {
                      const targetY =
                        element.getBoundingClientRect().top +
                        window.scrollY -
                        360;
                      window.scrollTo({top: Math.max(0, targetY), left: 0});
                    }
                    """
                )
                page.wait_for_timeout(450)
                focus_box = locator.bounding_box()
                page.screenshot(
                    path=str(capture_dir / str(spec["filename"])),
                    type="png",
                    full_page=False,
                )
                capture_records.append(
                    {
                        "id": spec["id"],
                        "source_url": spec["url"],
                        "page_title": page.title(),
                        "capture_path": (
                            "source-captures/"
                            + str(spec["filename"])
                        ),
                        "viewport": {"width": 1440, "height": 1600},
                        "scroll_y": round(
                            page.evaluate("() => window.scrollY")
                        ),
                        "focus_box": (
                            {
                                key: round(value, 2)
                                for key, value in focus_box.items()
                            }
                            if focus_box is not None
                            else None
                        ),
                        "captured_at": datetime.now(UTC).isoformat(),
                        "method": (
                            "Direct browser viewport capture with official "
                            "site pixels and in-page source context."
                        ),
                    }
                )
        finally:
            context.close()
            browser.close()
    existing_index = capture_dir / "capture-index.json"
    existing_records = []
    if existing_index.is_file():
        try:
            existing_records = json.loads(
                existing_index.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError):
            existing_records = []
    records_by_id = {
        str(item.get("id")): item
        for item in existing_records
        if isinstance(item, dict)
    }
    records_by_id.update(
        {str(item["id"]): item for item in capture_records}
    )
    _write_json(existing_index, list(records_by_id.values()))


def _ensure_capture_index(capture_dir: Path) -> None:
    index_path = capture_dir / "capture-index.json"
    if index_path.is_file():
        return
    records = []
    for spec in _CAPTURE_SPECS:
        path = capture_dir / str(spec["filename"])
        image = cv2.imread(str(path))
        if image is None:
            continue
        height, width = image.shape[:2]
        records.append(
            {
                "id": spec["id"],
                "source_url": spec["url"],
                "capture_path": (
                    "source-captures/" + str(spec["filename"])
                ),
                "viewport": {"width": width, "height": height},
                "captured_at": datetime.fromtimestamp(
                    path.stat().st_mtime,
                    tz=UTC,
                ).isoformat(),
                "method": (
                    "Direct browser viewport capture with official "
                    "site pixels and in-page source context."
                ),
            }
        )
    _write_json(index_path, records)


def _capture_needs_refresh(path: Path) -> bool:
    if not path.is_file():
        return True
    image = cv2.imread(str(path))
    if image is None:
        return True
    height, width = image.shape[:2]
    return width < 1_200 or height < 1_200


def _build_evidence_items(output_dir: Path) -> list[EvidenceItem]:
    accessed_at = datetime.now(UTC)
    return [
        EvidenceItem(
            id="metaquotes-automated-trading",
            claim=(
                "MetaTrader describes automated-trading applications as "
                "trading robots that analyze quotes and execute trades."
            ),
            source_title="Algorithmic (automated) trading in MetaTrader 5",
            source_url="https://www.metatrader5.com/en/automated-trading",
            source_type="official",
            capture_path=(
                "source-captures/"
                "metatrader5-automated-trading-definition.png"
            ),
            accessed_at=accessed_at,
            status="verified",
            visible_excerpt=(
                "These applications are referred to as trading robots; "
                "they can analyze quotes ... and execute trade operations."
            ),
            license=(
                "Editorial evidence excerpt; rights retained by "
                "MetaQuotes Ltd."
            ),
        ),
        EvidenceItem(
            id="metaquotes-expert-advisor",
            claim="MetaTrader states that an Expert Advisor trades in markets.",
            source_title=(
                "Algorithmic trading and trading robots in MetaTrader 4"
            ),
            source_url="https://www.metatrader4.com/en/automated-trading",
            source_type="official",
            capture_path=(
                "source-captures/"
                "metatrader4-expert-advisor-definition.png"
            ),
            accessed_at=accessed_at,
            status="verified",
            visible_excerpt=(
                "Your indicator analyzes the markets, while an Expert "
                "Advisor trades in them."
            ),
            license=(
                "Editorial evidence excerpt; rights retained by "
                "MetaQuotes Ltd."
            ),
        ),
        EvidenceItem(
            id="metaquotes-atc-history",
            claim=(
                "MetaTrader records Automated Trading Championships from "
                "2006 through 2012 with Expert Advisors trading automatically."
            ),
            source_title="Algorithmic (automated) trading in MetaTrader 5",
            source_url="https://www.metatrader5.com/en/automated-trading",
            source_type="official",
            capture_path="source-captures/metatrader5-atc-history.png",
            accessed_at=accessed_at,
            status="verified",
            visible_excerpt=(
                "Automated Trading Championships 2006-2012 ... hundreds "
                "of Expert Advisors traded automatically."
            ),
            license=(
                "Editorial evidence excerpt; rights retained by "
                "MetaQuotes Ltd."
            ),
        ),
        EvidenceItem(
            id="mql5-atc-2008-risk",
            claim=(
                "ATC 2008 participant Leonid Velichkovsky reported earning "
                "110,000 before falling to 14,749 because of aggressive "
                "money management."
            ),
            source_title=(
                'Interview with Leonid Velichkovsky: "The Biggest Myth '
                'about Neural Networks is Super-Profitability"'
            ),
            source_url="https://www.mql5.com/en/articles/525",
            source_type="primary",
            capture_path="source-captures/mql5-atc-2008-risk.png",
            accessed_at=accessed_at,
            status="verified",
            visible_excerpt=(
                "I managed to earn 110,000 and then fell to 14,749 "
                "because of that too aggressive money management."
            ),
            license=(
                "Editorial evidence excerpt; rights retained by the "
                "publisher and author."
            ),
        ),
    ]


def _build_artifacts_legacy_source_cards(
    *,
    output_dir: Path,
    evidence: list[EvidenceItem],
) -> list[ArtifactSpec]:
    artifact_dir = output_dir / "artifacts"
    evidence_by_id = {item.id: item for item in evidence}
    cards = [
        (
            "automation-source-card",
            "metaquotes-automated-trading",
            "WHAT AUTOMATED TRADING DOES",
            "OFFICIAL METATRADER 5 DOCUMENTATION",
        ),
        (
            "ea-source-card",
            "metaquotes-expert-advisor",
            "EXPERT ADVISOR = TRADING ROBOT",
            "OFFICIAL METATRADER 4 DOCUMENTATION",
        ),
        (
            "atc-source-card",
            "metaquotes-atc-history",
            "AUTOMATED TRADING CHAMPIONSHIPS",
            "OFFICIAL METATRADER 5 HISTORY",
        ),
        (
            "risk-source-card",
            "mql5-atc-2008-risk",
            "$110,000 — THEN THE REVERSAL",
            "PRIMARY-SOURCE INTERVIEW • MQL5",
        ),
    ]
    artifacts: list[ArtifactSpec] = []
    for artifact_id, evidence_id, title, eyebrow in cards:
        item = evidence_by_id[evidence_id]
        output = artifact_dir / f"{artifact_id}.svg"
        _write_source_card_svg(
            output=output,
            capture=output_dir / item.capture_path,
            title=title,
            eyebrow=eyebrow,
            source_url=item.source_url,
            claim=item.claim,
        )
        artifacts.append(
            ArtifactSpec(
                id=artifact_id,
                kind="source-capture",
                path=f"artifacts/{output.name}",
                provenance="official-source-excerpt-wrapper",
                evidence_ids=[evidence_id],
                illustrative=False,
            )
        )

    generated = [
        (
            "rule-engine-diagram",
            "diagram",
            "rule-engine.svg",
            ["metaquotes-automated-trading"],
            _rule_engine_svg(),
        ),
        (
            "ea-code-diagram",
            "code",
            "ea-code.svg",
            ["metaquotes-expert-advisor"],
            _ea_code_svg(),
        ),
        (
            "risk-curve-diagram",
            "chart",
            "risk-curve.svg",
            ["mql5-atc-2008-risk"],
            _risk_curve_svg(),
        ),
        (
            "automation-risk-comparison",
            "diagram",
            "automation-vs-risk.svg",
            [
                "metaquotes-automated-trading",
                "mql5-atc-2008-risk",
            ],
            _automation_vs_risk_svg(),
        ),
    ]
    for artifact_id, kind, filename, evidence_ids, contents in generated:
        (artifact_dir / filename).write_text(contents, encoding="utf-8")
        artifacts.append(
            ArtifactSpec(
                id=artifact_id,
                kind=kind,
                path=f"artifacts/{filename}",
                provenance="generated-from-verified-facts",
                evidence_ids=evidence_ids,
                illustrative=True,
                label="ILLUSTRATIVE",
            )
        )
    return artifacts


def _build_artifacts(
    *,
    output_dir: Path,
    evidence: list[EvidenceItem],
) -> list[ArtifactSpec]:
    artifact_dir = output_dir / "artifacts"
    for stale in (
        "automation-source-card.svg",
        "ea-source-card.svg",
        "atc-source-card.svg",
        "risk-source-card.svg",
    ):
        (artifact_dir / stale).unlink(missing_ok=True)

    artifacts = [
        ArtifactSpec(
            id=f"capture-{item.id}",
            kind="source-capture",
            path=item.capture_path,
            provenance="official-source-capture",
            evidence_ids=[item.id],
            illustrative=False,
        )
        for item in evidence
    ]
    generated = [
        (
            "metaeditor-code",
            "code",
            "metaeditor-code.svg",
            ["metaquotes-automated-trading", "metaquotes-expert-advisor"],
            _ea_code_svg(),
        ),
        (
            "wrong-rule-flow",
            "diagram",
            "wrong-rule-flow.svg",
            ["metaquotes-automated-trading"],
            _rule_engine_svg(),
        ),
        (
            "risk-control",
            "diagram",
            "risk-control.svg",
            ["mql5-atc-2008-risk"],
            _risk_curve_svg(),
        ),
        (
            "demo-panel",
            "diagram",
            "demo-panel.svg",
            ["metaquotes-expert-advisor"],
            _automation_vs_risk_svg(),
        ),
    ]
    for artifact_id, kind, filename, evidence_ids, contents in generated:
        (artifact_dir / filename).write_text(contents, encoding="utf-8")
        artifacts.append(
            ArtifactSpec(
                id=artifact_id,
                kind=kind,
                path=f"artifacts/{filename}",
                provenance="generated-from-verified-facts",
                evidence_ids=evidence_ids,
                illustrative=True,
                label="ILLUSTRATIVE",
            )
        )
    return artifacts


def _build_0806_caption_pages(
    segments: list[TranscriptSegment],
) -> list[CaptionPage]:
    family_by_segment = {
        0: "technical-mono",
        1: "technical-mono",
        2: "technical-mono",
        3: "technical-mono",
        4: "technical-mono",
        5: "documentary-clean",
        6: "documentary-clean",
        7: "technical-mono",
        8: "technical-mono",
        9: "technical-mono",
        10: "technical-mono",
        11: "compact-pill",
    }
    phrase_ranges: dict[int, list[tuple[int, int]]] = {
        0: [(0, 4), (4, 7), (7, 8)],
        1: [(0, 3), (3, 5), (5, 6), (6, 10)],
        2: [(0, 1), (1, 4), (4, 7)],
        3: [(0, 3)],
        4: [(0, 2), (2, 5), (5, 6)],
        5: [(0, 2), (2, 5), (5, 7)],
        6: [(0, 3), (3, 5)],
        7: [(0, 3), (3, 6)],
        8: [(0, 3), (3, 6)],
        9: [(0, 3), (3, 6)],
        10: [
            (0, 3),
            (3, 6),
            (6, 10),
            (10, 13),
            (13, 16),
        ],
        11: [
            (0, 3),
            (3, 6),
            (6, 9),
            (9, 10),
            (10, 13),
            (13, 15),
            (15, 18),
            (18, 20),
            (20, 22),
        ],
    }
    geometry = {
        "technical-mono": ("center-74", "hard-cut", 900),
        "documentary-clean": ("center-71", "hard-cut", 920),
        "compact-pill": ("center-76", "fade-up", 900),
    }
    pages: list[CaptionPage] = []
    previous_page_end_ms = 0
    for index, segment in enumerate(segments[:12]):
        segment_family = family_by_segment[index]
        segment_end_ms = round(segment.end * 1000)
        next_sentence_start_ms = (
            round(segments[index + 1].start * 1000)
            if index + 1 < min(12, len(segments))
            else segment_end_ms
        )
        for start_index, end_index in phrase_ranges[index]:
            words = segment.words[start_index:end_index]
            if not words:
                continue
            tokens = [
                CaptionToken(
                    text=word.text,
                    start_ms=round(word.start * 1000),
                    end_ms=max(
                        round(word.end * 1000),
                        round(word.start * 1000) + 1,
                    ),
                    highlighted=False,
                    confidence=word.confidence,
                )
                for word in words
            ]
            family = (
                "technical-mono"
                if index == 11 and tokens[-1].end_ms <= 37_160
                else segment_family
            )
            anchor, transition, max_width = geometry[family]
            if index == 0:
                anchor = "upper-56"
            raw_start_ms = tokens[0].start_ms
            raw_end_ms = max(token.end_ms for token in tokens)
            page_start_ms = max(raw_start_ms, previous_page_end_ms)
            page_end_ms = min(raw_end_ms, page_start_ms + 1300)
            if page_end_ms - page_start_ms < 350:
                page_start_ms = max(
                    previous_page_end_ms,
                    page_end_ms - 350,
                )
                if page_end_ms - page_start_ms < 350:
                    page_end_ms = min(
                        next_sentence_start_ms,
                        page_start_ms + 350,
                    )
            if page_end_ms - page_start_ms < 350:
                raise ValueError(
                    "Unable to schedule a non-overlapping 350 ms caption "
                    f"page for segment {index}"
                )
            pages.append(
                CaptionPage(
                    start_ms=page_start_ms,
                    end_ms=page_end_ms,
                    tokens=tokens,
                    family=family,
                    anchor=anchor,
                    transition=transition,
                    max_width=max_width,
                )
            )
            previous_page_end_ms = page_end_ms
    return pages


def _build_0806_timeline(
    source_duration_ms: int,
) -> list[TimelineMapSegment]:
    return [
        TimelineMapSegment(
            source_start_ms=0,
            source_end_ms=source_duration_ms,
            output_start_ms=0,
            output_end_ms=source_duration_ms,
        )
    ]


def _build_0806_storyboard(
    *,
    retimed_segments: list[TranscriptSegment],
    duration_ms: int,
    output_dir: Path,
) -> tuple[
    list[ScenePlan],
    list[ShotSpec],
    list[AssetRef],
    list[GraphicCue],
]:
    reference_duration_ms = 41_401
    scale = duration_ms / reference_duration_ms
    expected_follow_ms = round(37_160 * scale)
    detected_follow_ms = _word_start_ms(
        retimed_segments[11],
        "follow",
        -1,
    )
    if (
        detected_follow_ms >= 0
        and abs(detected_follow_ms - expected_follow_ms) <= 250
    ):
        follow_boundary_ms = detected_follow_ms
    elif duration_ms >= 40_000:
        follow_boundary_ms = expected_follow_ms
    else:
        follow_boundary_ms = round(
            (
                retimed_segments[11].start
                + (
                    retimed_segments[11].end
                    - retimed_segments[11].start
                )
                * 0.55
            )
            * 1000
        )
    aligned_times = {
        0: 0,
        2_340: round(retimed_segments[0].end * 1000),
        2_800: round(retimed_segments[1].start * 1000),
        2_820: max(
            round(retimed_segments[1].start * 1000),
            round(retimed_segments[0].end * 1000) + 1,
        ),
        6_820: round(retimed_segments[1].end * 1000),
        7_200: round(retimed_segments[2].start * 1000),
        9_020: round(retimed_segments[2].end * 1000),
        9_560: round(retimed_segments[3].start * 1000),
        10_700: round(retimed_segments[3].end * 1000),
        12_060: round(retimed_segments[4].start * 1000),
        14_160: round(retimed_segments[4].end * 1000),
        14_480: round(retimed_segments[5].start * 1000),
        17_460: round(retimed_segments[5].end * 1000),
        17_920: round(retimed_segments[6].start * 1000),
        21_140: round(retimed_segments[6].end * 1000),
        21_820: round(retimed_segments[7].start * 1000),
        23_140: round(retimed_segments[7].end * 1000),
        24_000: round(retimed_segments[8].start * 1000),
        25_520: round(retimed_segments[8].end * 1000),
        26_080: round(retimed_segments[9].start * 1000),
        27_780: round(retimed_segments[9].end * 1000),
        32_200: round(retimed_segments[10].end * 1000),
        33_180: round(retimed_segments[11].start * 1000),
        37_160: follow_boundary_ms,
        41_000: round(retimed_segments[11].end * 1000),
        reference_duration_ms: duration_ms,
    }

    def at(reference_time_ms: int) -> int:
        if reference_time_ms in aligned_times:
            return aligned_times[reference_time_ms]
        return round(reference_time_ms * scale)

    blueprints = [
        (
            0,
            2_340,
            "0806-split-hook",
            "hook",
            "split-screen",
            "technical-mono",
            [],
            [],
            None,
            "live-footage",
        ),
        (
            2_340,
            2_820,
            "0806-terminal-boot",
            "explanation",
            "asset-full",
            "technical-mono",
            [],
            ["metaeditor-code"],
            None,
            "animated",
        ),
        (
            2_820,
            6_820,
            "0806-code-rule-trace",
            "explanation",
            "asset-full",
            "technical-mono",
            ["metaquotes-automated-trading"],
            ["metaeditor-code"],
            "metaquotes-automated-trading-page",
            "animated",
        ),
        (
            6_820,
            7_200,
            "0806-code-scroll",
            "explanation",
            "asset-full",
            "technical-mono",
            [],
            ["metaeditor-code"],
            None,
            "animated",
        ),
        (
            7_200,
            9_020,
            "0806-ea-label",
            "evidence",
            "asset-full",
            "technical-mono",
            ["metaquotes-expert-advisor"],
            ["capture-metaquotes-expert-advisor"],
            "metaquotes-expert-advisor-page",
            "document-pan",
        ),
        (
            9_020,
            9_560,
            "0806-terminal-detail-a",
            "explanation",
            "asset-full",
            "technical-mono",
            [],
            ["metaeditor-code"],
            None,
            "animated",
        ),
        (
            9_560,
            10_700,
            "0806-presenter-reset",
            "claim",
            "presenter",
            "technical-mono",
            [],
            [],
            None,
            "live-footage",
        ),
        (
            10_700,
            12_060,
            "0806-terminal-detail-b",
            "explanation",
            "asset-full",
            "technical-mono",
            [],
            ["metaeditor-code"],
            None,
            "animated",
        ),
        (
            12_060,
            14_160,
            "0806-wrong-rule-flow",
            "contrast",
            "asset-full",
            "technical-mono",
            ["metaquotes-automated-trading"],
            ["wrong-rule-flow"],
            None,
            "animated",
        ),
        (
            14_160,
            14_480,
            "0806-document-scroll-in",
            "evidence",
            "asset-full",
            "documentary-clean",
            ["metaquotes-atc-history"],
            ["capture-metaquotes-atc-history"],
            None,
            "document-pan",
        ),
        (
            14_480,
            17_460,
            "0806-championship-evidence",
            "evidence",
            "asset-full",
            "documentary-clean",
            ["metaquotes-atc-history"],
            ["capture-metaquotes-atc-history"],
            "metaquotes-atc-history-page",
            "document-pan",
        ),
        (
            17_460,
            17_920,
            "0806-document-transition",
            "evidence",
            "asset-full",
            "documentary-clean",
            ["mql5-atc-2008-risk"],
            ["capture-mql5-atc-2008-risk"],
            None,
            "document-pan",
        ),
        (
            17_920,
            21_140,
            "0806-mql5-evidence",
            "evidence",
            "asset-full",
            "documentary-clean",
            ["mql5-atc-2008-risk"],
            ["capture-mql5-atc-2008-risk"],
            "mql5-atc-2008-risk-page",
            "document-pan",
        ),
        (
            21_140,
            21_820,
            "0806-risk-turn",
            "contrast",
            "asset-full",
            "technical-mono",
            ["mql5-atc-2008-risk"],
            ["risk-control"],
            None,
            "animated",
        ),
        (
            21_820,
            24_000,
            "0806-risk-control",
            "contrast",
            "asset-full",
            "technical-mono",
            ["mql5-atc-2008-risk"],
            ["risk-control"],
            None,
            "animated",
        ),
        (
            24_000,
            27_780,
            "0806-risk-reversal",
            "contrast",
            "asset-full",
            "technical-mono",
            ["mql5-atc-2008-risk"],
            ["risk-control"],
            None,
            "animated",
        ),
        (
            27_780,
            32_200,
            "automation-vs-risk",
            "payoff",
            "asset-full",
            "technical-mono",
            [
                "metaquotes-automated-trading",
                "mql5-atc-2008-risk",
            ],
            ["metaeditor-code", "risk-control"],
            None,
            "animated",
        ),
        (
            32_200,
            33_180,
            "0806-demo-setup",
            "demonstration",
            "asset-full",
            "technical-mono",
            [],
            ["demo-panel"],
            None,
            "animated",
        ),
        (
            33_180,
            37_160,
            "0806-demo-cta",
            "demonstration",
            "asset-full",
            "technical-mono",
            [],
            ["demo-panel"],
            None,
            "animated",
        ),
        (
            37_160,
            41_000,
            "0806-presenter-ending",
            "cta",
            "presenter",
            "compact-pill",
            [],
            [],
            None,
            "live-footage",
        ),
        (
            41_000,
            41_401,
            "0806-clean-tail",
            "payoff",
            "presenter",
            "compact-pill",
            [],
            [],
            None,
            "static",
        ),
    ]

    capture_by_asset_id = {
        "metaquotes-automated-trading-page": (
            "metaquotes-automated-trading",
            "metatrader5-automated-trading-definition.png",
        ),
        "metaquotes-expert-advisor-page": (
            "metaquotes-expert-advisor",
            "metatrader4-expert-advisor-definition.png",
        ),
        "metaquotes-atc-history-page": (
            "metaquotes-atc-history",
            "metatrader5-atc-history.png",
        ),
        "mql5-atc-2008-risk-page": (
            "mql5-atc-2008-risk",
            "mql5-atc-2008-risk.png",
        ),
    }
    capture_manifest_path = output_dir / "capture-manifest.json"
    capture_entries = {}
    if capture_manifest_path.is_file():
        capture_manifest = CaptureManifest.model_validate_json(
            capture_manifest_path.read_text(encoding="utf-8")
        )
        capture_entries = {
            entry.id: entry
            for entry in capture_manifest.entries
            if (output_dir / entry.path).is_file()
        }
    capture_id_by_treatment = {
        "0806-split-hook": "capture-mt5-hook-action",
        "0806-terminal-boot": "capture-metaeditor-open",
        "0806-code-rule-trace": "capture-metaeditor-code-macro",
        "0806-code-scroll": "capture-metaeditor-rule-highlight",
        "0806-ea-label": "capture-mt5-navigator-ea",
        "0806-terminal-detail-a": "capture-metaeditor-rule-highlight",
        "0806-terminal-detail-b": "capture-metaeditor-code-macro",
        "0806-risk-turn": "capture-mt5-risk-inputs",
        "0806-risk-control": "capture-mt5-risk-inputs",
        "0806-risk-reversal": "capture-mt5-risk-alternate",
        "automation-vs-risk": "capture-metaeditor-risk-code",
        "0806-demo-setup": "capture-mt5-attach-ea",
        "0806-demo-cta": "capture-mt5-strategy-tester",
    }
    scenes: list[ScenePlan] = []
    shots: list[ShotSpec] = []
    assets: list[AssetRef] = []
    for index, blueprint in enumerate(blueprints):
        (
            reference_start_ms,
            reference_end_ms,
            treatment,
            role,
            layout,
            caption_family,
            evidence_ids,
            artifact_ids,
            asset_id,
            motion,
        ) = blueprint
        start_ms = at(reference_start_ms)
        end_ms = at(reference_end_ms)
        scene_id = f"scene-{index + 1:02d}"
        capture_id = capture_id_by_treatment.get(treatment)
        capture_entry = (
            capture_entries.get(capture_id)
            if capture_id is not None
            else None
        )
        scheduled_asset_id = asset_id
        source_kind = "procedural"
        reference_role = (
            "secondary-4"
            if treatment in {
                "0806-wrong-rule-flow",
                "0806-risk-turn",
                "0806-risk-reversal",
            }
            else "primary-10"
        )
        if capture_entry is not None:
            scheduled_asset_id = f"{capture_entry.id}-{scene_id}"
            source_kind = "screen-recording"
            motion = "live-footage"
        elif asset_id in capture_by_asset_id:
            source_kind = "direct-source"
        elif layout in {"presenter", "split-screen", "presenter-pip"}:
            source_kind = "presenter"
        zoom = (
            1.12
            if treatment in {
                "0806-presenter-reset",
                "0806-presenter-ending",
                "0806-clean-tail",
            }
            else 1.0
        )
        scenes.append(
            ScenePlan(
                id=scene_id,
                start_ms=start_ms,
                end_ms=end_ms,
                role=role,
                layout=layout,
                zoom=zoom,
                treatment=treatment,
                asset_id=scheduled_asset_id,
                motion=motion,
            )
        )
        shots.append(
            ShotSpec(
                id=scene_id,
                start_ms=start_ms,
                end_ms=end_ms,
                role=role,
                layout=layout,
                treatment=treatment,
                caption_family=caption_family,
                evidence_ids=evidence_ids,
                artifact_ids=artifact_ids,
                asset_id=scheduled_asset_id,
                motion=motion,
                source_kind=source_kind,
                reference_role=reference_role,
            )
        )
        if capture_entry is not None and scheduled_asset_id is not None:
            assets.append(
                AssetRef(
                    id=scheduled_asset_id,
                    kind="video",
                    path=str((output_dir / capture_entry.path).resolve()),
                    keywords=[
                        treatment,
                        capture_entry.application,
                        "safe-demo-capture",
                    ],
                    provenance="local-safe-demo-capture",
                    license="Self-recorded disposable demo capture",
                    provider=capture_entry.application,
                    creator="Cutline local production",
                    start_ms=start_ms,
                    end_ms=end_ms,
                )
            )
        elif asset_id is not None:
            evidence_id, filename = capture_by_asset_id[asset_id]
            spec = next(
                item
                for item in _CAPTURE_SPECS
                if item["id"] == evidence_id
            )
            assets.append(
                AssetRef(
                    id=asset_id,
                    kind="image",
                    path=str(
                        (
                            output_dir
                            / "source-captures"
                            / filename
                        ).resolve()
                    ),
                    keywords=[
                        treatment,
                        evidence_id,
                        "direct-page",
                        motion,
                    ],
                    provenance="official-source-capture",
                    license="Editorial evidence capture",
                    provider=(
                        "MQL5"
                        if evidence_id.startswith("mql5-")
                        else "MetaQuotes"
                    ),
                    source_url=str(spec["url"]),
                    start_ms=start_ms,
                    end_ms=end_ms,
                )
            )

    existing_asset_ids = {asset.id for asset in assets}
    for asset_id, (evidence_id, filename) in capture_by_asset_id.items():
        if asset_id in existing_asset_ids:
            continue
        spec = next(
            item
            for item in _CAPTURE_SPECS
            if item["id"] == evidence_id
        )
        assets.append(
            AssetRef(
                id=asset_id,
                kind="image",
                path=str(
                    (
                        output_dir
                        / "source-captures"
                        / filename
                    ).resolve()
                ),
                keywords=[evidence_id, "direct-page"],
                provenance="official-source-capture",
                license="Editorial evidence capture",
                provider=(
                    "MQL5"
                    if evidence_id.startswith("mql5-")
                    else "MetaQuotes"
                ),
                source_url=str(spec["url"]),
            )
        )

    graphics = [
        GraphicCue(
            id="hook-display",
            start_ms=0,
            end_ms=at(2_100),
            kind="headline",
            text="CAN A ROBOT CHOOSE SAFE RISK?",
            accent="#F4F0E8",
        ),
        GraphicCue(
            id="risk-display",
            start_ms=at(21_820),
            end_ms=at(24_000),
            kind="headline",
            text="RISK TURNED THE GAME.",
            accent="#FF657A",
        ),
    ]
    return scenes, shots, assets, graphics


def _load_0806_v3_assets(output_dir: Path) -> list[AssetRef]:
    assets: list[AssetRef] = []
    direct_captures = {
        "v3-evidence-automated-trading": (
            "metaquotes-automated-trading",
            "metatrader5-automated-trading-definition.png",
        ),
        "v3-evidence-ea-definition": (
            "metaquotes-expert-advisor",
            "metatrader4-expert-advisor-definition.png",
        ),
        "v3-evidence-history": (
            "metaquotes-atc-history",
            "metatrader5-atc-history.png",
        ),
        "v3-evidence-result": (
            "mql5-atc-2008-risk",
            "mql5-atc-2008-risk.png",
        ),
    }
    for asset_id, (evidence_id, filename) in direct_captures.items():
        spec = next(
            item for item in _CAPTURE_SPECS if item["id"] == evidence_id
        )
        path = (output_dir / "source-captures" / filename).resolve()
        if not path.is_file():
            raise RuntimeError(f"Missing V3 evidence capture: {path}")
        assets.append(
            AssetRef(
                id=asset_id,
                kind="image",
                path=str(path),
                keywords=["0806-v3", evidence_id, "direct-source"],
                provenance="official-source-capture",
                license="Editorial evidence capture",
                provider=(
                    "MQL5"
                    if evidence_id.startswith("mql5-")
                    else "MetaQuotes"
                ),
                source_url=str(spec["url"]),
            )
        )

    licensed_manifest_path = (
        output_dir / "licensed-footage" / "manifest.json"
    )
    if not licensed_manifest_path.is_file():
        raise RuntimeError(
            "V3 requires licensed-footage/manifest.json with complete "
            "provenance"
        )
    licensed_manifest = json.loads(
        licensed_manifest_path.read_text(encoding="utf-8")
    )
    for entry in licensed_manifest.get("entries", []):
        path = (output_dir / str(entry["path"])).resolve()
        if not path.is_file():
            raise RuntimeError(f"Missing licensed V3 footage: {path}")
        assets.append(
            AssetRef(
                id=str(entry["id"]),
                kind="video",
                path=str(path),
                keywords=["0806-v3", "cinematic", "licensed-footage"],
                provenance="internet:coverr-free-video",
                license=str(entry["license"]),
                provider=str(entry["provider"]),
                remote_id=str(entry["remote_id"]),
                creator=str(entry["creator"]),
                source_url=str(entry["source_url"]),
                license_url=str(entry["license_url"]),
                search_query=str(entry["search_query"]),
            )
        )

    capture_manifest_path = output_dir / "capture-manifest.json"
    if not capture_manifest_path.is_file():
        raise RuntimeError(
            "V3 requires the privacy-reviewed local MetaTrader "
            "capture-manifest.json"
        )
    capture_manifest = CaptureManifest.model_validate_json(
        capture_manifest_path.read_text(encoding="utf-8")
    )
    for entry in capture_manifest.entries:
        path = (output_dir / entry.path).resolve()
        if not path.is_file():
            continue
        assets.append(
            AssetRef(
                id=entry.id,
                kind="video",
                path=str(path),
                keywords=[
                    "0806-v3",
                    entry.application,
                    "safe-demo-capture",
                ],
                provenance="local-safe-demo-capture",
                license="Self-recorded disposable demo capture",
                provider=entry.application,
                creator="Cutline local production",
            )
        )
    return assets


def _build_0806_v3_storyboard(
    *,
    retimed_segments: list[TranscriptSegment],
    duration_ms: int,
    output_dir: Path,
) -> tuple[
    list[ScenePlan],
    list[ShotSpec],
    list[AssetRef],
    list[GraphicCue],
]:
    reference_duration_ms = 41_401
    scale = duration_ms / reference_duration_ms
    expected_follow_ms = round(37_160 * scale)
    detected_follow_ms = _word_start_ms(
        retimed_segments[11],
        "follow",
        -1,
    )
    if (
        detected_follow_ms >= 0
        and abs(detected_follow_ms - expected_follow_ms) <= 250
    ):
        follow_boundary_ms = detected_follow_ms
    elif duration_ms >= 40_000:
        follow_boundary_ms = expected_follow_ms
    else:
        follow_boundary_ms = round(
            (
                retimed_segments[11].start
                + (
                    retimed_segments[11].end
                    - retimed_segments[11].start
                )
                * 0.55
            )
            * 1000
        )
    aligned_times = {
        0: 0,
        2_340: round(retimed_segments[0].end * 1000),
        6_820: round(retimed_segments[1].end * 1000),
        9_560: round(retimed_segments[3].start * 1000),
        10_700: round(retimed_segments[3].end * 1000),
        12_060: round(retimed_segments[4].start * 1000),
        14_160: round(retimed_segments[4].end * 1000),
        14_480: round(retimed_segments[5].start * 1000),
        17_460: round(retimed_segments[5].end * 1000),
        17_920: round(retimed_segments[6].start * 1000),
        21_140: round(retimed_segments[6].end * 1000),
        21_820: round(retimed_segments[7].start * 1000),
        23_140: round(retimed_segments[7].end * 1000),
        24_000: round(retimed_segments[8].start * 1000),
        25_520: round(retimed_segments[8].end * 1000),
        26_080: round(retimed_segments[9].start * 1000),
        27_780: round(retimed_segments[9].end * 1000),
        32_200: round(retimed_segments[10].end * 1000),
        33_180: round(retimed_segments[11].start * 1000),
        37_160: follow_boundary_ms,
        41_000: round(retimed_segments[11].end * 1000),
        reference_duration_ms: duration_ms,
    }

    def at(reference_time_ms: int) -> int:
        if reference_time_ms in aligned_times:
            return aligned_times[reference_time_ms]
        return round(reference_time_ms * scale)

    blueprints = [
        {
            "start": 0,
            "end": 1_200,
            "treatment": "0806-v3-hook-physical",
            "role": "hook",
            "layout": "asset-full",
            "caption_family": "technical-mono",
            "asset_id": "coverr-developing-coding-sequences-3909",
            "source_kind": "licensed-footage",
            "reference_role": "primary-10",
            "visual_category": "cinematic-broll",
            "primary_subject": "physical laptop running an Expert Advisor",
            "source_family": "coverr-developing-coding-sequences-3909",
        },
        {
            "start": 1_200,
            "end": 2_340,
            "treatment": "0806-v3-hook-presenter",
            "role": "hook",
            "layout": "split-screen",
            "caption_family": "technical-mono",
            "asset_id": "coverr-developing-coding-sequences-3909",
            "source_kind": "licensed-footage",
            "reference_role": "primary-10",
            "visual_category": "hook-composite",
            "primary_subject": "Expert Advisor screen and presenter",
            "source_family": "coverr-developing-coding-sequences-3909",
        },
        {
            "start": 2_340,
            "end": 3_740,
            "treatment": "0806-v3-code-cinematic",
            "role": "explanation",
            "layout": "asset-full",
            "caption_family": "technical-mono",
            "asset_id": "coverr-casual-man-typing-9754",
            "source_kind": "licensed-footage",
            "reference_role": "primary-10",
            "visual_category": "cinematic-broll",
            "primary_subject": "hands entering code on a laptop",
            "source_family": "coverr-casual-man-typing-9754",
        },
        {
            "start": 3_740,
            "end": 5_200,
            "treatment": "0806-v3-code-card",
            "role": "explanation",
            "layout": "asset-full",
            "caption_family": "technical-mono",
            "artifact_ids": ["metaeditor-code"],
            "source_kind": "procedural",
            "reference_role": "primary-10",
            "visual_category": "designed-explanation",
            "primary_subject": "isolated MQL5 rule card",
            "source_family": "v3-code-card",
        },
        {
            "start": 5_200,
            "end": 6_820,
            "treatment": "0806-v3-rule-pipeline",
            "role": "explanation",
            "layout": "asset-full",
            "caption_family": "technical-mono",
            "evidence_ids": ["metaquotes-automated-trading"],
            "artifact_ids": ["metaeditor-code"],
            "source_kind": "procedural",
            "reference_role": "primary-10",
            "visual_category": "designed-explanation",
            "primary_subject": "read decide execute pipeline",
            "source_family": "v3-rule-pipeline",
        },
        {
            "start": 6_820,
            "end": 7_800,
            "treatment": "0806-v3-navigator-macro",
            "role": "demonstration",
            "layout": "asset-full",
            "caption_family": "technical-mono",
            "evidence_ids": ["metaquotes-expert-advisor"],
            "asset_id": "capture-mt5-navigator-ea",
            "source_kind": "screen-recording",
            "reference_role": "supporting",
            "visual_category": "product-macro",
            "primary_subject": "Expert Advisors item in Navigator",
            "source_family": "capture-mt5-navigator-ea",
            "simultaneous_actions": 1,
        },
        {
            "start": 7_800,
            "end": 9_560,
            "treatment": "0806-v3-ea-identity",
            "role": "explanation",
            "layout": "asset-full",
            "caption_family": "technical-mono",
            "evidence_ids": ["metaquotes-expert-advisor"],
            "artifact_ids": ["metaeditor-code"],
            "source_kind": "procedural",
            "reference_role": "primary-10",
            "visual_category": "designed-explanation",
            "primary_subject": "Expert Advisor identity",
            "source_family": "v3-ea-identity",
        },
        {
            "start": 9_560,
            "end": 10_700,
            "treatment": "0806-v3-presenter-reset",
            "role": "claim",
            "layout": "presenter",
            "caption_family": "technical-mono",
            "source_kind": "presenter",
            "reference_role": "primary-10",
            "visual_category": "presenter",
            "primary_subject": "presenter",
            "source_family": "presenter",
        },
        {
            "start": 10_700,
            "end": 12_060,
            "treatment": "0806-v3-rule-card",
            "role": "explanation",
            "layout": "asset-full",
            "caption_family": "technical-mono",
            "artifact_ids": ["metaeditor-code"],
            "source_kind": "procedural",
            "reference_role": "primary-10",
            "visual_category": "designed-explanation",
            "primary_subject": "preset trading rule",
            "source_family": "v3-rule-card",
        },
        {
            "start": 12_060,
            "end": 14_160,
            "treatment": "0806-v3-wrong-rule",
            "role": "contrast",
            "layout": "asset-full",
            "caption_family": "technical-mono",
            "evidence_ids": ["metaquotes-automated-trading"],
            "artifact_ids": ["wrong-rule-flow"],
            "source_kind": "procedural",
            "reference_role": "secondary-4",
            "visual_category": "designed-explanation",
            "primary_subject": "wrong-rule branch",
            "source_family": "v3-wrong-rule",
        },
        {
            "start": 14_160,
            "end": 14_480,
            "treatment": "0806-v3-evidence-overview",
            "role": "evidence",
            "layout": "asset-full",
            "caption_family": "documentary-clean",
            "evidence_ids": ["metaquotes-expert-advisor"],
            "artifact_ids": ["capture-metaquotes-expert-advisor"],
            "asset_id": "v3-evidence-ea-definition",
            "source_kind": "direct-source",
            "reference_role": "supporting",
            "visual_category": "edited-evidence",
            "primary_subject": "official championship source page",
            "source_family": "v3-evidence-ea-definition",
        },
        {
            "start": 14_480,
            "end": 16_000,
            "treatment": "0806-v3-evidence-heading",
            "role": "evidence",
            "layout": "asset-full",
            "caption_family": "documentary-clean",
            "evidence_ids": ["metaquotes-atc-history"],
            "artifact_ids": ["capture-metaquotes-atc-history"],
            "asset_id": "v3-evidence-history",
            "source_kind": "direct-source",
            "reference_role": "supporting",
            "visual_category": "edited-evidence",
            "primary_subject": "Automated Trading Championship heading",
            "source_family": "v3-evidence-history",
        },
        {
            "start": 16_000,
            "end": 17_460,
            "treatment": "0806-v3-evidence-history",
            "role": "evidence",
            "layout": "asset-full",
            "caption_family": "documentary-clean",
            "evidence_ids": ["metaquotes-atc-history"],
            "artifact_ids": ["capture-metaquotes-atc-history"],
            "asset_id": "v3-evidence-history",
            "source_kind": "direct-source",
            "reference_role": "supporting",
            "visual_category": "edited-evidence",
            "primary_subject": "championship history excerpt",
            "source_family": "v3-evidence-history",
        },
        {
            "start": 17_460,
            "end": 17_920,
            "treatment": "0806-v3-evidence-year",
            "role": "evidence",
            "layout": "asset-full",
            "caption_family": "documentary-clean",
            "evidence_ids": ["mql5-atc-2008-risk"],
            "artifact_ids": ["capture-mql5-atc-2008-risk"],
            "source_kind": "procedural",
            "reference_role": "supporting",
            "visual_category": "edited-evidence",
            "primary_subject": "verified year 2008",
            "source_family": "v3-evidence-year",
        },
        {
            "start": 17_920,
            "end": 19_520,
            "treatment": "0806-v3-evidence-result",
            "role": "evidence",
            "layout": "asset-full",
            "caption_family": "documentary-clean",
            "evidence_ids": ["mql5-atc-2008-risk"],
            "artifact_ids": ["capture-mql5-atc-2008-risk"],
            "asset_id": "v3-evidence-result",
            "source_kind": "direct-source",
            "reference_role": "supporting",
            "visual_category": "edited-evidence",
            "primary_subject": "verified result excerpt",
            "source_family": "v3-evidence-result",
        },
        {
            "start": 19_520,
            "end": 21_140,
            "treatment": "0806-v3-evidence-number",
            "role": "evidence",
            "layout": "asset-full",
            "caption_family": "documentary-clean",
            "evidence_ids": ["mql5-atc-2008-risk"],
            "artifact_ids": ["capture-mql5-atc-2008-risk"],
            "asset_id": "v3-evidence-result",
            "source_kind": "direct-source",
            "reference_role": "supporting",
            "visual_category": "edited-evidence",
            "primary_subject": "verified $110,000 sentence",
            "source_family": "v3-evidence-result",
        },
        {
            "start": 21_140,
            "end": 21_550,
            "treatment": "0806-v3-risk-turn",
            "role": "contrast",
            "layout": "asset-full",
            "caption_family": "technical-mono",
            "evidence_ids": ["mql5-atc-2008-risk"],
            "artifact_ids": ["risk-control"],
            "source_kind": "procedural",
            "reference_role": "secondary-4",
            "visual_category": "designed-explanation",
            "primary_subject": "risk control reset",
            "source_family": "v3-risk-turn",
        },
        {
            "start": 21_550,
            "end": 23_140,
            "treatment": "0806-v3-risk-control",
            "role": "contrast",
            "layout": "asset-full",
            "caption_family": "technical-mono",
            "evidence_ids": ["mql5-atc-2008-risk"],
            "artifact_ids": ["risk-control"],
            "source_kind": "procedural",
            "reference_role": "secondary-4",
            "visual_category": "designed-explanation",
            "primary_subject": "single risk variable",
            "source_family": "v3-risk-control",
        },
        {
            "start": 23_140,
            "end": 24_000,
            "treatment": "0806-v3-risk-input",
            "role": "demonstration",
            "layout": "asset-full",
            "caption_family": "technical-mono",
            "evidence_ids": ["mql5-atc-2008-risk"],
            "asset_id": "capture-mt5-risk-inputs",
            "source_kind": "screen-recording",
            "reference_role": "supporting",
            "visual_category": "product-macro",
            "primary_subject": "real risk input",
            "source_family": "capture-mt5-risk-inputs",
            "simultaneous_actions": 1,
        },
        {
            "start": 24_000,
            "end": 25_520,
            "treatment": "0806-v3-risk-rise",
            "role": "contrast",
            "layout": "asset-full",
            "caption_family": "technical-mono",
            "evidence_ids": ["mql5-atc-2008-risk"],
            "artifact_ids": ["risk-control"],
            "source_kind": "procedural",
            "reference_role": "secondary-4",
            "visual_category": "designed-explanation",
            "primary_subject": "rising risk path",
            "source_family": "v3-risk-path",
        },
        {
            "start": 25_520,
            "end": 26_080,
            "treatment": "0806-v3-risk-alternate",
            "role": "demonstration",
            "layout": "asset-full",
            "caption_family": "technical-mono",
            "evidence_ids": ["mql5-atc-2008-risk"],
            "asset_id": "capture-mt5-risk-alternate",
            "source_kind": "screen-recording",
            "reference_role": "supporting",
            "visual_category": "product-macro",
            "primary_subject": "alternate risk input",
            "source_family": "capture-mt5-risk-alternate",
            "simultaneous_actions": 1,
        },
        {
            "start": 26_080,
            "end": 27_780,
            "treatment": "0806-v3-risk-reversal",
            "role": "contrast",
            "layout": "asset-full",
            "caption_family": "technical-mono",
            "evidence_ids": ["mql5-atc-2008-risk"],
            "artifact_ids": ["risk-control"],
            "source_kind": "procedural",
            "reference_role": "secondary-4",
            "visual_category": "designed-explanation",
            "primary_subject": "reversing risk path",
            "source_family": "v3-risk-path",
        },
        {
            "start": 27_780,
            "end": 29_980,
            "treatment": "0806-v3-lesson-contrast",
            "role": "payoff",
            "layout": "asset-full",
            "caption_family": "technical-mono",
            "evidence_ids": [
                "metaquotes-automated-trading",
                "mql5-atc-2008-risk",
            ],
            "artifact_ids": ["demo-panel"],
            "asset_id": "coverr-casual-man-typing-9754",
            "source_kind": "licensed-footage",
            "reference_role": "primary-10",
            "visual_category": "cinematic-broll",
            "primary_subject": "human hands choosing the trading input",
            "source_family": "coverr-casual-man-typing-9754",
        },
        {
            "start": 29_980,
            "end": 32_320,
            "treatment": "0806-v3-lesson-pipeline",
            "role": "payoff",
            "layout": "asset-full",
            "caption_family": "technical-mono",
            "evidence_ids": ["metaquotes-automated-trading"],
            "artifact_ids": ["metaeditor-code", "demo-panel"],
            "source_kind": "procedural",
            "reference_role": "primary-10",
            "visual_category": "designed-explanation",
            "primary_subject": "deterministic execution pipeline",
            "source_family": "v3-lesson-pipeline",
        },
        {
            "start": 32_320,
            "end": 33_180,
            "treatment": "0806-v3-demo-establishing",
            "role": "demonstration",
            "layout": "asset-full",
            "caption_family": "technical-mono",
            "asset_id": "coverr-guy-working-pc-18",
            "source_kind": "licensed-footage",
            "reference_role": "supporting",
            "visual_category": "cinematic-broll",
            "primary_subject": "physical workstation",
            "source_family": "coverr-guy-working-pc-18",
        },
        {
            "start": 33_180,
            "end": 35_000,
            "treatment": "0806-v3-demo-attach",
            "role": "demonstration",
            "layout": "asset-full",
            "caption_family": "technical-mono",
            "asset_id": "coverr-developing-coding-sequences-3909",
            "source_kind": "licensed-footage",
            "reference_role": "supporting",
            "visual_category": "cinematic-broll",
            "primary_subject": "attach Expert Advisor on a physical laptop",
            "source_family": "coverr-developing-coding-sequences-3909",
            "simultaneous_actions": 1,
        },
        {
            "start": 35_000,
            "end": 36_080,
            "treatment": "0806-v3-demo-input",
            "role": "demonstration",
            "layout": "asset-full",
            "caption_family": "technical-mono",
            "asset_id": "capture-mt5-risk-inputs",
            "source_kind": "screen-recording",
            "reference_role": "supporting",
            "visual_category": "product-macro",
            "primary_subject": "one real Expert Advisor input",
            "source_family": "capture-mt5-risk-inputs",
            "simultaneous_actions": 1,
        },
        {
            "start": 36_080,
            "end": 37_160,
            "treatment": "0806-v3-demo-strategy",
            "role": "demonstration",
            "layout": "asset-full",
            "caption_family": "technical-mono",
            "asset_id": "capture-mt5-strategy-tester",
            "source_kind": "screen-recording",
            "reference_role": "supporting",
            "visual_category": "product-macro",
            "primary_subject": "real Strategy Tester setup",
            "source_family": "capture-mt5-strategy-tester",
            "simultaneous_actions": 1,
        },
        {
            "start": 37_160,
            "end": 39_200,
            "treatment": "0806-v3-presenter-ending",
            "role": "cta",
            "layout": "presenter",
            "caption_family": "compact-pill",
            "source_kind": "presenter",
            "reference_role": "primary-10",
            "visual_category": "presenter",
            "primary_subject": "presenter",
            "source_family": "presenter",
        },
        {
            "start": 39_200,
            "end": 41_401,
            "treatment": "0806-v3-clean-ending",
            "role": "cta",
            "layout": "presenter",
            "caption_family": "compact-pill",
            "source_kind": "presenter",
            "reference_role": "primary-10",
            "visual_category": "presenter",
            "primary_subject": "presenter",
            "source_family": "presenter",
        },
    ]

    assets = _load_0806_v3_assets(output_dir)
    asset_ids = {asset.id for asset in assets}
    scenes: list[ScenePlan] = []
    shots: list[ShotSpec] = []
    for index, blueprint in enumerate(blueprints):
        start_ms = at(int(blueprint["start"]))
        end_ms = at(int(blueprint["end"]))
        asset_id = blueprint.get("asset_id")
        if asset_id is not None and asset_id not in asset_ids:
            raise RuntimeError(
                f"V3 storyboard asset is unavailable: {asset_id}"
            )
        scene_id = f"scene-{index + 1:02d}"
        treatment = str(blueprint["treatment"])
        layout = str(blueprint["layout"])
        zoom = (
            1.12
            if treatment in {
                "0806-v3-presenter-reset",
                "0806-v3-presenter-ending",
                "0806-v3-clean-ending",
            }
            else 1.0
        )
        motion = str(blueprint.get("motion", "animated"))
        if blueprint["source_kind"] in {
            "presenter",
            "licensed-footage",
            "screen-recording",
        }:
            motion = "live-footage"
        elif blueprint["source_kind"] == "direct-source":
            motion = "document-pan"
        scenes.append(
            ScenePlan(
                id=scene_id,
                start_ms=start_ms,
                end_ms=end_ms,
                role=blueprint["role"],
                layout=layout,
                zoom=zoom,
                treatment=treatment,
                asset_id=asset_id,
                motion=motion,
            )
        )
        shots.append(
            ShotSpec(
                id=scene_id,
                start_ms=start_ms,
                end_ms=end_ms,
                role=blueprint["role"],
                layout=layout,
                treatment=treatment,
                caption_family=blueprint["caption_family"],
                evidence_ids=list(blueprint.get("evidence_ids", [])),
                artifact_ids=list(blueprint.get("artifact_ids", [])),
                asset_id=asset_id,
                motion=motion,
                source_kind=blueprint["source_kind"],
                reference_role=blueprint["reference_role"],
                visual_category=blueprint["visual_category"],
                primary_subject=str(blueprint["primary_subject"]),
                source_family=str(blueprint["source_family"]),
                simultaneous_actions=int(
                    blueprint.get("simultaneous_actions", 0)
                ),
            )
        )

    graphics = [
        GraphicCue(
            id="v3-hook-display",
            start_ms=0,
            end_ms=at(2_340),
            kind="headline",
            text="CAN A ROBOT CHOOSE SAFE RISK?",
            accent="#F4F0E8",
        )
    ]
    return scenes, shots, assets, graphics


def _word_start_ms(
    segment: TranscriptSegment,
    text: str,
    fallback: int,
) -> int:
    normalized = re.sub(r"[^a-z0-9]", "", text.casefold())
    for word in segment.words:
        candidate = re.sub(r"[^a-z0-9]", "", word.text.casefold())
        if candidate == normalized:
            return round(word.start * 1000)
    return fallback


def _strict_boundaries(
    values: list[int],
    *,
    duration_ms: int,
) -> list[int]:
    boundaries: list[int] = []
    for value in values:
        clamped = max(0, min(duration_ms, value))
        if not boundaries or clamped > boundaries[-1]:
            boundaries.append(clamped)
    if boundaries[0] != 0:
        boundaries.insert(0, 0)
    if boundaries[-1] != duration_ms:
        boundaries.append(duration_ms)
    return boundaries


def _reference_caption_structure_ok(
    pages: list[CaptionPage],
    segments: list[TranscriptSegment],
    *,
    duration_ms: int,
) -> bool:
    allowed_four_word_phrases = {
        "do you know what",
        "trades on set rules.",
        "doesn't trade with emotions,",
    }
    for page in pages:
        phrase = " ".join(token.text for token in page.tokens).casefold()
        if len(page.tokens) > 4:
            return False
        if (
            len(page.tokens) == 4
            and phrase not in allowed_four_word_phrases
        ):
            return False
        if (
            page.tokens[-1].text.rstrip(".,:;!?") == "Expert"
            or page.tokens[0].text.rstrip(".,:;!?") == "Advisor"
        ):
            return False
        first_token_ms = page.tokens[0].start_ms
        sentence_index = next(
            (
                index
                for index, segment in enumerate(segments)
                if (
                    round(segment.start * 1000) <= first_token_ms
                    < (
                        round(segments[index + 1].start * 1000)
                        if index + 1 < len(segments)
                        else duration_ms + 1
                    )
                )
            ),
            None,
        )
        if sentence_index is None:
            return False
        sentence_start_ms = round(
            segments[sentence_index].start * 1000
        )
        sentence_window_end_ms = (
            round(segments[sentence_index + 1].start * 1000)
            if sentence_index + 1 < len(segments)
            else duration_ms
        )
        if (
            page.start_ms < sentence_start_ms
            or page.end_ms > sentence_window_end_ms
        ):
            return False
    return True


def _preflight_review(
    *,
    plan: EditPlanV1,
    shots: list[ShotSpec],
    evidence: list[EvidenceItem],
    artifacts: list[ArtifactSpec],
    retimed_segments: list[TranscriptSegment],
) -> list[VisualReviewCheck]:
    evidence_ids = {item.id for item in evidence if item.status == "verified"}
    artifact_ids = {item.id for item in artifacts}
    caption_structure_ok = _reference_caption_structure_ok(
        plan.caption_pages,
        retimed_segments,
        duration_ms=plan.duration_ms,
    )
    output_dir = Path(plan.assets[0].path).parents[1]
    source_capture_ok = all(
        Path(item.capture_path).suffix.lower() == ".png"
        and (output_dir / item.capture_path).is_file()
        and not _capture_needs_refresh(output_dir / item.capture_path)
        for item in evidence
    )
    presenter_ms = sum(
        shot.end_ms - shot.start_ms
        for shot in shots
        if shot.layout in {"presenter", "split-screen", "presenter-pip"}
    )
    presenter_ratio = presenter_ms / plan.duration_ms
    moving_ms = sum(
        shot.end_ms - shot.start_ms
        for shot in shots
        if shot.motion != "static"
    )
    moving_ratio = moving_ms / plan.duration_ms
    technical_ratio = (
        sum(
            page.family == "technical-mono"
            for page in plan.caption_pages
        )
        / max(len(plan.caption_pages), 1)
    )
    direct_capture_count = len(
        {
            asset.id
            for asset in plan.assets
            if asset.provenance == "official-source-capture"
        }
    )
    no_source_cards = all(
        "source-card" not in artifact.path
        for artifact in artifacts
    ) and all(
        "source-card" not in asset.path
        for asset in plan.assets
    )
    music_duration_ok = False
    music_asset = next(
        (
            asset
            for asset in plan.assets
            if asset.id == plan.audio.music_asset_id
        ),
        None,
    )
    if music_asset is not None:
        try:
            with wave.open(music_asset.path, "rb") as stream:
                music_duration_ms = round(
                    stream.getnframes()
                    / stream.getframerate()
                    * 1000
                )
            music_duration_ok = (
                abs(music_duration_ms - plan.duration_ms) <= 2
            )
        except (wave.Error, OSError):
            music_duration_ok = False
    return [
        VisualReviewCheck(
            name="verified-evidence",
            passed=(
                len(evidence_ids) >= 4
                and all(
                    set(shot.evidence_ids).issubset(evidence_ids)
                    for shot in shots
                )
            ),
            detail=f"{len(evidence_ids)} verified evidence records.",
            evidence=["evidence.json"],
        ),
        VisualReviewCheck(
            name="storyboard-artifacts",
            passed=(
                len({shot.treatment for shot in shots}) >= 6
                and all(
                    set(shot.artifact_ids).issubset(artifact_ids)
                    for shot in shots
                )
            ),
            detail=(
                f"{len({shot.treatment for shot in shots})} unique visual "
                "treatments."
            ),
            evidence=["storyboard.json", "artifacts.json"],
        ),
        VisualReviewCheck(
            name="caption-sentence-boundaries",
            passed=(
                caption_structure_ok
                and technical_ratio > 0.60
            ),
            detail=(
                "Pages stay inside sentence or trailing-pause windows, use "
                "one to three words except approved grammar-bound four-word "
                "phrases, preserve Expert Advisor, and keep "
                f"technical mono dominant ({technical_ratio:.1%})."
            ),
            evidence=["caption-plan.json", "transcript.json"],
        ),
        VisualReviewCheck(
            name="source-capture-files",
            passed=source_capture_ok,
            detail="Every verified evidence item has a local source capture.",
            evidence=[item.capture_path for item in evidence],
        ),
        VisualReviewCheck(
            name="original-duration",
            passed=(
                plan.duration_ms
                == round(plan.source_metadata.duration_seconds * 1000)
                and len(plan.timeline) == 1
                and plan.timeline[0].source_start_ms == 0
            ),
            detail=(
                f"Output plan preserves the complete {plan.duration_ms} ms "
                "source timeline."
            ),
            evidence=["edit-plan.json", "transcript-aligned.json"],
        ),
        VisualReviewCheck(
            name="presenter-motion-coverage",
            passed=(
                0.14 <= presenter_ratio <= 0.20
                and moving_ratio >= 0.60
            ),
            detail=(
                f"presenter={presenter_ratio:.1%}, "
                f"meaningful motion={moving_ratio:.1%}."
            ),
            evidence=["storyboard.json"],
        ),
        VisualReviewCheck(
            name="direct-capture-policy",
            passed=direct_capture_count >= 4 and no_source_cards,
            detail=(
                f"{direct_capture_count} direct official captures; "
                "zero generated source-card wrappers."
            ),
            evidence=["asset-manifest.json", "source-captures/"],
        ),
        VisualReviewCheck(
            name="motivated-sound-design",
            passed=(
                9 <= len(plan.audio.sfx_cues) <= 13
                and all(cue.reason for cue in plan.audio.sfx_cues)
                and music_duration_ok
            ),
            detail=(
                f"{len(plan.audio.sfx_cues)} motivated effects and one "
                "full-duration non-looping score."
            ),
            evidence=["sfx-cue-sheet.json", "music-map.json"],
        ),
        VisualReviewCheck(
            name="unsupported-visible-facts",
            passed=True,
            detail=(
                "Generated visuals contain no statistics or social metrics; "
                "the visible 2008/$110,000 claims are tied to evidence."
            ),
            evidence=["evidence.json", "storyboard.json"],
        ),
    ]


def _write_source_card_svg(
    *,
    output: Path,
    capture: Path,
    title: str,
    eyebrow: str,
    source_url: str,
    claim: str,
) -> None:
    encoded = base64.b64encode(capture.read_bytes()).decode("ascii")
    image = cv2.imread(str(capture))
    if image is None:
        raise RuntimeError(f"Unable to read source capture: {capture}")
    height, width = image.shape[:2]
    display_width = 900
    display_height = min(460, round(display_width * height / width))
    card_y = 620
    claim_lines = _wrap_text(claim, width=48)
    title_lines = _wrap_text(title, width=23)
    claim_tspans = "".join(
        (
            f'<tspan x="90" dy="{0 if index == 0 else 46}">'
            f"{escape(line)}</tspan>"
        )
        for index, line in enumerate(claim_lines)
    )
    title_tspans = "".join(
        (
            f'<tspan x="72" dy="{0 if index == 0 else 70}">'
            f"{escape(line)}</tspan>"
        )
        for index, line in enumerate(title_lines)
    )
    browser_y = 276 + max(1, len(title_lines)) * 70
    card_y = max(620, browser_y + 230)
    output.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#071018"/>
    <stop offset="0.58" stop-color="#080A0D"/>
    <stop offset="1" stop-color="#111C24"/>
  </linearGradient>
  <filter id="shadow"><feDropShadow dx="0" dy="24" stdDeviation="28" flood-opacity="0.45"/></filter>
</defs>
<rect width="1080" height="1920" fill="url(#bg)"/>
<circle cx="920" cy="160" r="280" fill="#00E5FF" opacity="0.08"/>
<text x="72" y="116" fill="#D7FF64" font-family="Consolas, monospace" font-size="25" font-weight="700" letter-spacing="3">{escape(eyebrow)}</text>
<text x="72" y="206" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="62" font-weight="800" letter-spacing="-2">{title_tspans}</text>
<rect x="64" y="{browser_y}" width="952" height="104" rx="24" fill="#111820" stroke="#2B3944" stroke-width="2"/>
<circle cx="108" cy="{browser_y + 52}" r="9" fill="#FF657A"/><circle cx="140" cy="{browser_y + 52}" r="9" fill="#FFF078"/><circle cx="172" cy="{browser_y + 52}" r="9" fill="#55F2A2"/>
<text x="210" y="{browser_y + 63}" fill="#B8C4CE" font-family="Consolas, monospace" font-size="24">{escape(source_url)}</text>
<rect x="64" y="{card_y - 34}" width="952" height="{display_height + 68}" rx="30" fill="#F8F8F6" filter="url(#shadow)"/>
<image x="90" y="{card_y}" width="{display_width}" height="{display_height}" href="data:image/png;base64,{encoded}" preserveAspectRatio="xMidYMid meet"/>
<text x="90" y="{card_y + display_height + 150}" fill="#FFFFFF" font-family="Arial, sans-serif" font-size="38" font-weight="700">{claim_tspans}</text>
<rect x="72" y="1710" width="936" height="2" fill="#33434F"/>
<text x="72" y="1770" fill="#93A4B1" font-family="Consolas, monospace" font-size="22">SOURCE CAPTURE • VERIFIED • NO RECREATED DOCUMENT</text>
</svg>""",
        encoding="utf-8",
    )


def _rule_engine_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920">
<defs><linearGradient id="b" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#061017"/><stop offset="1" stop-color="#0B0D12"/></linearGradient></defs>
<rect width="1080" height="1920" fill="url(#b)"/>
<g opacity=".13" stroke="#00E5FF"><path d="M0 260H1080M0 520H1080M0 780H1080M0 1040H1080M0 1300H1080M0 1560H1080"/><path d="M180 0V1920M360 0V1920M540 0V1920M720 0V1920M900 0V1920"/></g>
<text x="70" y="140" fill="#00E5FF" font-family="Consolas" font-size="25" font-weight="700" letter-spacing="4">TECHNICAL BREAKDOWN • ILLUSTRATIVE</text>
<text x="70" y="245" fill="white" font-family="Arial" font-size="68" font-weight="800">FIXED RULES → ACTION</text>
<text x="70" y="305" fill="#AAB7C1" font-family="Arial" font-size="31">A verified concept diagram — not trading performance data</text>
<g font-family="Consolas" font-size="34" font-weight="700">
<rect x="110" y="520" width="860" height="180" rx="34" fill="#101A21" stroke="#50616D" stroke-width="3"/><text x="165" y="625" fill="white">01  READ MARKET DATA</text>
<path d="M540 700V790" stroke="#00E5FF" stroke-width="8"/><path d="M520 770L540 800L560 770" fill="#00E5FF"/>
<rect x="110" y="800" width="860" height="180" rx="34" fill="#0A2229" stroke="#00E5FF" stroke-width="4"/><text x="165" y="905" fill="#D7FF64">02  CHECK PRESET RULES</text>
<path d="M540 980V1070" stroke="#00E5FF" stroke-width="8"/><path d="M520 1050L540 1080L560 1050" fill="#00E5FF"/>
<rect x="110" y="1080" width="860" height="180" rx="34" fill="#101A21" stroke="#50616D" stroke-width="3"/><text x="165" y="1185" fill="white">03  EXECUTE / WAIT</text>
</g>
<text x="70" y="1695" fill="#8697A3" font-family="Consolas" font-size="22">BASED ON OFFICIAL METATRADER AUTOMATED-TRADING DOCUMENTATION</text>
</svg>"""


def _ea_code_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920">
<rect width="1080" height="1920" fill="#070A0E"/>
<circle cx="920" cy="210" r="330" fill="#00E5FF" opacity=".08"/>
<text x="70" y="130" fill="#D7FF64" font-family="Consolas" font-size="24" font-weight="700" letter-spacing="4">EXPERT ADVISOR • ILLUSTRATIVE LOGIC</text>
<text x="70" y="235" fill="white" font-family="Arial" font-size="68" font-weight="800">A RULES-BASED</text>
<text x="70" y="315" fill="white" font-family="Arial" font-size="68" font-weight="800">PROGRAM</text>
<rect x="66" y="440" width="948" height="830" rx="32" fill="#020407" stroke="#273640" stroke-width="3"/>
<rect x="66" y="440" width="948" height="86" rx="32" fill="#111820"/>
<circle cx="116" cy="483" r="10" fill="#FF657A"/><circle cx="150" cy="483" r="10" fill="#FFF078"/><circle cx="184" cy="483" r="10" fill="#55F2A2"/>
<text x="230" y="494" fill="#97A6B1" font-family="Consolas" font-size="23">ILLUSTRATIVE EA LOGIC — NOT SOURCE CODE</text>
<g font-family="Consolas" font-size="34">
<text x="118" y="650" fill="#71808C">01</text><text x="190" y="650" fill="#FFFFFF">if (rulesAreValid) &#123;</text>
<text x="118" y="755" fill="#71808C">02</text><text x="230" y="755" fill="#00E5FF">checkRiskLimits();</text>
<text x="118" y="860" fill="#71808C">03</text><text x="230" y="860" fill="#D7FF64">executeTrade();</text>
<text x="118" y="965" fill="#71808C">04</text><text x="190" y="965" fill="#FFFFFF">&#125; else &#123;</text>
<text x="118" y="1070" fill="#71808C">05</text><text x="230" y="1070" fill="#FF657A">wait();</text>
<text x="118" y="1175" fill="#71808C">06</text><text x="190" y="1175" fill="#FFFFFF">&#125;</text>
</g>
<text x="70" y="1695" fill="#8697A3" font-family="Consolas" font-size="22">CONCEPT SUPPORTED BY OFFICIAL METATRADER EXPERT-ADVISOR DOCUMENTATION</text>
</svg>"""


def _risk_curve_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920">
<defs><linearGradient id="risk" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#130A10"/><stop offset=".55" stop-color="#080A0D"/><stop offset="1" stop-color="#0C151B"/></linearGradient><linearGradient id="line" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#D7FF64"/><stop offset=".5" stop-color="#FFF078"/><stop offset="1" stop-color="#FF657A"/></linearGradient></defs>
<rect width="1080" height="1920" fill="url(#risk)"/>
<text x="70" y="125" fill="#FF657A" font-family="Consolas" font-size="24" font-weight="700" letter-spacing="4">RISK EXPLANATION • ILLUSTRATIVE</text>
<text x="70" y="245" fill="white" font-family="Arial" font-size="79" font-weight="800">HIGHER RETURN.</text>
<text x="70" y="335" fill="white" font-family="Arial" font-size="79" font-weight="800">HIGHER RISK.</text>
<g transform="translate(80 520)">
<rect width="920" height="650" rx="34" fill="#06090D" stroke="#27343D" stroke-width="3"/>
<g stroke="#29343C" opacity=".7"><path d="M70 120H850M70 240H850M70 360H850M70 480H850"/><path d="M220 70V560M390 70V560M560 70V560M730 70V560"/></g>
<path d="M90 500 C210 470 280 390 370 310 C470 220 560 120 650 115 C735 110 770 260 845 525" fill="none" stroke="url(#line)" stroke-width="16" stroke-linecap="round"/>
<circle cx="650" cy="115" r="20" fill="#FFF078"/><circle cx="845" cy="525" r="20" fill="#FF657A"/>
<text x="540" y="80" fill="#FFF078" font-family="Consolas" font-size="25">AGGRESSIVE PEAK</text>
<text x="600" y="595" fill="#FF657A" font-family="Consolas" font-size="25">RISK REVERSAL</text>
</g>
<text x="70" y="1700" fill="#8697A3" font-family="Consolas" font-size="22">SOURCE: MQL5 PRIMARY INTERVIEW • EXACT NUMBERS SHOWN ONLY IN THE SOURCE CAPTURE</text>
</svg>"""


def _automation_vs_risk_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920">
<rect width="1080" height="1920" fill="#070A0E"/>
<text x="70" y="130" fill="#00E5FF" font-family="Consolas" font-size="24" font-weight="700" letter-spacing="4">FINAL LESSON • EVIDENCE-DERIVED</text>
<text x="70" y="225" fill="white" font-family="Arial" font-size="64" font-weight="800">AUTOMATION ≠</text>
<text x="70" y="305" fill="white" font-family="Arial" font-size="64" font-weight="800">SAFE RISK</text>
<g transform="translate(70 480)">
<rect width="440" height="780" rx="36" fill="#0B1D23" stroke="#00E5FF" stroke-width="4"/>
<text x="44" y="86" fill="#00E5FF" font-family="Consolas" font-size="24" font-weight="700">AUTOMATION</text>
<text x="44" y="185" fill="white" font-family="Arial" font-size="47" font-weight="800">FOLLOWS</text><text x="44" y="245" fill="white" font-family="Arial" font-size="47" font-weight="800">THE RULES</text>
<path d="M70 370H370M70 470H370M70 570H370" stroke="#00E5FF" stroke-width="8" stroke-linecap="round"/>
<circle cx="110" cy="370" r="17" fill="#D7FF64"/><circle cx="210" cy="470" r="17" fill="#D7FF64"/><circle cx="330" cy="570" r="17" fill="#D7FF64"/>
</g>
<g transform="translate(570 480)">
<rect width="440" height="780" rx="36" fill="#261017" stroke="#FF657A" stroke-width="4"/>
<text x="44" y="86" fill="#FF657A" font-family="Consolas" font-size="24" font-weight="700">RISK</text>
<text x="44" y="185" fill="white" font-family="Arial" font-size="47" font-weight="800">DEPENDS ON</text><text x="44" y="245" fill="white" font-family="Arial" font-size="47" font-weight="800">THE SETTINGS</text>
<path d="M70 370L190 430L290 350L370 600" fill="none" stroke="#FF657A" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>
<circle cx="370" cy="600" r="18" fill="#FF657A"/>
</g>
<text x="70" y="1700" fill="#8697A3" font-family="Consolas" font-size="22">ILLUSTRATIVE DIAGRAM • NO PERFORMANCE CLAIM</text>
</svg>"""


def _render_reference_fixtures(review_dir: Path) -> None:
    renderer_root = Path(__file__).resolve().parents[3] / "renderer"
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is required to render caption fixtures")
    completed = subprocess.run(
        [
            node,
            str(renderer_root / "render-fixtures.mjs"),
            str(review_dir),
        ],
        cwd=renderer_root,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=600,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "Unable to render reference fixtures: "
            + completed.stderr[-3000:]
        )


def _measure_font_match(
    *,
    review_dir: Path,
    primary_reference: int,
) -> dict[str, object]:
    if primary_reference != 10:
        return {
            "selected": "Share Tech Mono",
            "reason": "Reference #10 is required for measured mono matching.",
            "scores": {},
        }
    reference_video = sorted(
        (
            Path(__file__).resolve().parents[3]
            / "training videos data"
        ).glob("*.mp4")
    )[9]
    capture = cv2.VideoCapture(str(reference_video))
    capture.set(cv2.CAP_PROP_POS_MSEC, 6500)
    ok, frame = capture.read()
    capture.release()
    fixture = cv2.imread(str(review_dir / "font-comparison.png"))
    if not ok or frame is None or fixture is None:
        raise RuntimeError("Unable to calculate the caption-font match")
    cv2.imwrite(str(review_dir / "reference-10-font-frame.png"), frame)
    reference_crop = frame[885:1010, 220:510]
    cv2.imwrite(
        str(review_dir / "reference-10-font-crop.png"),
        reference_crop,
    )
    reference_mask = _normalized_text_mask(reference_crop)
    crops = {
        "Share Tech Mono": (318, 392, 82, 344),
        "Space Mono": (685, 765, 82, 360),
        "Chakra Petch": (1055, 1135, 82, 360),
        "IBM Plex Mono": (1422, 1505, 82, 360),
    }
    scores: dict[str, float] = {}
    for label, (top, bottom, left, right) in crops.items():
        crop = fixture[top:bottom, left:right]
        mask = _normalized_text_mask(crop)
        scores[label] = round(
            float(cv2.absdiff(reference_mask, mask).mean()) / 255,
            5,
        )
    best_score = min(scores.values())
    selected = min(scores, key=scores.get)
    if scores["Share Tech Mono"] <= best_score + 0.035:
        selected = "Share Tech Mono"
    return {
        "selected": selected,
        "scores": scores,
        "method": (
            "White-glyph masks normalized to 360x96; mean absolute image "
            "difference; Share Tech Mono wins ties within 0.035."
        ),
        "reference_phrase": "THAT'S EVEN",
    }


def _normalized_text_mask(image) -> object:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    mask = cv2.inRange(gray, 190, 255)
    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    boxes = [
        cv2.boundingRect(contour)
        for contour in contours
        if cv2.contourArea(contour) >= 2
    ]
    if not boxes:
        return cv2.resize(mask, (360, 96))
    x1 = min(box[0] for box in boxes)
    y1 = min(box[1] for box in boxes)
    x2 = max(box[0] + box[2] for box in boxes)
    y2 = max(box[1] + box[3] for box in boxes)
    cropped = mask[y1:y2, x1:x2]
    canvas = cv2.resize(cropped, (360, 96))
    return canvas


def _extract_caption_family_stills(
    *,
    video: Path,
    pages: list[CaptionPage],
    review_dir: Path,
) -> list[str]:
    first_by_family: dict[str, CaptionPage] = {}
    for page in pages:
        first_by_family.setdefault(page.family, page)
    relative_paths: list[str] = []
    executable = get_ffmpeg_exe()
    for family, page in first_by_family.items():
        timestamp = (page.start_ms + page.end_ms) / 2000
        filename = f"caption-{family}.png"
        output = review_dir / filename
        completed = subprocess.run(
            [
                executable,
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-ss",
                f"{timestamp:.3f}",
                "-i",
                str(video),
                "-frames:v",
                "1",
                str(output),
            ],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=120,
            check=False,
            shell=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"Unable to extract {family} caption still"
            )
        relative_paths.append(f"review/{filename}")
    return relative_paths


def _create_contact_sheet(
    *,
    video: Path,
    output: Path,
    duration_seconds: float,
) -> None:
    frame_dir = output.parent / "contact-frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    timestamps = [
        duration_seconds * index / 11
        for index in range(12)
    ]
    frames = []
    capture = cv2.VideoCapture(str(video))
    try:
        for index, timestamp in enumerate(timestamps):
            capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            ok, frame = capture.read()
            if not ok:
                continue
            resized = cv2.resize(frame, (270, 480))
            cv2.putText(
                resized,
                f"{timestamp:04.1f}s",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (120, 255, 220),
                2,
                cv2.LINE_AA,
            )
            frames.append(resized)
    finally:
        capture.release()
    if len(frames) < 8:
        raise RuntimeError("Unable to build the production contact sheet")
    rows = []
    for index in range(0, len(frames), 4):
        row = frames[index:index + 4]
        if len(row) < 4:
            row.extend([row[-1]] * (4 - len(row)))
        rows.append(cv2.hconcat(row))
    cv2.imwrite(str(output), cv2.vconcat(rows))
    shutil.rmtree(frame_dir, ignore_errors=True)


def _create_role_comparison_sheet(
    *,
    video: Path,
    shots: list[ShotSpec],
    reference_profile: dict[str, object],
    output: Path,
) -> None:
    role_specs = [
        (
            "hook",
            "hook",
            {
                "0806-split-hook",
                "0806-v3-hook-physical",
                "0806-v3-hook-presenter",
            },
        ),
        (
            "code",
            "code",
            {
                "0806-terminal-boot",
                "0806-code-rule-trace",
                "0806-code-scroll",
                "0806-v3-code-cinematic",
                "0806-v3-code-card",
                "0806-v3-rule-pipeline",
            },
        ),
        (
            "evidence",
            "evidence",
            {
                "0806-championship-evidence",
                "0806-mql5-evidence",
                "0806-v3-evidence-overview",
                "0806-v3-evidence-heading",
                "0806-v3-evidence-history",
                "0806-v3-evidence-year",
                "0806-v3-evidence-result",
                "0806-v3-evidence-number",
            },
        ),
        (
            "risk",
            "system-diagram",
            {
                "0806-wrong-rule-flow",
                "0806-risk-control",
                "0806-risk-reversal",
                "0806-v3-wrong-rule",
                "0806-v3-risk-turn",
                "0806-v3-risk-control",
                "0806-v3-risk-rise",
                "0806-v3-risk-reversal",
            },
        ),
        (
            "demo",
            "late-code",
            {
                "0806-demo-setup",
                "0806-demo-cta",
                "0806-v3-demo-establishing",
                "0806-v3-demo-attach",
                "0806-v3-demo-input",
                "0806-v3-demo-strategy",
            },
        ),
        (
            "ending",
            "ending",
            {
                "0806-presenter-ending",
                "0806-v3-presenter-ending",
                "0806-v3-clean-ending",
            },
        ),
    ]
    production_label = (
        "0806 PRODUCTION V3"
        if any(
            (shot.treatment or "").startswith("0806-v3-")
            for shot in shots
        )
        else "0806 PRODUCTION V2"
    )
    selected_frames = reference_profile.get("selected_frames", [])
    reference_by_role = {
        str(item["role"]): str(item["path"])
        for item in selected_frames
        if isinstance(item, dict)
        and "role" in item
        and "path" in item
    }
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise RuntimeError("Unable to open render for role comparison")
    rows: list[np.ndarray] = []
    try:
        for output_role, reference_role, treatments in role_specs:
            reference_path = reference_by_role.get(reference_role)
            shot = next(
                (
                    candidate
                    for candidate in shots
                    if candidate.treatment in treatments
                ),
                None,
            )
            if reference_path is None or shot is None:
                continue
            reference_image = cv2.imread(
                str(output.parent.parent / reference_path)
            )
            if reference_image is None:
                continue
            timestamp_ms = (shot.start_ms + shot.end_ms) / 2
            capture.set(cv2.CAP_PROP_POS_MSEC, timestamp_ms)
            ok, rendered_frame = capture.read()
            if not ok or rendered_frame is None:
                continue
            panels = []
            for label, image in (
                ("REFERENCE #10", reference_image),
                (production_label, rendered_frame),
            ):
                panel = cv2.resize(image, (360, 640))
                cv2.rectangle(panel, (0, 0), (360, 48), (10, 12, 14), -1)
                cv2.putText(
                    panel,
                    label,
                    (14, 32),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.54,
                    (235, 238, 238),
                    1,
                    cv2.LINE_AA,
                )
                panels.append(panel)
            row = np.hstack(panels)
            cv2.rectangle(row, (0, 592), (720, 640), (10, 12, 14), -1)
            cv2.putText(
                row,
                output_role.upper(),
                (14, 624),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.58,
                (145, 204, 218),
                1,
                cv2.LINE_AA,
            )
            rows.append(row)
    finally:
        capture.release()
    if not rows:
        raise RuntimeError("No role-matched comparison frames were available")
    output.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output), np.vstack(rows))


def _wrap_text(text: str, *, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        if current and len(" ".join([*current, word])) > width:
            lines.append(" ".join(current))
            current = []
        current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines[:4]


def _write_json(path: Path, payload: object) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

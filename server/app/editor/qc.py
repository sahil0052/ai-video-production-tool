import json
import os
from pathlib import Path
import re
import statistics
import subprocess

import cv2
from imageio_ffmpeg import get_ffmpeg_exe
import numpy as np

from app.models import (
    CaptionPage,
    EditPlanV1,
    QCCheck,
    QCMeasurements,
    QCReport,
)


def calculate_meaningful_visual_coverage(plan: EditPlanV1) -> float:
    if plan.duration_ms <= 0:
        return 0
    referenced_visual_ids = {
        scene.visual_id
        for scene in plan.scenes
        if scene.visual_id is not None and scene.layout != "presenter"
    }
    intervals = [
        (visual.start_ms, visual.end_ms)
        for visual in plan.editorial_visuals
        if visual.id in referenced_visual_ids
    ] + [
        (scene.start_ms, scene.end_ms)
        for scene in plan.scenes
        if scene.treatment is not None
        and scene.motion != "static"
        and scene.layout != "presenter"
    ] + [
        (cue.start_ms, cue.end_ms)
        for cue in plan.graphics
        if cue.kind in {"browser", "phone", "chat"}
    ] + [
        (asset.start_ms, asset.end_ms)
        for asset in plan.assets
        if asset.kind in {"image", "video"}
        and asset.start_ms is not None
        and asset.end_ms is not None
    ]
    if not intervals:
        return 0
    intervals.sort()
    merged: list[tuple[int, int]] = []
    for start, end in intervals:
        clipped_start = max(0, start)
        clipped_end = min(plan.duration_ms, end)
        if clipped_end <= clipped_start:
            continue
        if not merged or clipped_start > merged[-1][1]:
            merged.append((clipped_start, clipped_end))
        else:
            merged[-1] = (
                merged[-1][0],
                max(merged[-1][1], clipped_end),
            )
    covered = sum(end - start for start, end in merged)
    return min(1.0, covered / plan.duration_ms)


def measure_qc(
    *,
    output: Path,
    plan: EditPlanV1,
) -> QCMeasurements:
    integrated_lufs, true_peak_dbtp = _measure_loudness(output)
    samples, sample_rate = _extract_audio(output)
    longest_silence_ms = _measure_longest_silence(samples, sample_rate)
    black_frame_ratio, freeze_frame_ratio = _measure_video_frames(output)
    visual_events = _visual_event_times(plan)
    major_events = _major_visual_event_times(plan)
    duration_minutes = max(plan.duration_ms / 60_000, 1 / 60_000)
    cuts_per_minute = len(visual_events) / duration_minutes
    boundaries = [0, *visual_events, plan.duration_ms]
    shot_lengths = [
        right - left
        for left, right in zip(boundaries, boundaries[1:])
        if right > left
    ]
    median_shot_ms = (
        round(statistics.median(shot_lengths))
        if shot_lengths
        else plan.duration_ms
    )
    cut_onset_percent = _measure_cut_onsets(
        samples,
        sample_rate,
        major_events,
    )
    caption_overflow_count = sum(
        1 for page in plan.caption_pages if _caption_page_overflows(page)
    )
    return QCMeasurements(
        integrated_lufs=integrated_lufs,
        true_peak_dbtp=true_peak_dbtp,
        longest_silence_ms=longest_silence_ms,
        black_frame_ratio=black_frame_ratio,
        freeze_frame_ratio=freeze_frame_ratio,
        cuts_per_minute=cuts_per_minute,
        median_shot_ms=median_shot_ms,
        cut_onset_percent=cut_onset_percent,
        caption_overflow_count=caption_overflow_count,
        meaningful_visual_coverage=calculate_meaningful_visual_coverage(
            plan
        ),
    )


def _measure_loudness(path: Path) -> tuple[float, float]:
    command = [
        get_ffmpeg_exe(),
        "-hide_banner",
        "-i",
        str(path),
        "-map",
        "0:a:0",
        "-af",
        "loudnorm=I=-14.2:TP=-1:LRA=5:print_format=json",
        "-f",
        "null",
        os.devnull,
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=300,
        check=False,
        shell=False,
    )
    matches = re.findall(r"\{\s*\"input_i\".*?\}", completed.stderr, re.S)
    if completed.returncode != 0 or not matches:
        raise RuntimeError("Unable to measure output loudness")
    payload = json.loads(matches[-1])
    return float(payload["input_i"]), float(payload["input_tp"])


def _extract_audio(path: Path) -> tuple[np.ndarray, int]:
    sample_rate = 16_000
    command = [
        get_ffmpeg_exe(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(path),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-f",
        "f32le",
        "pipe:1",
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        timeout=300,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("Unable to decode output audio")
    return np.frombuffer(completed.stdout, dtype="<f4"), sample_rate


def measure_cut_onsets_for_video(
    path: Path,
    event_times_ms: list[int],
) -> float:
    samples, sample_rate = _extract_audio(path)
    return _measure_cut_onsets(samples, sample_rate, event_times_ms)


def measure_reference_cut_onsets_for_video(
    path: Path,
    event_times_ms: list[int],
) -> float:
    samples, sample_rate = _extract_audio(path)
    return _measure_reference_cut_onsets(
        samples,
        sample_rate,
        event_times_ms,
    )


def _measure_reference_cut_onsets(
    samples: np.ndarray,
    sample_rate: int,
    event_times_ms: list[int],
) -> float:
    if not event_times_ms or samples.size == 0:
        return 100.0
    window_size = max(1, round(sample_rate * 0.02))
    usable = samples[: samples.size - samples.size % window_size]
    if usable.size == 0:
        return 0.0
    frames = usable.reshape(-1, window_size)
    rms = np.sqrt(np.mean(np.square(frames), axis=1) + 1e-12)
    db = 20 * np.log10(rms + 1e-9)
    onset_strength = np.maximum(0.0, np.diff(db, prepend=db[0]))
    threshold = max(2.0, float(np.percentile(onset_strength, 85)))
    candidate_indexes = np.flatnonzero(onset_strength >= threshold)
    accents: list[float] = []
    for index in candidate_indexes:
        timestamp = float(index * window_size / sample_rate)
        if accents and timestamp - accents[-1] < 0.12:
            continue
        accents.append(timestamp)
    aligned = sum(
        any(abs(event_ms / 1000 - accent) <= 0.1 for accent in accents)
        for event_ms in event_times_ms
    )
    return aligned / len(event_times_ms) * 100


def _measure_longest_silence(samples: np.ndarray, sample_rate: int) -> int:
    if samples.size == 0:
        return 0
    window_size = max(1, round(sample_rate * 0.02))
    usable = samples[: samples.size - samples.size % window_size]
    if usable.size == 0:
        return 0
    frames = usable.reshape(-1, window_size)
    rms = np.sqrt(np.mean(np.square(frames), axis=1) + 1e-12)
    silent = 20 * np.log10(rms) < -45
    longest = current = 0
    for is_silent in silent:
        current = current + 1 if is_silent else 0
        longest = max(longest, current)
    return round(longest * window_size / sample_rate * 1000)


def _measure_video_frames(path: Path) -> tuple[float, float]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError("Unable to inspect rendered video frames")
    fps = max(1.0, float(capture.get(cv2.CAP_PROP_FPS)))
    sample_every = max(1, round(fps / 5))
    sampled = black = frozen = 0
    previous: np.ndarray | None = None
    frame_index = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame_index % sample_every:
                frame_index += 1
                continue
            gray = cv2.cvtColor(cv2.resize(frame, (96, 170)), cv2.COLOR_BGR2GRAY)
            sampled += 1
            if _is_black_frame(gray):
                black += 1
            if previous is not None and float(np.mean(cv2.absdiff(gray, previous))) < 0.2:
                frozen += 1
            previous = gray
            frame_index += 1
    finally:
        capture.release()
    if sampled == 0:
        return 1.0, 1.0
    return black / sampled, frozen / max(1, sampled - 1)


def _is_black_frame(gray: np.ndarray) -> bool:
    if gray.size == 0:
        return True
    mean_luminance = float(np.mean(gray))
    bright_pixel_ratio = float(np.mean(gray > 32))
    return mean_luminance < 8 and bright_pixel_ratio < 0.002


def _caption_page_overflows(page: CaptionPage) -> bool:
    text = " ".join(token.text for token in page.tokens)
    limits = {
        "technical-mono": (5, 36),
        "compact-pill": (5, 36),
        "documentary-clean": (10, 72),
        "outlined-demo": (8, 56),
        "display-emphasis": (8, 48),
    }
    max_tokens, max_characters = limits[page.family]
    return len(page.tokens) > max_tokens or len(text) > max_characters


def _visual_event_times(plan: EditPlanV1) -> list[int]:
    event_times = {
        segment.output_start_ms for segment in plan.timeline[1:]
    } | {scene.start_ms for scene in plan.scenes[1:]} | {
        cue.start_ms for cue in plan.graphics[1:]
    }
    return sorted(time for time in event_times if 0 < time < plan.duration_ms)


def _major_visual_event_times(plan: EditPlanV1) -> list[int]:
    event_times = {scene.start_ms for scene in plan.scenes[1:]} | {
        cue.start_ms for cue in plan.graphics[1:]
    }
    return sorted(time for time in event_times if 0 < time < plan.duration_ms)


def _measure_cut_onsets(
    samples: np.ndarray,
    sample_rate: int,
    event_times_ms: list[int],
) -> float:
    if not event_times_ms or samples.size == 0:
        return 100.0
    window_size = max(1, round(sample_rate * 0.02))
    usable = samples[: samples.size - samples.size % window_size]
    if usable.size == 0:
        return 0.0
    frames = usable.reshape(-1, window_size)
    envelope = np.sqrt(np.mean(np.square(frames), axis=1) + 1e-12)
    onset = np.maximum(0, np.diff(envelope, prepend=envelope[0]))
    positive = onset[onset > 0]
    baseline = float(np.median(positive)) if positive.size else 0
    threshold = baseline * 2.0
    matched = 0
    for event_ms in event_times_ms:
        center = round(event_ms / 1000 * sample_rate / window_size)
        left = max(0, center - 5)
        right = min(onset.size, center + 6)
        if right > left and float(np.max(onset[left:right])) >= threshold:
            matched += 1
    return matched / len(event_times_ms) * 100


def evaluate_qc(
    plan: EditPlanV1,
    measurements: QCMeasurements,
    *,
    repair_attempts: int = 0,
) -> QCReport:
    targets = plan.qc_targets
    checks_with_weights = [
        (
            QCCheck(
                name="loudness",
                passed=abs(
                    measurements.integrated_lufs - targets.integrated_lufs
                )
                <= targets.loudness_tolerance,
                measured=measurements.integrated_lufs,
                target=f"{targets.integrated_lufs}±{targets.loudness_tolerance} LUFS",
            ),
            12,
        ),
        (
            QCCheck(
                name="true_peak",
                passed=measurements.true_peak_dbtp <= targets.true_peak_dbtp,
                measured=measurements.true_peak_dbtp,
                target=f"≤ {targets.true_peak_dbtp} dBTP",
            ),
            8,
        ),
        (
            QCCheck(
                name="silence",
                passed=measurements.longest_silence_ms <= targets.max_silence_ms,
                measured=measurements.longest_silence_ms,
                target=f"≤ {targets.max_silence_ms} ms",
            ),
            12,
        ),
        (
            QCCheck(
                name="black_frames",
                passed=measurements.black_frame_ratio
                <= targets.max_black_frame_ratio,
                measured=round(measurements.black_frame_ratio, 4),
                target=f"≤ {targets.max_black_frame_ratio}",
            ),
            12,
        ),
        (
            QCCheck(
                name="freeze_frames",
                passed=measurements.freeze_frame_ratio
                <= targets.max_freeze_frame_ratio,
                measured=round(measurements.freeze_frame_ratio, 4),
                target=f"≤ {targets.max_freeze_frame_ratio}",
            ),
            4,
        ),
        (
            QCCheck(
                name="pacing",
                passed=targets.min_cuts_per_minute
                <= measurements.cuts_per_minute
                <= targets.max_cuts_per_minute,
                measured=round(measurements.cuts_per_minute, 1),
                target=(
                    f"{targets.min_cuts_per_minute:g}–"
                    f"{targets.max_cuts_per_minute:g} cuts/min"
                ),
            ),
            8,
        ),
        (
            QCCheck(
                name="shot_length",
                passed=targets.min_median_shot_ms
                <= measurements.median_shot_ms
                <= targets.max_median_shot_ms,
                measured=measurements.median_shot_ms,
                target=(
                    f"{targets.min_median_shot_ms}–"
                    f"{targets.max_median_shot_ms} ms"
                ),
            ),
            8,
        ),
        (
            QCCheck(
                name="cut_onsets",
                passed=measurements.cut_onset_percent
                >= targets.min_cut_onset_percent,
                measured=round(measurements.cut_onset_percent, 1),
                target=f"≥ {targets.min_cut_onset_percent:g}%",
            ),
            8,
        ),
        (
            QCCheck(
                name="caption_overflow",
                passed=measurements.caption_overflow_count == 0,
                measured=measurements.caption_overflow_count,
                target=0,
            ),
            8,
        ),
        (
            QCCheck(
                name="meaningful_visuals",
                passed=measurements.meaningful_visual_coverage
                >= targets.min_meaningful_visual_coverage,
                measured=round(
                    measurements.meaningful_visual_coverage,
                    3,
                ),
                target=(
                    f">= {targets.min_meaningful_visual_coverage:.2f}"
                ),
            ),
            20,
        ),
    ]
    checks = [check for check, _weight in checks_with_weights]
    style_score = float(
        sum(weight for check, weight in checks_with_weights if check.passed)
    )
    essential_names = {
        "loudness",
        "true_peak",
        "silence",
        "black_frames",
        "freeze_frames",
        "caption_overflow",
        "meaningful_visuals",
        "cut_onsets",
    }
    essential_passed = all(
        check.passed for check in checks if check.name in essential_names
    )
    return QCReport(
        passed=essential_passed and style_score >= targets.min_style_score,
        style_score=style_score,
        checks=checks,
        repair_attempts=repair_attempts,
    )

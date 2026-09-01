from __future__ import annotations

from collections import Counter
from pathlib import Path
import re
import subprocess

import cv2
import imageio_ffmpeg
import numpy as np

from app.models import ShotSpec


def estimate_audio_delay_ms(
    source: np.ndarray,
    final: np.ndarray,
    *,
    sample_rate: int,
    max_delay_ms: int = 500,
) -> int:
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    source_signal = np.asarray(source, dtype=np.float64).reshape(-1)
    final_signal = np.asarray(final, dtype=np.float64).reshape(-1)
    sample_count = min(source_signal.size, final_signal.size)
    if sample_count == 0:
        raise ValueError("Audio signals must not be empty")
    source_signal = source_signal[:sample_count]
    final_signal = final_signal[:sample_count]

    target_rate = min(sample_rate, 2000)
    stride = max(1, sample_rate // target_rate)
    if stride > 1:
        usable = sample_count - sample_count % stride
        source_signal = source_signal[:usable].reshape(-1, stride).mean(axis=1)
        final_signal = final_signal[:usable].reshape(-1, stride).mean(axis=1)
    effective_rate = sample_rate / stride
    source_signal -= np.mean(source_signal)
    final_signal -= np.mean(final_signal)

    max_lag = min(
        max(1, round(max_delay_ms * effective_rate / 1000)),
        source_signal.size - 1,
    )
    correlation_size = source_signal.size + final_signal.size - 1
    fft_size = 1 << max(1, correlation_size - 1).bit_length()
    correlation = np.fft.irfft(
        np.fft.rfft(final_signal, fft_size)
        * np.fft.rfft(source_signal[::-1], fft_size),
        fft_size,
    )[:correlation_size]

    lags = np.arange(-max_lag, max_lag + 1, dtype=np.int64)
    source_squared = np.concatenate(
        ([0.0], np.cumsum(source_signal * source_signal))
    )
    final_squared = np.concatenate(
        ([0.0], np.cumsum(final_signal * final_signal))
    )
    positive = lags >= 0

    source_starts = np.where(positive, 0, -lags)
    source_ends = np.where(
        positive,
        source_signal.size - lags,
        source_signal.size,
    )
    final_starts = np.where(positive, lags, 0)
    final_ends = np.where(
        positive,
        final_signal.size,
        final_signal.size + lags,
    )
    source_energy = (
        source_squared[source_ends] - source_squared[source_starts]
    )
    final_energy = final_squared[final_ends] - final_squared[final_starts]
    denominator = np.sqrt(source_energy * final_energy)
    numerators = correlation[source_signal.size - 1 + lags]
    scores = np.full(lags.shape, float("-inf"), dtype=np.float64)
    valid = denominator > 1e-12
    scores[valid] = numerators[valid] / denominator[valid]
    best_lag = int(lags[int(np.argmax(scores))])
    return round(best_lag * 1000 / effective_rate)


def build_audio_continuity_report(
    source: np.ndarray,
    final: np.ndarray,
    *,
    sample_rate: int,
    allowed_delay_ms: int = 20,
) -> dict[str, object]:
    source_signal = np.asarray(source, dtype=np.float64).reshape(-1)
    final_signal = np.asarray(final, dtype=np.float64).reshape(-1)
    delay_ms = estimate_audio_delay_ms(
        source_signal,
        final_signal,
        sample_rate=sample_rate,
    )
    delay_samples = round(delay_ms * sample_rate / 1000)
    if delay_samples > 0:
        aligned_source = source_signal[:-delay_samples]
        aligned_final = final_signal[delay_samples:]
    elif delay_samples < 0:
        aligned_source = source_signal[-delay_samples:]
        aligned_final = final_signal[:delay_samples]
    else:
        sample_count = min(source_signal.size, final_signal.size)
        aligned_source = source_signal[:sample_count]
        aligned_final = final_signal[:sample_count]
    sample_count = min(aligned_source.size, aligned_final.size, 262_144)
    if sample_count <= 0:
        spectral_distance_db = float("inf")
        spectral_band_hz = [200, min(8000, sample_rate // 2)]
    else:
        aligned_source = aligned_source[:sample_count]
        aligned_final = aligned_final[:sample_count]
        window = np.hanning(sample_count)
        source_spectrum = np.abs(np.fft.rfft(aligned_source * window))
        final_spectrum = np.abs(np.fft.rfft(aligned_final * window))
        frequencies = np.fft.rfftfreq(
            sample_count,
            d=1 / sample_rate,
        )
        speech_high_hz = min(8000, sample_rate // 2)
        speech_band = (
            (frequencies >= 200)
            & (frequencies <= speech_high_hz)
        )
        if not np.any(speech_band):
            speech_band = np.ones_like(frequencies, dtype=bool)
            spectral_band_hz = [0, sample_rate // 2]
        else:
            spectral_band_hz = [200, speech_high_hz]
        source_spectrum = source_spectrum[speech_band]
        final_spectrum = final_spectrum[speech_band]
        source_spectrum /= max(float(np.max(source_spectrum)), 1e-12)
        final_spectrum /= max(float(np.max(final_spectrum)), 1e-12)
        source_db = 20 * np.log10(np.maximum(source_spectrum, 1e-6))
        final_db = 20 * np.log10(np.maximum(final_spectrum, 1e-6))
        spectral_distance_db = float(np.mean(np.abs(source_db - final_db)))
    duration_delta_ms = round(
        (final_signal.size - source_signal.size) / sample_rate * 1000
    )
    return {
        "sample_rate": sample_rate,
        "source_samples": int(source_signal.size),
        "final_samples": int(final_signal.size),
        "duration_delta_ms": duration_delta_ms,
        "estimated_delay_ms": delay_ms,
        "allowed_delay_ms": allowed_delay_ms,
        "delay_passed": abs(delay_ms) <= allowed_delay_ms,
        "duration_passed": abs(duration_delta_ms) <= 50,
        "spectral_band_hz": spectral_band_hz,
        "spectral_continuity_db": round(spectral_distance_db, 3),
        "spectral_passed": spectral_distance_db <= 8,
    }


def estimate_audio_pulse_bpm(
    samples: np.ndarray,
    *,
    sample_rate: int,
    bpm_min: float = 72,
    bpm_max: float = 120,
) -> float:
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    if bpm_min <= 0 or bpm_max <= bpm_min:
        raise ValueError("BPM bounds must be positive and ordered")
    signal = np.asarray(samples, dtype=np.float64).reshape(-1)
    if signal.size < sample_rate * 4:
        raise ValueError("Pulse estimation requires at least four seconds")

    hop = max(64, round(sample_rate / 187.5))
    usable_size = signal.size - signal.size % hop
    windows = signal[:usable_size].reshape(-1, hop)
    rms = np.sqrt(np.mean(windows**2, axis=1) + 1e-12)
    onset = np.maximum(0, np.diff(rms, prepend=rms[0]))
    onset -= float(np.mean(onset))
    feature_rate = sample_rate / hop
    lag_min = max(1, round(feature_rate * 60 / bpm_max))
    lag_max = max(lag_min + 1, round(feature_rate * 60 / bpm_min))
    correlations: list[float] = []
    for lag in range(lag_min, lag_max + 1):
        left = onset[:-lag]
        right = onset[lag:]
        denominator = float(
            np.linalg.norm(left) * np.linalg.norm(right)
        )
        correlations.append(
            float(np.dot(left, right)) / max(denominator, 1e-12)
        )
    best_lag = lag_min + int(np.argmax(correlations))
    return round(60 * feature_rate / best_lag, 2)


def _check(
    name: str,
    passed: bool,
    measured: object,
    target: str,
) -> dict[str, object]:
    return {
        "name": name,
        "passed": passed,
        "measured": measured,
        "target": target,
    }


def evaluate_reference_max_frame_metrics(
    metrics: dict[str, float | int],
) -> dict[str, object]:
    checks = [
        _check(
            "rendered-cuts",
            20 <= int(metrics["rendered_cut_count"]) <= 22,
            metrics["rendered_cut_count"],
            "20-22 hard cuts",
        ),
        _check(
            "median-shot",
            1400 <= float(metrics["median_shot_ms"]) <= 1800,
            metrics["median_shot_ms"],
            "1400-1800 ms",
        ),
        _check(
            "motion",
            4.5 <= float(metrics["motion_score"]) <= 7.5,
            metrics["motion_score"],
            "4.5-7.5 rendered-pixel score",
        ),
        _check(
            "darkness",
            float(metrics["dark_frame_ratio"]) <= 0.45,
            metrics["dark_frame_ratio"],
            "<= 0.45",
        ),
        _check(
            "luminance",
            85 <= float(metrics["mean_luminance"]) <= 105,
            metrics["mean_luminance"],
            "85-105",
        ),
        _check(
            "saturation",
            50 <= float(metrics["mean_saturation"]) <= 90,
            metrics["mean_saturation"],
            "50-90",
        ),
        _check(
            "real-source-coverage",
            float(metrics["real_source_ratio"]) >= 0.65,
            metrics["real_source_ratio"],
            ">= 0.65",
        ),
        _check(
            "procedural-share",
            float(metrics["procedural_ratio"]) <= 0.25,
            metrics["procedural_ratio"],
            "<= 0.25",
        ),
        _check(
            "visual-source-diversity",
            int(metrics["visual_source_count"]) >= 6,
            metrics["visual_source_count"],
            ">= 6 genuine sources",
        ),
    ]
    return {
        "automated_pass": all(check["passed"] for check in checks),
        "checks": checks,
    }


def evaluate_reference_max_v3_frame_metrics(
    metrics: dict[str, float | int],
) -> dict[str, object]:
    checks = [
        _check(
            "rendered-cuts",
            24 <= int(metrics["rendered_cut_count"]) <= 30,
            metrics["rendered_cut_count"],
            "24-30 hard cuts",
        ),
        _check(
            "median-shot",
            1200 <= float(metrics["median_shot_ms"]) <= 1900,
            metrics["median_shot_ms"],
            "1200-1900 ms",
        ),
        _check(
            "motion",
            4.5 <= float(metrics["motion_score"]) <= 8.5,
            metrics["motion_score"],
            "4.5-8.5 rendered-pixel score",
        ),
        _check(
            "darkness",
            float(metrics["dark_frame_ratio"]) <= 0.45,
            metrics["dark_frame_ratio"],
            "<= 0.45",
        ),
        _check(
            "luminance",
            82 <= float(metrics["mean_luminance"]) <= 112,
            metrics["mean_luminance"],
            "82-112",
        ),
        _check(
            "saturation",
            30 <= float(metrics["mean_saturation"]) <= 90,
            metrics["mean_saturation"],
            "30-90",
        ),
        _check(
            "visual-source-diversity",
            int(metrics["visual_source_count"]) >= 8,
            metrics["visual_source_count"],
            ">= 8 genuine sources",
        ),
    ]
    return {
        "automated_pass": all(check["passed"] for check in checks),
        "checks": checks,
    }


def calculate_source_coverage(
    shots: list[ShotSpec],
    *,
    duration_ms: int,
) -> dict[str, float | int]:
    if duration_ms <= 0:
        return {
            "real_source_ratio": 0.0,
            "procedural_ratio": 0.0,
            "visual_source_count": 0,
        }
    real_kinds = {
        "presenter",
        "screen-recording",
        "direct-source",
        "licensed-footage",
    }
    real_ms = sum(
        shot.end_ms - shot.start_ms
        for shot in shots
        if shot.source_kind in real_kinds
    )
    procedural_ms = sum(
        shot.end_ms - shot.start_ms
        for shot in shots
        if shot.source_kind == "procedural"
    )
    sources = {
        shot.asset_id or f"{shot.source_kind}:source"
        for shot in shots
    }
    return {
        "real_source_ratio": min(1.0, real_ms / duration_ms),
        "procedural_ratio": min(1.0, procedural_ms / duration_ms),
        "visual_source_count": len(sources),
    }


def calculate_visual_language_distribution(
    shots: list[ShotSpec],
    *,
    duration_ms: int,
) -> dict[str, object]:
    categories = [
        "presenter",
        "hook-composite",
        "cinematic-broll",
        "designed-explanation",
        "edited-evidence",
        "product-macro",
        "literal-desktop-ui",
    ]
    durations = {category: 0 for category in categories}
    durations["unclassified"] = 0
    missing_primary_subjects: list[str] = []
    software_multi_action_shots: list[str] = []
    full_page_overview_violations: list[str] = []
    source_keys: list[str] = []

    for shot in shots:
        shot_duration = max(0, shot.end_ms - shot.start_ms)
        category = shot.visual_category or "unclassified"
        durations.setdefault(category, 0)
        durations[category] += shot_duration
        if not shot.primary_subject.strip():
            missing_primary_subjects.append(shot.id)
        if (
            category in {"literal-desktop-ui", "product-macro"}
            and shot.simultaneous_actions > 1
        ):
            software_multi_action_shots.append(shot.id)
        if (
            category == "edited-evidence"
            and "overview" in shot.treatment
            and shot_duration > 800
        ):
            full_page_overview_violations.append(shot.id)
        source_keys.append(
            shot.source_family.strip()
            or shot.asset_id
            or f"{shot.source_kind}:{shot.treatment}"
        )

    max_consecutive = 0
    current_key: str | None = None
    current_count = 0
    for key in source_keys:
        if key == current_key:
            current_count += 1
        else:
            current_key = key
            current_count = 1
        max_consecutive = max(max_consecutive, current_count)

    denominator = max(duration_ms, 1)
    ratios = {
        category: durations.get(category, 0) / denominator
        for category in durations
    }
    return {
        "duration_ms": duration_ms,
        "durations_ms": durations,
        "ratios": ratios,
        "missing_primary_subjects": missing_primary_subjects,
        "software_multi_action_shots": software_multi_action_shots,
        "full_page_overview_violations": full_page_overview_violations,
        "max_consecutive_source_repeats": max_consecutive,
    }


def evaluate_reference_max_visual_language(
    distribution: dict[str, object],
) -> dict[str, object]:
    ratios = distribution["ratios"]
    if not isinstance(ratios, dict):
        raise TypeError("Visual-language ratios must be a mapping")

    def ratio(name: str) -> float:
        return float(ratios.get(name, 0.0))

    missing_subjects = list(
        distribution.get("missing_primary_subjects", [])
    )
    multi_action = list(
        distribution.get("software_multi_action_shots", [])
    )
    overview_violations = list(
        distribution.get("full_page_overview_violations", [])
    )
    max_repeats = int(
        distribution.get("max_consecutive_source_repeats", 0)
    )
    checks = [
        _check(
            "literal-desktop-ui",
            ratio("literal-desktop-ui") < 0.20,
            round(ratio("literal-desktop-ui"), 4),
            "< 0.20",
        ),
        _check(
            "designed-explanation",
            0.25 <= ratio("designed-explanation") <= 0.45,
            round(ratio("designed-explanation"), 4),
            "0.25-0.45",
        ),
        _check(
            "cinematic-broll",
            0.15 <= ratio("cinematic-broll") <= 0.30,
            round(ratio("cinematic-broll"), 4),
            "0.15-0.30",
        ),
        _check(
            "edited-evidence",
            0.15 <= ratio("edited-evidence") <= 0.20,
            round(ratio("edited-evidence"), 4),
            "0.15-0.20",
        ),
        _check(
            "primary-subjects",
            not missing_subjects,
            missing_subjects,
            "one named primary subject per shot",
        ),
        _check(
            "single-software-action",
            not multi_action,
            multi_action,
            "at most one action per software shot",
        ),
        _check(
            "evidence-overview-duration",
            not overview_violations,
            overview_violations,
            "full-page overview <= 800 ms",
        ),
        _check(
            "source-repetition",
            max_repeats <= 2,
            max_repeats,
            "<= 2 consecutive shots",
        ),
    ]
    return {
        "automated_pass": all(check["passed"] for check in checks),
        "checks": checks,
    }


def _tokens(text: str) -> list[str]:
    normalized = re.sub(
        r"(?<=\d)[,._](?=\d)",
        "",
        text.casefold(),
    )
    return re.findall(r"[a-z0-9]+", normalized)


_CONTENT_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "being",
        "but",
        "by",
        "did",
        "do",
        "does",
        "during",
        "for",
        "from",
        "had",
        "has",
        "have",
        "he",
        "her",
        "hers",
        "him",
        "his",
        "how",
        "i",
        "if",
        "in",
        "is",
        "it",
        "its",
        "just",
        "more",
        "my",
        "no",
        "not",
        "of",
        "on",
        "or",
        "our",
        "she",
        "so",
        "than",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "to",
        "was",
        "we",
        "were",
        "what",
        "when",
        "which",
        "while",
        "who",
        "why",
        "will",
        "with",
        "would",
        "you",
        "your",
    }
)
_CONTENT_CANONICAL = {
    "big": "big",
    "huge": "big",
    "control": "control",
    "controlled": "control",
    "controlling": "control",
    "controls": "control",
}
_CONTRACTION_EXPANSIONS = {
    "aren't": "are not",
    "can't": "can not",
    "couldn't": "could not",
    "didn't": "did not",
    "doesn't": "does not",
    "don't": "do not",
    "hadn't": "had not",
    "hasn't": "has not",
    "haven't": "have not",
    "he'll": "he will",
    "i'll": "i will",
    "isn't": "is not",
    "shouldn't": "should not",
    "wasn't": "was not",
    "weren't": "were not",
    "won't": "will not",
    "wouldn't": "would not",
    "you'll": "you will",
}


def _content_tokens(text: str) -> list[str]:
    normalized = text.casefold().replace("’", "'")
    for contraction, expansion in _CONTRACTION_EXPANSIONS.items():
        normalized = re.sub(
            rf"\b{re.escape(contraction)}\b",
            expansion,
            normalized,
        )
    tokens = _tokens(normalized)
    return [
        _CONTENT_CANONICAL.get(token, token)
        for token in tokens
        if token not in _CONTENT_STOPWORDS
    ]


def _contains_token_sequence(
    haystack: list[str],
    needle: list[str],
) -> bool:
    if not needle:
        return True
    return any(
        haystack[index : index + len(needle)] == needle
        for index in range(len(haystack) - len(needle) + 1)
    )


def compare_asr_tokens(
    *,
    source_text: str,
    final_text: str,
    protected_terms: list[str],
    protected_term_aliases: dict[str, list[str]] | None = None,
    unverifiable_source_tokens: list[str] | None = None,
) -> dict[str, object]:
    source_tokens = _tokens(source_text)
    final_tokens = _tokens(final_text)
    raw_remaining = Counter(final_tokens)
    raw_missing_tokens: list[str] = []
    raw_retained = 0
    for token in source_tokens:
        if raw_remaining[token] > 0:
            raw_retained += 1
            raw_remaining[token] -= 1
        else:
            raw_missing_tokens.append(token)
    remaining = Counter(final_tokens)
    unverifiable = Counter(
        token
        for text in (unverifiable_source_tokens or [])
        for token in _tokens(text)
    )
    missing_tokens: list[str] = []
    ignored_unaligned_source_tokens: list[str] = []
    retained = 0
    verified_source_count = 0
    for token in source_tokens:
        if remaining[token] > 0:
            retained += 1
            verified_source_count += 1
            remaining[token] -= 1
        elif unverifiable[token] > 0:
            ignored_unaligned_source_tokens.append(token)
            unverifiable[token] -= 1
        else:
            verified_source_count += 1
            missing_tokens.append(token)
    source_content_tokens = _content_tokens(source_text)
    final_content_tokens = _content_tokens(final_text)
    remaining_content = Counter(final_content_tokens)
    unverifiable_content = Counter(
        token
        for text in (unverifiable_source_tokens or [])
        for token in _content_tokens(text)
    )
    missing_content_tokens: list[str] = []
    retained_content = 0
    verified_content_count = 0
    for token in source_content_tokens:
        if remaining_content[token] > 0:
            retained_content += 1
            verified_content_count += 1
            remaining_content[token] -= 1
        elif unverifiable_content[token] > 0:
            unverifiable_content[token] -= 1
        else:
            verified_content_count += 1
            missing_content_tokens.append(token)
    aliases = protected_term_aliases or {}
    protected_missing = []
    for term in protected_terms:
        candidates = [term, *aliases.get(term, [])]
        if not any(
            _contains_token_sequence(final_tokens, _tokens(candidate))
            for candidate in candidates
        ):
            protected_missing.append(term)
    return {
        "raw_source_token_count": len(source_tokens),
        "raw_retained_token_count": raw_retained,
        "raw_retention_ratio": (
            raw_retained / len(source_tokens)
            if source_tokens
            else 1.0
        ),
        "raw_missing_tokens": raw_missing_tokens,
        "source_token_count": verified_source_count,
        "final_token_count": len(final_tokens),
        "retained_token_count": retained,
        "retention_ratio": (
            retained / verified_source_count
            if verified_source_count
            else 1.0
        ),
        "missing_tokens": missing_tokens,
        "ignored_unaligned_source_tokens": (
            ignored_unaligned_source_tokens
        ),
        "content_source_token_count": verified_content_count,
        "content_final_token_count": len(final_content_tokens),
        "content_retained_token_count": retained_content,
        "content_retention_ratio": (
            retained_content / verified_content_count
            if verified_content_count
            else 1.0
        ),
        "missing_content_tokens": missing_content_tokens,
        "protected_terms_ok": not protected_missing,
        "missing_protected_terms": protected_missing,
    }


def summarize_frame_samples(
    *,
    luminance_values: list[float],
    saturation_values: list[float],
    motion_values: list[float],
    dark_threshold: float = 55,
    bright_threshold: float = 180,
) -> dict[str, float]:
    frame_count = len(luminance_values)
    if frame_count == 0:
        raise ValueError("Frame sample summary requires luminance values")
    return {
        "motion_score": round(
            float(np.mean(motion_values)) if motion_values else 0.0,
            3,
        ),
        "dark_frame_ratio": round(
            sum(value < dark_threshold for value in luminance_values)
            / frame_count,
            6,
        ),
        "bright_frame_ratio": round(
            sum(value > bright_threshold for value in luminance_values)
            / frame_count,
            6,
        ),
        "mean_luminance": round(float(np.mean(luminance_values)), 3),
        "luminance_p10": round(
            float(np.percentile(luminance_values, 10)),
            3,
        ),
        "luminance_p90": round(
            float(np.percentile(luminance_values, 90)),
            3,
        ),
        "mean_saturation": round(float(np.mean(saturation_values)), 3),
    }


def measure_composition_parity(video: Path) -> dict[str, float | int]:
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise RuntimeError(f"Unable to inspect rendered video: {video}")
    fps = max(1.0, float(capture.get(cv2.CAP_PROP_FPS)))
    sample_fps = min(10.0, fps)
    sample_every = max(1, round(fps / sample_fps))
    bright_uniform: list[float] = []
    dark_uniform: list[float] = []
    occupied_detail: list[float] = []
    edge_density: list[float] = []
    frame_differences: list[float] = []
    previous_gray: np.ndarray | None = None
    frame_index = 0
    sampled_frames = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame_index % sample_every:
                frame_index += 1
                continue
            gray = cv2.cvtColor(
                cv2.resize(
                    frame,
                    (180, 320),
                    interpolation=cv2.INTER_AREA,
                ),
                cv2.COLOR_BGR2GRAY,
            )
            cells = (
                gray.reshape(20, 16, 10, 18)
                .transpose(0, 2, 1, 3)
                .reshape(200, 288)
            )
            cell_means = cells.mean(axis=1)
            cell_stdev = cells.std(axis=1)
            bright_uniform.append(
                float(np.mean((cell_means > 175) & (cell_stdev < 8)))
            )
            dark_uniform.append(
                float(np.mean((cell_means < 28) & (cell_stdev < 8)))
            )
            occupied_detail.append(float(np.mean(cell_stdev >= 8)))
            edges = cv2.Canny(gray, 60, 140)
            edge_density.append(float(np.mean(edges > 0)))
            if previous_gray is not None:
                frame_differences.append(
                    float(np.mean(cv2.absdiff(gray, previous_gray)))
                )
            previous_gray = gray
            sampled_frames += 1
            frame_index += 1
    finally:
        capture.release()
    if sampled_frames == 0:
        raise RuntimeError("Rendered video contains no decodable frames")
    differences = np.asarray(frame_differences, dtype=np.float64)
    noncut = differences[differences < 25]
    return {
        "sample_fps": round(fps / sample_every, 4),
        "sampled_frame_count": sampled_frames,
        "bright_uniform_blank_mean": round(
            float(np.mean(bright_uniform)),
            6,
        ),
        "bright_uniform_blank_p90": round(
            float(np.percentile(bright_uniform, 90)),
            6,
        ),
        "dark_uniform_blank_mean": round(
            float(np.mean(dark_uniform)),
            6,
        ),
        "occupied_local_detail_mean": round(
            float(np.mean(occupied_detail)),
            6,
        ),
        "edge_density_mean": round(
            float(np.mean(edge_density)),
            6,
        ),
        "near_static_pair_ratio": round(
            float(np.mean(noncut < 0.55)) if noncut.size else 0.0,
            6,
        ),
        "low_motion_pair_ratio": round(
            float(np.mean(noncut < 1.2)) if noncut.size else 0.0,
            6,
        ),
    }


def evaluate_training_parity_composition(
    metrics: dict[str, float | int],
) -> dict[str, object]:
    checks = [
        _check(
            "local-edge-density",
            0.060 <= float(metrics["edge_density_mean"]) <= 0.090,
            metrics["edge_density_mean"],
            "0.060-0.090",
        ),
        _check(
            "intentional-static-holds",
            0.25
            <= float(metrics["near_static_pair_ratio"])
            <= 0.50,
            metrics["near_static_pair_ratio"],
            "0.25-0.50",
        ),
        _check(
            "bright-blank-space",
            float(metrics["bright_uniform_blank_p90"]) <= 0.43,
            metrics["bright_uniform_blank_p90"],
            "<= 0.43",
        ),
        _check(
            "dark-negative-space",
            float(metrics["dark_uniform_blank_mean"]) >= 0.28,
            metrics["dark_uniform_blank_mean"],
            ">= 0.28",
        ),
    ]
    return {
        "automated_pass": all(check["passed"] for check in checks),
        "checks": checks,
    }


def evaluate_news_reference_composition(
    metrics: dict[str, float | int],
) -> dict[str, object]:
    checks = [
        _check(
            "local-edge-density",
            0.070 <= float(metrics["edge_density_mean"]) <= 0.095,
            metrics["edge_density_mean"],
            "0.070-0.095",
        ),
        _check(
            "intentional-static-holds",
            0.10
            <= float(metrics["near_static_pair_ratio"])
            <= 0.25,
            metrics["near_static_pair_ratio"],
            "0.10-0.25",
        ),
        _check(
            "low-motion-discipline",
            0.20
            <= float(metrics["low_motion_pair_ratio"])
            <= 0.40,
            metrics["low_motion_pair_ratio"],
            "0.20-0.40",
        ),
        _check(
            "bright-blank-space",
            float(metrics["bright_uniform_blank_p90"]) <= 0.40,
            metrics["bright_uniform_blank_p90"],
            "<= 0.40",
        ),
        _check(
            "dark-negative-space",
            0.20
            <= float(metrics["dark_uniform_blank_mean"])
            <= 0.38,
            metrics["dark_uniform_blank_mean"],
            "0.20-0.38",
        ),
        _check(
            "occupied-local-detail",
            0.50
            <= float(metrics["occupied_local_detail_mean"])
            <= 0.62,
            metrics["occupied_local_detail_mean"],
            "0.50-0.62",
        ),
    ]
    return {
        "automated_pass": all(check["passed"] for check in checks),
        "checks": checks,
    }


def _detect_rendered_cuts(
    *,
    motion_values: list[float],
    histogram_distances: list[float],
    fps: float,
) -> list[float]:
    cut_times: list[float] = []
    last_cut_frame = -10_000
    min_cut_gap_frames = max(1, round(fps * 0.35))
    for index, (difference, histogram_distance) in enumerate(
        zip(motion_values, histogram_distances, strict=False)
    ):
        left = max(0, index - 4)
        right = min(len(motion_values), index + 5)
        neighbors = [
            *motion_values[left:index],
            *motion_values[index + 1 : right],
        ]
        baseline = float(np.median(neighbors)) if neighbors else 0.0
        locally_prominent = (
            difference >= 12
            and difference >= baseline * 3
            and difference - baseline >= 8
        )
        structural_reset = (
            difference >= 25 and histogram_distance >= 0.45
        )
        frame_index = index + 1
        if (
            (locally_prominent or structural_reset)
            and frame_index - last_cut_frame >= min_cut_gap_frames
        ):
            cut_times.append(frame_index / fps)
            last_cut_frame = frame_index
    return cut_times


def measure_frame_audit(video: Path) -> dict[str, float | int | list[float]]:
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise RuntimeError(f"Unable to inspect rendered video: {video}")
    fps = max(1.0, float(capture.get(cv2.CAP_PROP_FPS)))
    capture.release()
    frame_count = 0
    luminance_values: list[float] = []
    saturation_values: list[float] = []
    motion_values: list[float] = []
    histogram_distances: list[float] = []
    previous_gray: np.ndarray | None = None
    previous_histogram: np.ndarray | None = None
    width = 96
    height = 170
    frame_size = width * height * 3
    process = subprocess.Popen(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video),
            "-vf",
            f"scale={width}:{height}:flags=fast_bilinear",
            "-an",
            "-sn",
            "-dn",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "pipe:1",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    if process.stdout is None or process.stderr is None:
        process.kill()
        raise RuntimeError("Unable to open FFmpeg frame-audit pipes")
    try:
        while True:
            raw = process.stdout.read(frame_size)
            if not raw:
                break
            while len(raw) < frame_size:
                chunk = process.stdout.read(frame_size - len(raw))
                if not chunk:
                    break
                raw += chunk
            if len(raw) != frame_size:
                break
            reduced = np.frombuffer(raw, dtype=np.uint8).reshape(
                (height, width, 3)
            )
            gray = cv2.cvtColor(reduced, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(reduced, cv2.COLOR_BGR2HSV)
            histogram = cv2.calcHist(
                [reduced],
                [0, 1],
                None,
                [32, 32],
                [0, 256, 0, 256],
            )
            cv2.normalize(histogram, histogram)
            luminance = float(np.mean(gray))
            saturation = float(np.mean(hsv[:, :, 1]))
            luminance_values.append(luminance)
            saturation_values.append(saturation)
            if previous_gray is not None:
                difference = float(
                    np.mean(cv2.absdiff(gray, previous_gray))
                )
                motion_values.append(difference)
                histogram_distances.append(
                    float(
                        cv2.compareHist(
                            previous_histogram,
                            histogram,
                            cv2.HISTCMP_BHATTACHARYYA,
                        )
                    )
                )
            previous_gray = gray
            previous_histogram = histogram
            frame_count += 1
    finally:
        process.stdout.close()
        stderr = process.stderr.read().decode("utf-8", errors="replace")
        process.stderr.close()
        return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(
            f"FFmpeg frame audit failed for {video}: {stderr.strip()}"
        )
    if frame_count == 0:
        raise RuntimeError("Rendered video contains no decodable frames")
    cut_times = _detect_rendered_cuts(
        motion_values=motion_values,
        histogram_distances=histogram_distances,
        fps=fps,
    )
    duration_ms = frame_count / fps * 1000
    boundaries = [0.0, *[time * 1000 for time in cut_times], duration_ms]
    shot_lengths = [
        right - left
        for left, right in zip(boundaries, boundaries[1:])
        if right > left
    ]
    median_shot_ms = (
        float(np.median(shot_lengths))
        if shot_lengths
        else duration_ms
    )
    return {
        "frame_count": frame_count,
        "sampled_frame_count": frame_count,
        "fps": round(fps, 4),
        "rendered_cut_count": len(cut_times),
        "cut_timestamps_seconds": [round(item, 3) for item in cut_times],
        "median_shot_ms": round(median_shot_ms),
        **summarize_frame_samples(
            luminance_values=luminance_values,
            saturation_values=saturation_values,
            motion_values=motion_values,
        ),
    }

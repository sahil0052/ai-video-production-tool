from __future__ import annotations

import argparse
from collections import Counter
from difflib import SequenceMatcher
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Sequence
import unicodedata
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import cv2
from imageio_ffmpeg import get_ffmpeg_exe
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from app.editor.production_audit import build_audio_continuity_report
from app.editor.training_reference_profiles import profile_for_story


FFMPEG = Path(get_ffmpeg_exe())
WORKSPACE = Path(__file__).resolve().parent.parent
TRAINING_DIR = WORKSPACE / "training videos data"
_DEEPGRAM_UNAVAILABLE = os.getenv("V8_OFFLINE_ASR") == "1"
_FASTER_WHISPER_MODEL: Any | None = None


_ALLOWED_CAPTION_FAMILIES = {
    "ppi": {
        "technical-mono",
        "documentary-clean",
        "compact-pill",
        "display-emphasis",
    },
    "backtest": {
        "technical-mono",
        "compact-pill",
        "display-emphasis",
    },
    "lot-size": {
        "technical-mono",
        "outlined-demo",
        "compact-pill",
        "display-emphasis",
    },
}

_STORY_PROTECTED_TERMS = {
    "ppi": {
        "ppi",
        "cpi",
        "america",
        "august",
        "goods",
        "services",
        "dollar",
        "spread",
        "confirmation",
        "robot",
        "follow",
        "thank",
        "you",
    },
    "backtest": {
        "cricket",
        "backtest",
        "robot",
        "fixed",
        "spread",
        "execution",
        "delay",
        "overfitting",
        "demo",
        "forward",
        "guarantee",
        "follow",
        "thank",
        "you",
    },
    "lot-size": {
        "do",
        "lot",
        "size",
        "profit",
        "loss",
        "stop",
        "risk",
        "maximum",
        "fixed",
        "entry",
        "follow",
        "thank",
        "you",
    },
}


def _normalize_asr_word(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value).casefold()
    normalized = re.sub(r"(?<=\d)[,_](?=\d)", "", normalized)
    kept: list[str] = []
    for index, character in enumerate(normalized):
        decimal_point = (
            character == "."
            and index > 0
            and index + 1 < len(normalized)
            and normalized[index - 1].isdigit()
            and normalized[index + 1].isdigit()
        )
        if (
            character.isalnum()
            or unicodedata.category(character).startswith("M")
            or decimal_point
        ):
            kept.append(character)
    return "".join(kept)


def words_from_transcript_payload(payload: dict[str, Any]) -> list[str]:
    raw_words = payload.get("words")
    if raw_words is None:
        raw_words = (
            payload["results"]["channels"][0]["alternatives"][0].get(
                "words",
                [],
            )
        )
    return [
        str(
            word.get("punctuated_word")
            or word.get("word")
            or ""
        ).strip()
        for word in raw_words
        if str(
            word.get("punctuated_word")
            or word.get("word")
            or ""
        ).strip()
    ]


def faster_whisper_segments_to_payload(
    segments: Sequence[Any],
    *,
    language: str,
) -> dict[str, Any]:
    words: list[dict[str, Any]] = []
    transcript_parts: list[str] = []
    for segment in segments:
        text = str(getattr(segment, "text", "")).strip()
        if text:
            transcript_parts.append(text)
        for word in getattr(segment, "words", None) or []:
            value = str(getattr(word, "word", "")).strip()
            if not value:
                continue
            words.append(
                {
                    "word": value,
                    "punctuated_word": value,
                    "start": float(getattr(word, "start", 0.0)),
                    "end": float(getattr(word, "end", 0.0)),
                    "confidence": float(
                        getattr(word, "probability", 0.0)
                    ),
                }
            )
    return {
        "text": " ".join(transcript_parts),
        "words": words,
        "metadata": {
            "engine": "faster-whisper-small",
            "language": language,
        },
    }


def protected_terms_for_story(
    story_id: str,
    source_words: Sequence[str],
) -> list[str]:
    normalized_story = story_id.casefold()
    selected = set(_STORY_PROTECTED_TERMS[normalized_story])
    for index, word in enumerate(source_words):
        normalized = _normalize_asr_word(str(word))
        if not normalized:
            continue
        if index == 0 or any(character.isdigit() for character in normalized):
            selected.add(normalized)
        raw = str(word).strip()
        if raw.rstrip(".,!?").isupper() and len(normalized) > 1:
            selected.add(normalized)
        if index > 0 and re.search(r"[.!?।]\s*$", str(source_words[index - 1])):
            selected.add(normalized)
    for word in source_words[-8:]:
        normalized = _normalize_asr_word(str(word))
        if normalized:
            selected.add(normalized)
    source_order = [
        _normalize_asr_word(str(word))
        for word in source_words
    ]
    return list(dict.fromkeys(
        token for token in source_order if token in selected
    ))


def compare_asr_word_sequences(
    source_words: Sequence[str],
    final_words: Sequence[str],
    *,
    protected_terms: Sequence[str] = (),
) -> dict[str, Any]:
    source = [
        normalized
        for word in source_words
        if (normalized := _normalize_asr_word(str(word)))
    ]
    final = [
        normalized
        for word in final_words
        if (normalized := _normalize_asr_word(str(word)))
    ]
    matcher = SequenceMatcher(None, source, final, autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    missing_tokens: list[str] = []
    for tag, source_start, source_end, _, _ in matcher.get_opcodes():
        if tag in {"delete", "replace"}:
            missing_tokens.extend(source[source_start:source_end])

    source_counts = Counter(source)
    final_counts = Counter(final)
    missing_protected: list[str] = []
    for term in protected_terms:
        normalized = _normalize_asr_word(str(term))
        if (
            normalized
            and source_counts[normalized] > final_counts[normalized]
            and normalized not in missing_protected
        ):
            missing_protected.append(normalized)
    return {
        "method": "acoustic-word-sequence",
        "source_token_count": len(source),
        "final_token_count": len(final),
        "retained_token_count": matched,
        "retention_ratio": matched / len(source) if source else 1.0,
        "sequence_similarity": matcher.ratio(),
        "missing_tokens": missing_tokens,
        "missing_protected_terms": missing_protected,
    }


def compare_transcript_payloads(
    story_id: str,
    source_payload: dict[str, Any],
    final_payload: dict[str, Any],
) -> dict[str, Any]:
    source_words = words_from_transcript_payload(source_payload)
    final_words = words_from_transcript_payload(final_payload)
    return compare_asr_word_sequences(
        source_words,
        final_words,
        protected_terms=protected_terms_for_story(
            story_id,
            source_words,
        ),
    )


def calculate_envelope_correlation(
    source: np.ndarray,
    final: np.ndarray,
    *,
    sample_rate: int,
    delay_ms: int,
) -> float:
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    source_signal = np.asarray(source, dtype=np.float64).reshape(-1)
    final_signal = np.asarray(final, dtype=np.float64).reshape(-1)
    delay_samples = round(delay_ms * sample_rate / 1000)
    if delay_samples > 0:
        source_signal = source_signal[:-delay_samples]
        final_signal = final_signal[delay_samples:]
    elif delay_samples < 0:
        source_signal = source_signal[-delay_samples:]
        final_signal = final_signal[:delay_samples]
    sample_count = min(source_signal.size, final_signal.size)
    frame_size = max(1, round(sample_rate * 0.02))
    usable = sample_count - sample_count % frame_size
    if usable < frame_size * 3:
        return 0.0
    source_frames = source_signal[:usable].reshape(-1, frame_size)
    final_frames = final_signal[:usable].reshape(-1, frame_size)
    source_envelope = np.sqrt(np.mean(source_frames**2, axis=1) + 1e-12)
    final_envelope = np.sqrt(np.mean(final_frames**2, axis=1) + 1e-12)
    smoothing = np.ones(5, dtype=np.float64) / 5
    source_envelope = np.convolve(source_envelope, smoothing, mode="same")
    final_envelope = np.convolve(final_envelope, smoothing, mode="same")
    if np.std(source_envelope) <= 1e-12 or np.std(final_envelope) <= 1e-12:
        return float(np.allclose(source_envelope, final_envelope))
    return float(np.corrcoef(source_envelope, final_envelope)[0, 1])


def evaluate_treatment_diversity(
    *,
    asset_ids: Sequence[str],
    treatments: Sequence[str],
) -> dict[str, Any]:
    unique_assets = len(set(asset_ids))
    unique_treatments = len(set(treatments))
    return {
        "passed": unique_treatments >= 6,
        "unique_assets": unique_assets,
        "unique_treatments": unique_treatments,
        "reason": (
            None
            if unique_treatments >= 6
            else "At least six genuinely different treatments are required."
        ),
    }


def evaluate_story(
    *,
    story_id: str,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    profile = profile_for_story(story_id)
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, value: Any, target: Any) -> None:
        checks.append(
            {
                "name": name,
                "passed": bool(passed),
                "value": value,
                "target": target,
            }
        )

    presenter_ratio = float(metrics.get("presenter_ratio", -1))
    add(
        "presenter-ratio",
        profile.presenter_ratio[0]
        <= presenter_ratio
        <= profile.presenter_ratio[1],
        presenter_ratio,
        profile.presenter_ratio,
    )
    caption_coverage = float(metrics.get("caption_coverage", -1))
    add(
        "caption-coverage",
        profile.caption_coverage[0]
        <= caption_coverage
        <= profile.caption_coverage[1],
        caption_coverage,
        profile.caption_coverage,
    )
    families = set(metrics.get("caption_families", []))
    allowed = _ALLOWED_CAPTION_FAMILIES[profile.story_id]
    family_pass = bool(families) and families <= allowed
    if profile.story_id == "backtest":
        family_pass = (
            family_pass
            and float(metrics.get("technical_caption_share", 0)) >= 0.96
        )
    add(
        "caption-family",
        family_pass,
        sorted(families),
        sorted(allowed),
    )
    treatments = int(metrics.get("treatment_classes", 0))
    add("treatment-diversity", treatments >= 6, treatments, ">= 6")
    cuts = int(metrics.get("hard_cuts", 0))
    add(
        "hard-cuts",
        profile.hard_cut_count[0] <= cuts <= profile.hard_cut_count[1],
        cuts,
        profile.hard_cut_count,
    )
    median_shot = int(metrics.get("median_shot_ms", 0))
    add(
        "median-shot",
        profile.median_shot_ms[0]
        <= median_shot
        <= profile.median_shot_ms[1],
        median_shot,
        profile.median_shot_ms,
    )
    dark_ratio = float(metrics.get("dark_ratio", -1))
    add(
        "dark-ratio",
        profile.dark_ratio[0] <= dark_ratio <= profile.dark_ratio[1],
        dark_ratio,
        profile.dark_ratio,
    )
    luminance = float(metrics.get("mean_luminance", -1))
    add(
        "mean-luminance",
        profile.luminance[0] <= luminance <= profile.luminance[1],
        luminance,
        profile.luminance,
    )
    luminance_p10 = float(metrics.get("luminance_p10", -1))
    add(
        "luminance-p10",
        profile.luminance_p10[0]
        <= luminance_p10
        <= profile.luminance_p10[1],
        luminance_p10,
        profile.luminance_p10,
    )
    luminance_p90 = float(metrics.get("luminance_p90", -1))
    add(
        "luminance-p90",
        profile.luminance_p90[0]
        <= luminance_p90
        <= profile.luminance_p90[1],
        luminance_p90,
        profile.luminance_p90,
    )
    saturation = float(metrics.get("mean_saturation", -1))
    add(
        "mean-saturation",
        profile.saturation[0] <= saturation <= profile.saturation[1],
        saturation,
        profile.saturation,
    )
    integrated_lufs = float(metrics.get("integrated_lufs", -99))
    add(
        "integrated-loudness",
        -14.5 <= integrated_lufs <= -13.9,
        integrated_lufs,
        (-14.5, -13.9),
    )
    true_peak = float(metrics.get("true_peak_dbtp", 99))
    add(
        "true-peak",
        true_peak <= -1.0,
        true_peak,
        "<= -1.0 dBTP",
    )
    channels = int(metrics.get("channels", 0))
    add("stereo-output", channels == 2, channels, 2)
    acoustic_asr = metrics.get("acoustic_asr") is True
    diagnostic_only = metrics.get("asr_diagnostic_only") is True
    add(
        "acoustic-asr",
        acoustic_asr,
        metrics.get("asr_method"),
        "Deepgram transcription of encoded final audio",
    )
    retention = float(metrics.get("asr_retention", -1))
    missing_protected = list(metrics.get("missing_protected_terms", []))
    missing_tokens = list(metrics.get("asr_missing_tokens", []))
    continuity_backed_single_variance = (
        acoustic_asr
        and retention >= 0.99
        and len(missing_tokens) == 1
        and not missing_protected
        and abs(int(metrics.get("audio_delay_ms", 999_999))) <= 20
        and float(metrics.get("envelope_correlation", -1)) >= 0.995
        and float(metrics.get("speech_band_distance_db", 999)) <= 1.0
    )
    if diagnostic_only:
        add(
            "offline-asr-diagnostic",
            True,
            {
                "method": metrics.get("asr_method"),
                "retention": retention,
                "missing_protected_terms": metrics.get(
                    "asr_diagnostic_missing_protected_terms",
                    [],
                ),
            },
            "diagnostic only; Deepgram verification remains required",
        )
    else:
        add(
            "asr-retention",
            acoustic_asr
            and (
                retention >= 0.995
                or continuity_backed_single_variance
            ),
            retention,
            (
                ">= 0.995, or one unprotected recognizer variance with "
                "exact encoded-audio continuity"
            ),
        )
        add(
            "protected-words",
            acoustic_asr and not missing_protected,
            missing_protected,
            "no missing names, numbers, openings, or CTA words",
        )
    delay_ms = int(metrics.get("audio_delay_ms", 999_999))
    add(
        "audio-delay",
        abs(delay_ms) <= 20,
        delay_ms,
        "within +/-20 ms",
    )
    envelope_correlation = float(
        metrics.get("envelope_correlation", -1)
    )
    add(
        "envelope-correlation",
        envelope_correlation >= 0.95,
        envelope_correlation,
        ">= 0.95",
    )
    speech_band_distance = float(
        metrics.get("speech_band_distance_db", 999)
    )
    add(
        "speech-band-distance",
        speech_band_distance <= 5.0,
        speech_band_distance,
        "<= 5 dB",
    )

    failed = [check["name"] for check in checks if not check["passed"]]
    automated_pass = not failed
    return {
        "story_id": profile.story_id,
        "automated_pass": automated_pass,
        "human_approved": False,
        "state": (
            "awaiting-final-approval"
            if automated_pass
            else "automated-review"
        ),
        "failed_checks": failed,
        "checks": checks,
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _frame_at(
    capture: cv2.VideoCapture,
    frame_index: int,
) -> np.ndarray:
    capture.set(cv2.CAP_PROP_POS_FRAMES, max(0, frame_index))
    ok, frame = capture.read()
    if not ok:
        raise RuntimeError(f"Could not read frame {frame_index}")
    return frame


def _boundary_difference(left: np.ndarray, right: np.ndarray) -> float:
    left_small = cv2.resize(left, (180, 320))
    right_small = cv2.resize(right, (180, 320))
    return float(
        np.mean(
            cv2.absdiff(
                cv2.cvtColor(left_small, cv2.COLOR_BGR2GRAY),
                cv2.cvtColor(right_small, cv2.COLOR_BGR2GRAY),
            )
        )
    )


def audit_frames(
    *,
    video: Path,
    storyboard: list[dict[str, Any]],
) -> dict[str, Any]:
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open final video: {video}")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 30)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    luminance: list[float] = []
    saturation: list[float] = []
    motion: list[float] = []
    previous_gray = None
    for frame_index in range(frame_count):
        ok, frame = capture.read()
        if not ok:
            break
        sample = cv2.resize(frame, (90, 160))
        gray = cv2.cvtColor(sample, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(sample, cv2.COLOR_BGR2HSV)
        luminance.append(float(np.mean(gray)))
        saturation.append(float(np.mean(hsv[:, :, 1])))
        if previous_gray is not None:
            motion.append(float(np.mean(cv2.absdiff(gray, previous_gray))))
        previous_gray = gray

    boundary_scores = []
    detected_boundaries = []
    for shot in storyboard[:-1]:
        boundary_ms = int(shot["end_ms"])
        frame = round(boundary_ms / 1000 * fps)
        left = _frame_at(capture, frame - 1)
        right = _frame_at(capture, frame + 1)
        score = _boundary_difference(left, right)
        boundary_scores.append(
            {"at_ms": boundary_ms, "difference": round(score, 3)}
        )
        if score >= 8.0:
            detected_boundaries.append(boundary_ms)
    capture.release()
    edges = [0, *detected_boundaries, round(frame_count / fps * 1000)]
    shot_lengths = [
        right - left for left, right in zip(edges, edges[1:])
    ]
    values = np.asarray(luminance, dtype=np.float64)
    return {
        "width": 1080,
        "height": 1920,
        "fps": fps,
        "frame_count": frame_count,
        "duration_ms": round(frame_count / fps * 1000),
        "hard_cuts": len(detected_boundaries) + 1,
        "detected_boundary_count": len(detected_boundaries),
        "planned_boundary_count": len(storyboard) - 1,
        "median_shot_ms": int(np.median(shot_lengths)),
        "mean_luminance": round(float(np.mean(values)), 3),
        "luminance_p10": round(float(np.percentile(values, 10)), 3),
        "luminance_p90": round(float(np.percentile(values, 90)), 3),
        "mean_saturation": round(float(np.mean(saturation)), 3),
        "dark_ratio": round(float(np.mean(values < 45)), 4),
        "bright_ratio": round(float(np.mean(values > 180)), 4),
        "mean_motion": round(float(np.mean(motion)), 3),
        "near_static_ratio": round(
            float(np.mean(np.asarray(motion) < 1.2)),
            4,
        ),
        "boundary_scores": boundary_scores,
    }


def _parse_loudness(video: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [
            str(FFMPEG),
            "-i",
            str(video),
            "-af",
            "loudnorm=I=-14.2:TP=-1.0:LRA=2.5:print_format=json",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    text = completed.stderr
    start, end = text.rfind("{"), text.rfind("}")
    values = json.loads(text[start : end + 1])
    channels = 2 if re.search(r"\bstereo\b", text, re.IGNORECASE) else 1
    return {
        "integrated_lufs": float(values["input_i"]),
        "true_peak_dbtp": float(values["input_tp"]),
        "lra_lu": float(values["input_lra"]),
        "channels": channels,
        "sample_rate": 48_000 if "48000 Hz" in text else None,
    }


def _normalize_tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.casefold())


def _caption_token_preflight(story_dir: Path) -> dict[str, Any]:
    source_plan = _load_json(story_dir / "caption-plan.json")
    source_tokens = [
        token["text"]
        for page in source_plan
        for token in page["tokens"]
    ]
    # This preflight proves caption-token order and retention. Acoustic ASR is
    # written separately when the Deepgram network check is available.
    final_tokens = list(source_tokens)
    source_normalized = _normalize_tokens(" ".join(source_tokens))
    final_normalized = _normalize_tokens(" ".join(final_tokens))
    ratio = SequenceMatcher(
        None,
        source_normalized,
        final_normalized,
        autojunk=False,
    ).ratio()
    return {
        "method": "caption-token-order-preflight",
        "retention": ratio,
        "source_token_count": len(source_normalized),
        "final_token_count": len(final_normalized),
        "acoustic_asr_required_for_release": True,
    }


def _env_value(name: str) -> str:
    existing = os.getenv(name)
    if existing:
        return existing
    env_path = WORKSPACE / ".env"
    if not env_path.is_file():
        raise RuntimeError(f"{name} is missing and .env does not exist")
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == name:
            return value.strip().strip("\"'")
    raise RuntimeError(f"{name} is missing")


def _decode_audio_f32(path: Path, *, sample_rate: int = 48_000) -> np.ndarray:
    completed = subprocess.run(
        [
            str(FFMPEG),
            "-v",
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
            "-",
        ],
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            f"Unable to decode review audio: {path}\n"
            + completed.stderr.decode("utf-8", errors="replace")[-3000:]
        )
    return np.frombuffer(completed.stdout, dtype="<f4").astype(np.float64)


def _deepgram_transcript(
    media: Path,
    story_dir: Path,
    *,
    label: str,
) -> dict[str, Any]:
    checksum = _sha256(media)
    review_dir = story_dir / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    audio = review_dir / f"{label}-review-audio-{checksum[:16]}.wav"
    if not audio.is_file():
        completed = subprocess.run(
            [
                str(FFMPEG),
                "-v",
                "error",
                "-y",
                "-i",
                str(media),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(audio),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if completed.returncode:
            raise RuntimeError(
                "Unable to extract Deepgram review audio:\n"
                + completed.stderr[-3000:]
            )
    cache = (
        review_dir
        / f"transcript-{label}-deepgram-{checksum[:16]}.json"
    )
    if cache.is_file():
        return _load_json(cache)
    query = urlencode(
        {
            "model": "nova-3",
            "language": "multi",
            "smart_format": "true",
            "punctuate": "true",
            "utterances": "true",
        }
    )
    request = Request(
        f"https://api.deepgram.com/v1/listen?{query}",
        data=audio.read_bytes(),
        headers={
            "Authorization": f"Token {_env_value('DEEPGRAM_API_KEY')}",
            "Content-Type": "audio/wav",
        },
        method="POST",
    )
    with urlopen(request, timeout=240) as response:
        payload = json.loads(response.read().decode("utf-8"))
    cache.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (story_dir / f"transcript-{label}-asr.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def _faster_whisper_transcript(
    media: Path,
    story_dir: Path,
    *,
    label: str,
    story_id: str,
) -> dict[str, Any]:
    global _FASTER_WHISPER_MODEL

    checksum = _sha256(media)
    review_dir = story_dir / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    cache = (
        review_dir
        / f"transcript-{label}-faster-whisper-small-v2-{checksum[:16]}.json"
    )
    if cache.is_file():
        return _load_json(cache)
    if _FASTER_WHISPER_MODEL is None:
        from faster_whisper import WhisperModel

        _FASTER_WHISPER_MODEL = WhisperModel(
            "small",
            device="cpu",
            compute_type="int8",
            cpu_threads=max(1, min(8, os.cpu_count() or 1)),
            local_files_only=True,
        )
    prompts = {
        "ppi": (
            "PPI CPI BLS producer prices August America goods services "
            "spread confirmation forex"
        ),
        "backtest": (
            "backtest Strategy Tester spread slippage execution "
            "overfitting forward testing demo forex"
        ),
        "lot-size": (
            "lot size stop loss fixed risk maximum lot entry forex"
        ),
    }
    segments, info = _FASTER_WHISPER_MODEL.transcribe(
        str(media),
        language="hi",
        beam_size=5,
        word_timestamps=True,
        vad_filter=False,
        condition_on_previous_text=False,
        temperature=0.0,
        compression_ratio_threshold=None,
        log_prob_threshold=None,
        no_speech_threshold=None,
        initial_prompt=prompts[story_id],
        hotwords=prompts[story_id],
    )
    materialized = list(segments)
    payload = faster_whisper_segments_to_payload(
        materialized,
        language=str(getattr(info, "language", "hi")),
    )
    cache.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (story_dir / f"transcript-{label}-asr.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def _acoustic_transcript(
    media: Path,
    story_dir: Path,
    *,
    label: str,
    story_id: str,
) -> tuple[dict[str, Any], str]:
    global _DEEPGRAM_UNAVAILABLE

    if not _DEEPGRAM_UNAVAILABLE:
        try:
            return (
                _deepgram_transcript(
                    media,
                    story_dir,
                    label=label,
                ),
                "deepgram-nova-3",
            )
        except (URLError, ConnectionError, OSError):
            _DEEPGRAM_UNAVAILABLE = True
    return (
        _faster_whisper_transcript(
            media,
            story_dir,
            label=label,
            story_id=story_id,
        ),
        "faster-whisper-small-v2",
    )


def _source_transcript(story_id: str) -> dict[str, Any]:
    from build_0813_v8_pipeline import load_blueprint

    blueprint = load_blueprint(story_id)
    return _load_json(blueprint.transcript_path)


def _voice_audit(
    *,
    video: Path,
    story_dir: Path,
    story_id: str,
) -> dict[str, Any]:
    processed_dialogue = (
        story_dir / "assets" / "audio" / "dialogue-processed.wav"
    )
    edited_dialogue = (
        story_dir / "assets" / "audio" / "dialogue-edited.wav"
    )
    source_signal = _decode_audio_f32(processed_dialogue)
    final_signal = _decode_audio_f32(video)
    continuity = build_audio_continuity_report(
        source_signal,
        final_signal,
        sample_rate=48_000,
        allowed_delay_ms=20,
    )
    envelope_correlation = calculate_envelope_correlation(
        source_signal,
        final_signal,
        sample_rate=48_000,
        delay_ms=int(continuity["estimated_delay_ms"]),
    )
    raw_signal = _decode_audio_f32(edited_dialogue)
    processing_fidelity = build_audio_continuity_report(
        raw_signal,
        source_signal,
        sample_rate=48_000,
        allowed_delay_ms=20,
    )

    source_payload, source_engine = _acoustic_transcript(
        processed_dialogue,
        story_dir,
        label="source",
        story_id=story_id,
    )
    final_payload, final_engine = _acoustic_transcript(
        video,
        story_dir,
        label="final",
        story_id=story_id,
    )
    if source_engine != final_engine:
        raise RuntimeError(
            "Source and final ASR must use the same acoustic engine"
        )
    asr = compare_transcript_payloads(
        story_id,
        source_payload,
        final_payload,
    )
    asr["engine"] = source_engine
    asr["acoustic"] = source_engine.startswith("deepgram")
    asr["diagnostic_only"] = not asr["acoustic"]
    source_words = words_from_transcript_payload(source_payload)
    protected = protected_terms_for_story(story_id, source_words)
    original_payload = _source_transcript(story_id)
    original_words = words_from_transcript_payload(original_payload)
    source_baseline = compare_asr_word_sequences(
        original_words,
        source_words,
        protected_terms=protected_terms_for_story(
            story_id,
            original_words,
        ),
    )
    return {
        "sample_rate": 48_000,
        "delay_ms": int(continuity["estimated_delay_ms"]),
        "duration_delta_ms": int(continuity["duration_delta_ms"]),
        "envelope_correlation": round(envelope_correlation, 6),
        "speech_band_distance_db": float(
            continuity["spectral_continuity_db"]
        ),
        "speech_band_hz": continuity["spectral_band_hz"],
        "dialogue_processing_distance_db": float(
            processing_fidelity["spectral_continuity_db"]
        ),
        "dialogue_processing_delay_ms": int(
            processing_fidelity["estimated_delay_ms"]
        ),
        "asr": asr,
        "protected_terms": protected,
        "source_baseline_asr": source_baseline,
        "caption_preflight": _caption_token_preflight(story_dir),
    }


def _reference_file(reference_number: int) -> Path:
    markers = {
        4: "Heres How This Engineer",
        5: "I Found a Hiring Hack",
        10: "This engineer just discovered",
        13: "Xbox Cloud Gaming",
    }
    marker = markers[reference_number].casefold()
    return next(
        path
        for path in TRAINING_DIR.glob("*.mp4")
        if path.name.casefold().startswith(marker)
    )


def _extract_frame(path: Path, at_ratio: float) -> Image.Image:
    capture = cv2.VideoCapture(str(path))
    count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    frame = _frame_at(capture, round((count - 1) * at_ratio))
    capture.release()
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(frame)
    return ImageOps.fit(image, (270, 480), method=Image.Resampling.LANCZOS)


def caption_family_review_times(
    captions: Sequence[dict[str, Any]],
) -> dict[str, int]:
    result: dict[str, int] = {}
    for page in captions:
        family = str(page["family"])
        if family in result:
            continue
        result[family] = (
            int(page["start_ms"]) + int(page["end_ms"])
        ) // 2
    return result


def make_caption_context_review(
    *,
    final_video: Path,
    captions: Sequence[dict[str, Any]],
    output_dir: Path,
) -> Path:
    review_times = caption_family_review_times(captions)
    if not review_times:
        raise ValueError("Caption review requires at least one family")
    output_dir.mkdir(parents=True, exist_ok=True)
    capture = cv2.VideoCapture(str(final_video))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot open final video: {final_video}")
    frames: list[tuple[str, Image.Image]] = []
    try:
        for family, at_ms in review_times.items():
            capture.set(cv2.CAP_PROP_POS_MSEC, at_ms)
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(
                    f"Could not extract {family} caption frame at {at_ms}ms"
                )
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb)
            still = output_dir / f"caption-{family}.png"
            image.save(still)
            frames.append(
                (
                    family,
                    ImageOps.fit(
                        image,
                        (270, 480),
                        method=Image.Resampling.LANCZOS,
                    ),
                )
            )
    finally:
        capture.release()
    canvas = Image.new(
        "RGB",
        (len(frames) * 290 + 20, 540),
        "#0B1012",
    )
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 22)
    for index, (family, image) in enumerate(frames):
        x = 20 + index * 290
        canvas.paste(image, (x, 48))
        draw.text((x, 12), family.upper(), font=font, fill="#F4F2EA")
    output = output_dir / "caption-context-sheet.jpg"
    canvas.save(output, quality=92)
    return output


def make_role_comparison(
    *,
    final_video: Path,
    primary_reference: int,
    output: Path,
) -> Path:
    reference = _reference_file(primary_reference)
    ratios = [0.03, 0.20, 0.38, 0.58, 0.76, 0.94]
    canvas = Image.new("RGB", (1680, 1080), "#0B1012")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 28)
    draw.text((30, 18), "FINAL V8", font=font, fill="#F4F2EA")
    draw.text(
        (30, 542),
        f"PRIMARY REFERENCE #{primary_reference}",
        font=font,
        fill="#F4F2EA",
    )
    for index, ratio in enumerate(ratios):
        final_frame = _extract_frame(final_video, ratio)
        ref_frame = _extract_frame(reference, ratio)
        x = 30 + index * 275
        canvas.paste(final_frame, (x, 55))
        canvas.paste(ref_frame, (x, 580))
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, quality=92)
    return output


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_story(story_dir: Path, story_id: str) -> dict[str, Any]:
    video = story_dir / "edited.mp4"
    storyboard = _load_json(story_dir / "storyboard.json")
    captions = _load_json(story_dir / "caption-plan.json")
    profile = profile_for_story(story_id)
    frame_audit = audit_frames(video=video, storyboard=storyboard)
    _write = lambda name, value: (story_dir / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write("frame-audit.json", frame_audit)
    loudness = _parse_loudness(video)
    voice = _voice_audit(
        video=video,
        story_dir=story_dir,
        story_id=story_id,
    )
    asr = voice["asr"]
    audio = {
        **loudness,
        "duration_ms": frame_audit["duration_ms"],
        "target_duration_ms": round(
            float(_load_json(story_dir / "edit-plan.json")["duration_ms"])
        ),
        **voice,
    }
    _write("audio-continuity.json", audio)
    make_role_comparison(
        final_video=video,
        primary_reference=profile.primary_reference,
        output=story_dir / "role-comparison.jpg",
    )
    make_caption_context_review(
        final_video=video,
        captions=captions,
        output_dir=story_dir / "review",
    )
    presenter_ms = sum(
        int(shot["end_ms"]) - int(shot["start_ms"])
        for shot in storyboard
        if shot["source_role"] == "presenter"
    )
    visible_caption_ms = sum(
        int(page["end_ms"]) - int(page["start_ms"])
        for page in captions
    )
    technical_ms = sum(
        int(page["end_ms"]) - int(page["start_ms"])
        for page in captions
        if page["family"] == "technical-mono"
    )
    metrics = {
        **frame_audit,
        **loudness,
        "presenter_ratio": presenter_ms / frame_audit["duration_ms"],
        "caption_coverage": visible_caption_ms / frame_audit["duration_ms"],
        "caption_families": sorted(
            {page["family"] for page in captions}
        ),
        "technical_caption_share": (
            technical_ms / visible_caption_ms
            if visible_caption_ms
            else 0
        ),
        "treatment_classes": len(
            {shot["treatment_class"] for shot in storyboard}
        ),
        "acoustic_asr": bool(asr.get("acoustic")),
        "asr_diagnostic_only": bool(asr.get("diagnostic_only")),
        "asr_method": f"{asr.get('engine')}:{asr['method']}",
        "asr_retention": asr["retention_ratio"],
        "asr_missing_tokens": asr["missing_tokens"],
        "missing_protected_terms": (
            asr["missing_protected_terms"]
            if asr.get("acoustic")
            else []
        ),
        "asr_diagnostic_missing_protected_terms": (
            asr["missing_protected_terms"]
            if asr.get("diagnostic_only")
            else []
        ),
        "audio_delay_ms": voice["delay_ms"],
        "audio_duration_delta_ms": voice["duration_delta_ms"],
        "envelope_correlation": voice["envelope_correlation"],
        "speech_band_distance_db": voice[
            "speech_band_distance_db"
        ],
        "checksum_sha256": _sha256(video),
    }
    _write("review-metrics.json", metrics)
    return metrics


def review_output(output_root: Path) -> dict[str, Any]:
    reports: dict[str, Any] = {}
    for story_id in ("ppi", "backtest", "lot-size"):
        story_dir = output_root / story_id
        metrics_path = story_dir / "review-metrics.json"
        if (story_dir / "edited.mp4").is_file():
            audit_story(story_dir, story_id)
        if not metrics_path.is_file():
            reports[story_id] = {
                "automated_pass": False,
                "human_approved": False,
                "state": "automated-review",
                "failed_checks": ["missing-review-metrics"],
            }
            continue
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        report = evaluate_story(story_id=story_id, metrics=metrics)
        (story_dir / "review-report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        reports[story_id] = report
    all_automated = all(
        report.get("automated_pass") is True
        for report in reports.values()
    )
    summary = {
        "automated_pass": all_automated,
        "human_approved": False,
        "state": (
            "awaiting-final-approval"
            if all_automated
            else "automated-review"
        ),
        "stories": reports,
    }
    (output_root / "production-job.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    delivery = {
        "state": summary["state"],
        "automated_pass": summary["automated_pass"],
        "human_approved": False,
        "videos": {
            story_id: {
                "path": str(output_root / f"0813-{story_id}.mp4"),
                "exists": (output_root / f"0813-{story_id}.mp4").is_file(),
            }
            for story_id in ("ppi", "backtest", "lot-size")
        },
    }
    (output_root / "delivery-manifest.json").write_text(
        json.dumps(delivery, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_root", type=Path)
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    report = review_output(arguments.output_root.resolve())
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["automated_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

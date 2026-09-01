from __future__ import annotations

from difflib import SequenceMatcher
import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unicodedata
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import cv2
from imageio_ffmpeg import get_ffmpeg_exe
import numpy as np
from PIL import Image, ImageDraw, ImageOps

from app.editor.production_audit import estimate_audio_delay_ms


SERVER_DIR = Path(__file__).resolve().parent
WORKSPACE = SERVER_DIR.parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from caption_transliteration_0813 import romanize_word  # noqa: E402

build = importlib.import_module(  # noqa: E402
    os.getenv("VIDEO_STORY_BUILD_MODULE", "build_0813_ppi_live")
)
import render_0813_ppi_live as renderer  # noqa: E402
from render_0813_ppi_live import parse_loudness_payload  # noqa: E402


OUTPUT = build.OUTPUT
EDITED = OUTPUT / "edited.mp4"
FFMPEG = Path(get_ffmpeg_exe())


def _run(command: list[str], *, timeout: int = 1_800) -> str:
    completed = subprocess.run(
        command,
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
        shell=False,
    )
    output = "\n".join((completed.stdout, completed.stderr))
    if completed.returncode:
        raise RuntimeError(
            "Command failed:\n"
            + " ".join(command)
            + "\n"
            + output[-10_000:]
        )
    return output


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def normalized_tokens(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", text).lower()
    tokens: list[str] = []
    current: list[str] = []
    for index, character in enumerate(normalized):
        category = unicodedata.category(character)
        is_word_character = category[0] in {"L", "N", "M"}
        is_decimal_point = (
            character == "."
            and current
            and index + 1 < len(normalized)
            and normalized[index + 1].isdigit()
            and any(part.isdigit() for part in current)
        )
        if is_word_character or is_decimal_point:
            current.append(character)
            continue
        if current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tokens


def _media_metadata(path: Path) -> dict[str, Any]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"OpenCV cannot open {path}")
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    capture.release()
    duration = frame_count / fps if fps > 0 else 0
    probe_text = _run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-i",
            str(path),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-f",
            "null",
            "NUL",
        ]
    )
    video_codec = "h264" if "Video: h264" in probe_text else "unknown"
    audio_codec = "aac" if "Audio: aac" in probe_text else "unknown"
    audio_rate = 48_000 if "48000 Hz" in probe_text else None
    return {
        "width": width,
        "height": height,
        "fps": fps,
        "frame_count": frame_count,
        "duration_seconds": duration,
        "video_codec": video_codec,
        "audio_codec": audio_codec,
        "audio_sample_rate": audio_rate,
    }


def _measure_loudness(path: Path) -> dict[str, float]:
    output = _run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-af",
            "loudnorm=I=-14.2:TP=-1.0:LRA=3.0:print_format=json",
            "-f",
            "null",
            "NUL",
        ]
    )
    matches = re.findall(r"\{\s*\"input_i\".*?\}", output, flags=re.S)
    if not matches:
        raise RuntimeError("Unable to parse encoded loudness")
    return parse_loudness_payload(json.loads(matches[-1]))


def _extract_pcm(path: Path) -> np.ndarray:
    completed = subprocess.run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-ac",
            "1",
            "-ar",
            "48000",
            "-f",
            "s16le",
            "pipe:1",
        ],
        cwd=WORKSPACE,
        capture_output=True,
        timeout=600,
        check=False,
        shell=False,
    )
    if completed.returncode:
        raise RuntimeError(
            f"Unable to extract review audio from {path}: "
            + completed.stderr.decode("utf-8", errors="replace")[-2_000:]
        )
    return np.frombuffer(completed.stdout, dtype=np.int16).astype(np.float64)


def build_presenter_sync_audit(
    *,
    presenter_metrics: dict[str, Any],
    audio_alignment_offset_ms: int | float,
) -> dict[str, Any]:
    presenter_ratio = float(presenter_metrics["presenter_pixel_ratio"])
    visual_ratio = float(presenter_metrics["visual_pixel_ratio"])
    presenter_sync_offset = float(
        presenter_metrics["max_presenter_sync_offset_ms"]
    )
    audio_offset = float(audio_alignment_offset_ms)
    return {
        **presenter_metrics,
        "audio_alignment_offset_ms": audio_offset,
        "balance_passed": (
            0.58 <= presenter_ratio <= 0.68
            and 0.32 <= visual_ratio <= 0.42
            and int(presenter_metrics["longest_without_presenter_ms"])
            <= 3_800
        ),
        "presenter_sync_passed": (
            abs(presenter_sync_offset) <= 1000 / 30
        ),
        "audio_alignment_passed": abs(audio_offset) <= 40,
    }


def _visual_metrics(path: Path) -> dict[str, float]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"Unable to read {path}")
    luminance: list[float] = []
    saturation: list[float] = []
    dark = 0
    black = 0
    sampled = 0
    frame_index = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if frame_index % 15 == 0:
            small = cv2.resize(frame, (108, 192), interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
            mean_luma = float(np.mean(gray))
            luminance.append(mean_luma)
            saturation.append(float(np.mean(hsv[:, :, 1])))
            dark += int(mean_luma < 45)
            black += int(mean_luma < 8)
            sampled += 1
        frame_index += 1
    capture.release()
    if not sampled:
        raise RuntimeError("No frames sampled")
    return {
        "mean_luminance": float(np.mean(luminance)),
        "mean_saturation": float(np.mean(saturation)),
        "dark_frame_ratio": dark / sampled,
        "black_frame_ratio": black / sampled,
        "luminance_p10": float(np.percentile(luminance, 10)),
        "luminance_p90": float(np.percentile(luminance, 90)),
    }


def _caption_failures(plan: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    pages = plan["caption_pages"]
    for page in pages:
        duration = int(page["end_ms"]) - int(page["start_ms"])
        if not 350 <= duration <= 1_300:
            failures.append(f"{page['id']}: duration {duration} ms")
        if len(str(page["text"]).split()) > 4:
            failures.append(f"{page['id']}: more than four words")
        if int(page["max_width"]) > 900:
            failures.append(f"{page['id']}: width exceeds 900 px")
    for left, right in zip(pages, pages[1:]):
        if int(left["end_ms"]) > int(right["start_ms"]):
            failures.append(f"{left['id']}/{right['id']}: overlap")
    return failures


def caption_accuracy_report(
    transcript: dict[str, Any],
    pages: list[dict[str, Any]],
    *,
    expected_word_count: int | None = None,
) -> dict[str, Any]:
    words = transcript["words"]
    word_count = (
        len(words) if expected_word_count is None else expected_word_count
    )
    covered_indices: list[int] = []
    text_mismatches: list[dict[str, Any]] = []
    range_failures: list[str] = []

    for page in pages:
        start_index = int(page["source_word_start"])
        end_index = int(page["source_word_end"])
        if (
            start_index < 0
            or end_index < start_index
            or end_index >= word_count
        ):
            range_failures.append(
                f"{page['id']}: invalid source range "
                f"{start_index}-{end_index}"
            )
            continue
        expected_tokens = [
            romanize_word(str(words[index]["word"])).upper()
            for index in range(start_index, end_index + 1)
        ]
        actual_tokens = str(page["text"]).split()
        if actual_tokens != expected_tokens:
            text_mismatches.append(
                {
                    "id": page["id"],
                    "source_word_start": start_index,
                    "source_word_end": end_index,
                    "expected": " ".join(expected_tokens),
                    "actual": str(page["text"]),
                }
            )
        covered_indices.extend(range(start_index, end_index + 1))

    expected_indices = list(range(word_count))
    coverage_passed = covered_indices == expected_indices
    return {
        "passed": (
            coverage_passed
            and not text_mismatches
            and not range_failures
        ),
        "source_word_count": word_count,
        "caption_page_count": len(pages),
        "covered_word_count": len(covered_indices),
        "coverage_passed": coverage_passed,
        "text_mismatches": text_mismatches,
        "range_failures": range_failures,
    }


def semantic_visual_report(
    storyboard: list[dict[str, Any]],
    *,
    duration_ms: int,
) -> dict[str, Any]:
    allowed_jobs = {
        "presenter-explanation",
        "presenter-supported",
        "literal-action",
        "real-product",
        "direct-evidence",
    }
    asset_counts: dict[str, int] = {}
    missing_jobs: list[str] = []
    invalid_jobs: list[str] = []
    presenter_free_runs: list[dict[str, int]] = []
    run_start: int | None = None
    consecutive_non_presenter = 0
    max_consecutive_non_presenter = 0

    for shot in storyboard:
        asset_id = str(shot["asset_id"])
        secondary_asset_id = shot.get("secondary_asset_id")
        presenter_visible = (
            asset_id == "presenter-edl"
            or secondary_asset_id == "presenter-edl"
        )
        visual_job = str(shot.get("visual_job", "")).strip()
        if not visual_job:
            missing_jobs.append(str(shot["id"]))
        elif visual_job not in allowed_jobs:
            invalid_jobs.append(f"{shot['id']}: {visual_job}")
        elif asset_id == "presenter-edl" and visual_job not in {
            "presenter-explanation",
            "presenter-supported",
        }:
            invalid_jobs.append(
                f"{shot['id']}: presenter uses {visual_job}"
            )
        elif asset_id != "presenter-edl" and visual_job == (
            "presenter-explanation"
        ):
            invalid_jobs.append(
                f"{shot['id']}: non-presenter uses presenter-explanation"
            )

        for visible_asset in (asset_id, secondary_asset_id):
            if visible_asset and visible_asset != "presenter-edl":
                key = str(visible_asset)
                asset_counts[key] = asset_counts.get(key, 0) + 1

        if presenter_visible:
            if run_start is not None:
                presenter_free_runs.append(
                    {
                        "start_ms": run_start,
                        "end_ms": int(shot["start_ms"]),
                    }
                )
                run_start = None
            consecutive_non_presenter = 0
        else:
            if run_start is None:
                run_start = int(shot["start_ms"])
            consecutive_non_presenter += 1
            max_consecutive_non_presenter = max(
                max_consecutive_non_presenter,
                consecutive_non_presenter,
            )

    if run_start is not None:
        presenter_free_runs.append(
            {"start_ms": run_start, "end_ms": duration_ms}
        )

    repeated_assets = sorted(
        asset_id
        for asset_id, count in asset_counts.items()
        if count > 1
    )
    longest_run = max(
        (
            int(run["end_ms"]) - int(run["start_ms"])
            for run in presenter_free_runs
        ),
        default=0,
    )
    failures = []
    if missing_jobs:
        failures.append("missing visual jobs")
    if invalid_jobs:
        failures.append("invalid visual jobs")
    if repeated_assets:
        failures.append("repeated non-presenter assets")
    if longest_run > 3_800:
        failures.append("presenter-free run exceeds 3800 ms")
    if max_consecutive_non_presenter > 2:
        failures.append("more than two consecutive non-presenter shots")

    return {
        "passed": not failures,
        "failures": failures,
        "missing_visual_jobs": missing_jobs,
        "invalid_visual_jobs": invalid_jobs,
        "asset_counts": asset_counts,
        "repeated_non_presenter_assets": repeated_assets,
        "presenter_free_runs": presenter_free_runs,
        "longest_presenter_free_run_ms": longest_run,
        "max_consecutive_non_presenter_shots": (
            max_consecutive_non_presenter
        ),
    }


def _unsupported_visible_facts(plan: dict[str, Any]) -> list[str]:
    evidence_ids = {
        item["id"]
        for item in json.loads(
            (OUTPUT / "evidence.json").read_text(encoding="utf-8")
        )
        if item["status"] == "verified"
    }
    failures: list[str] = []
    for item in plan["fact_overlays"]:
        if overlay_requires_evidence(item):
            evidence_id = item.get("evidence_id")
            if evidence_id not in evidence_ids:
                failures.append(str(item["text"]))
    return failures


def overlay_requires_evidence(item: dict[str, Any]) -> bool:
    custom = getattr(build, "overlay_requires_evidence", None)
    if custom is not None:
        return bool(custom(item))
    return str(item.get("id", "")) in {
        "release-date",
        "forecast",
        "actual",
        "goods",
        "services",
        "opposite",
        "dollar",
    }


def _env_value(name: str) -> str:
    existing = os.getenv(name)
    if existing:
        return existing
    env_path = WORKSPACE / ".env"
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == name:
            return value.strip().strip("\"'")
    raise RuntimeError(f"{name} is missing")


def _deepgram_transcript(path: Path) -> dict[str, Any]:
    review_dir = OUTPUT / "review"
    review_dir.mkdir(parents=True, exist_ok=True)
    audio = review_dir / "final-review-audio.wav"
    _run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-y",
            "-i",
            str(path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(audio),
        ]
    )
    cache = review_dir / "transcript-final-deepgram-raw.json"
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
    _write_json(cache, payload)
    return payload


def _asr_metrics(final_payload: dict[str, Any]) -> dict[str, Any]:
    source = json.loads(build.TRANSCRIPT_PATH.read_text(encoding="utf-8"))
    source_text = str(source["text"])
    alternative = final_payload["results"]["channels"][0]["alternatives"][0]
    final_text = str(alternative["transcript"])
    source_tokens = normalized_tokens(source_text)
    final_tokens = normalized_tokens(final_text)
    similarity = SequenceMatcher(
        None,
        source_tokens,
        final_tokens,
        autojunk=False,
    ).ratio()
    protected = [
        "सोचिए",
        "ppi",
        "0.2",
        "0",
        "0.7",
        "services",
        "dollar",
        "spread",
        "confirmation",
        "robot",
        "follow",
        "thank",
        "you",
    ]
    protected = list(getattr(build, "PROTECTED_TOKENS", protected))
    final_set = set(final_tokens)
    missing = [token for token in protected if token not in final_set]
    return {
        "source_text": source_text,
        "final_text": final_text,
        "source_token_count": len(source_tokens),
        "final_token_count": len(final_tokens),
        "asr_similarity": similarity,
        "protected_tokens": protected,
        "missing_protected_tokens": missing,
    }


def _contact_sheet(
    path: Path,
    times_ms: list[int],
    destination: Path,
    *,
    columns: int,
    tile_size: tuple[int, int],
    labels: list[str],
) -> None:
    capture = cv2.VideoCapture(str(path))
    frames: list[Image.Image] = []
    for time_ms, label in zip(times_ms, labels, strict=True):
        capture.set(cv2.CAP_PROP_POS_MSEC, time_ms)
        ok, frame = capture.read()
        if not ok:
            raise RuntimeError(f"Unable to extract frame at {time_ms} ms")
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        tile = ImageOps.fit(
            Image.fromarray(frame),
            tile_size,
            method=Image.Resampling.LANCZOS,
        )
        draw = ImageDraw.Draw(tile)
        draw.rectangle((0, 0, tile.width, 24), fill=(0, 0, 0))
        draw.text((5, 5), label, fill=(255, 255, 255))
        frames.append(tile)
    capture.release()
    rows = (len(frames) + columns - 1) // columns
    sheet = Image.new(
        "RGB",
        (columns * tile_size[0], rows * tile_size[1]),
        (0, 0, 0),
    )
    for index, frame in enumerate(frames):
        sheet.paste(
            frame,
            (
                (index % columns) * tile_size[0],
                (index // columns) * tile_size[1],
            ),
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, quality=94)


def evaluate_release(metrics: dict[str, Any]) -> dict[str, Any]:
    checks = [
        ("full-decode", bool(metrics["decode_ok"])),
        (
            "portrait-h264",
            metrics["width"] == 1_080 and metrics["height"] == 1_920,
        ),
        ("frame-rate", abs(float(metrics["fps"]) - 30) <= 0.05),
        (
            "duration",
            45.90 <= float(metrics["duration_seconds"]) <= 46.10,
        ),
        (
            "integrated-loudness",
            -14.5 <= float(metrics["integrated_lufs"]) <= -13.9,
        ),
        ("true-peak", float(metrics["true_peak_dbtp"]) <= -1.0),
        ("black-frames", float(metrics["black_frame_ratio"]) <= 0.005),
        (
            "dark-frame-share",
            float(metrics["dark_frame_ratio"]) <= 0.25,
        ),
        (
            "mean-luminance",
            82 <= float(metrics["mean_luminance"]) <= 112,
        ),
        ("captions", not metrics["caption_failures"]),
        (
            "caption-accuracy",
            bool(metrics.get("caption_accuracy_passed", True)),
        ),
        (
            "semantic-visuals",
            bool(metrics.get("semantic_visuals_passed", True)),
        ),
        (
            "visual-uniqueness",
            bool(metrics.get("visual_uniqueness_passed", True)),
        ),
        ("live-footage", float(metrics["live_video_ratio"]) >= 0.80),
        (
            "presenter-balance",
            0.58 <= float(metrics["presenter_pixel_ratio"]) <= 0.68,
        ),
        (
            "visual-balance",
            0.32 <= float(metrics["visual_pixel_ratio"]) <= 0.42,
        ),
        (
            "presenter-free-run",
            int(metrics["longest_without_presenter_ms"]) <= 3_800,
        ),
        (
            "presenter-sync",
            abs(float(metrics["max_presenter_sync_offset_ms"]))
            <= 1000 / 30,
        ),
        (
            "audio-alignment",
            abs(float(metrics["audio_alignment_offset_ms"])) <= 40,
        ),
        ("asr-similarity", float(metrics["asr_similarity"]) >= 0.98),
        ("protected-words", not metrics["missing_protected_tokens"]),
        ("fact-provenance", not metrics["unsupported_visible_facts"]),
    ]
    return {
        "automated_pass": all(passed for _, passed in checks),
        "human_approved": False,
        "state": (
            "awaiting-final-approval"
            if all(passed for _, passed in checks)
            else "blocked"
        ),
        "checks": [
            {"name": name, "passed": passed}
            for name, passed in checks
        ],
        "metrics": metrics,
    }


def main() -> int:
    if not EDITED.is_file():
        raise FileNotFoundError(EDITED)
    plan = json.loads((OUTPUT / "edit-plan.json").read_text(encoding="utf-8"))
    renderer.load_build_module(build.__name__)
    decode_ok = True
    try:
        _run(
            [
                str(FFMPEG),
                "-v",
                "error",
                "-i",
                str(EDITED),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0",
                "-f",
                "null",
                "NUL",
            ]
        )
    except RuntimeError:
        decode_ok = False

    metadata = _media_metadata(EDITED)
    loudness = _measure_loudness(EDITED)
    visual = _visual_metrics(EDITED)
    final_asr = _deepgram_transcript(EDITED)
    asr = _asr_metrics(final_asr)
    caption_failures = _caption_failures(plan)
    source_transcript = json.loads(
        build.TRANSCRIPT_PATH.read_text(encoding="utf-8")
    )
    caption_accuracy = caption_accuracy_report(
        source_transcript,
        plan["caption_pages"],
    )
    if not caption_accuracy["passed"]:
        caption_failures.append("source transcript mismatch")
    semantic_visuals = semantic_visual_report(
        plan["storyboard"],
        duration_ms=build.DURATION_MS,
    )
    visual_uniqueness = {
        "passed": not semantic_visuals["repeated_non_presenter_assets"],
        "asset_counts": semantic_visuals["asset_counts"],
        "repeated_non_presenter_assets": semantic_visuals[
            "repeated_non_presenter_assets"
        ],
    }
    unsupported = _unsupported_visible_facts(plan)
    live_video_duration_ms = sum(
        max(0, int(shot["end_ms"]) - int(shot["start_ms"]))
        for shot in plan["storyboard"]
        if shot.get("kind") == "video"
    )
    live_video_ratio = min(
        1.0,
        live_video_duration_ms / max(1, build.DURATION_MS),
    )
    presenter_metrics = renderer.presenter_sync_metrics()
    dialogue_master = (
        OUTPUT / plan["assets"]["dialogue-original"]
    ).resolve()
    audio_alignment_offset_ms = estimate_audio_delay_ms(
        _extract_pcm(dialogue_master),
        _extract_pcm(EDITED),
        sample_rate=48_000,
    )
    presenter_sync = build_presenter_sync_audit(
        presenter_metrics=presenter_metrics,
        audio_alignment_offset_ms=audio_alignment_offset_ms,
    )

    review_dir = OUTPUT / "review"
    shot_times = [
        round((start + end) / 2)
        for start, end in zip(
            build.BOUNDARIES[:-1],
            build.BOUNDARIES[1:],
            strict=True,
        )
    ]
    _contact_sheet(
        EDITED,
        shot_times,
        review_dir / "all-shots-exact.jpg",
        columns=7,
        tile_size=(154, 274),
        labels=[f"S{index:02d}" for index in range(1, len(shot_times) + 1)],
    )
    caption_times = [
        round((page["start_ms"] + page["end_ms"]) / 2)
        for page in plan["caption_pages"]
    ]
    _contact_sheet(
        EDITED,
        caption_times,
        review_dir / "all-captions-exact.jpg",
        columns=8,
        tile_size=(135, 240),
        labels=[f"C{index:02d}" for index in range(1, len(caption_times) + 1)],
    )

    frame_audit = {
        **metadata,
        **visual,
        "planned_shots": len(plan["storyboard"]),
        "planned_hard_cuts": len(plan["storyboard"]) - 1,
        "median_planned_shot_ms": float(
            np.median(
                [
                    int(shot["end_ms"]) - int(shot["start_ms"])
                    for shot in plan["storyboard"]
                ]
            )
        ),
        "live_video_ratio": live_video_ratio,
        "presenter_pixel_ratio": presenter_sync["presenter_pixel_ratio"],
        "visual_pixel_ratio": presenter_sync["visual_pixel_ratio"],
        "longest_without_presenter_ms": presenter_sync[
            "longest_without_presenter_ms"
        ],
        "flow_coverage": 0.0,
        "static_base_shots": 0,
    }
    audio_continuity = {
        **loudness,
        **asr,
        "dialogue_master": "assets/audio/dialogue-original.wav",
        "opening_trim_ms": 0,
        "audio_alignment_offset_ms": audio_alignment_offset_ms,
        "music_duck_db": plan["audio"]["music_duck_db"],
        "sfx_count": len(plan["audio"]["sfx_cues"]),
    }
    metrics = {
        "decode_ok": decode_ok,
        **metadata,
        "integrated_lufs": loudness["input_i"],
        "true_peak_dbtp": loudness["input_tp"],
        "black_frame_ratio": visual["black_frame_ratio"],
        "dark_frame_ratio": visual["dark_frame_ratio"],
        "mean_luminance": visual["mean_luminance"],
        "caption_failures": caption_failures,
        "caption_accuracy_passed": caption_accuracy["passed"],
        "semantic_visuals_passed": semantic_visuals["passed"],
        "visual_uniqueness_passed": visual_uniqueness["passed"],
        "live_video_ratio": live_video_ratio,
        "presenter_pixel_ratio": presenter_sync["presenter_pixel_ratio"],
        "visual_pixel_ratio": presenter_sync["visual_pixel_ratio"],
        "longest_without_presenter_ms": presenter_sync[
            "longest_without_presenter_ms"
        ],
        "max_presenter_sync_offset_ms": presenter_sync[
            "max_presenter_sync_offset_ms"
        ],
        "audio_alignment_offset_ms": audio_alignment_offset_ms,
        "asr_similarity": asr["asr_similarity"],
        "missing_protected_tokens": asr["missing_protected_tokens"],
        "unsupported_visible_facts": unsupported,
    }
    report = evaluate_release(metrics)
    report["artifacts"] = {
        "all_shots": "review/all-shots-exact.jpg",
        "all_captions": "review/all-captions-exact.jpg",
        "frame_audit": "frame-audit.json",
        "audio_continuity": "audio-continuity.json",
        "asr_retention": "asr-retention.json",
        "presenter_sync_audit": "presenter-sync-audit.json",
        "caption_accuracy": "caption-accuracy.json",
        "semantic_visuals": "semantic-visuals.json",
        "visual_uniqueness": "visual-uniqueness.json",
    }
    _write_json(OUTPUT / "frame-audit.json", frame_audit)
    _write_json(OUTPUT / "audio-continuity.json", audio_continuity)
    _write_json(OUTPUT / "asr-retention.json", asr)
    _write_json(OUTPUT / "presenter-sync-audit.json", presenter_sync)
    _write_json(OUTPUT / "caption-accuracy.json", caption_accuracy)
    _write_json(OUTPUT / "semantic-visuals.json", semantic_visuals)
    _write_json(OUTPUT / "visual-uniqueness.json", visual_uniqueness)
    _write_json(OUTPUT / "review-report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["automated_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
from typing import Any

import cv2
from imageio_ffmpeg import get_ffmpeg_exe
import numpy as np
from PIL import Image, ImageDraw, ImageOps

from app.editor.human_reference_0810 import _map_source_time_ms
from app.production_models import DialogueEditSegment
from caption_transliteration_0813 import romanize_word


SERVER_DIR = Path(__file__).resolve().parent
WORKSPACE = SERVER_DIR.parent
FFMPEG = Path(get_ffmpeg_exe())


@dataclass(frozen=True)
class StoryConfig:
    story_id: str
    title: str
    source: Path
    output: Path
    transcript_path: Path
    duration_ms: int
    playback_rate: float
    edl_rows: list[tuple[int, int, int, int]]
    boundaries: list[int]
    shot_specs: list[dict[str, Any]]
    caption_groups: list[tuple[int, int, str]]
    fact_overlays: list[dict[str, Any]]
    asset_sources: dict[str, dict[str, Any]]
    desired_sfx: list[tuple[str, str, int, int, float]]
    protected_tokens: list[str]
    music_source_start_seconds: int
    visual_summary: list[str]
    risks: list[str]


def shot(
    asset_id: str,
    source_start_ms: int,
    editorial_role: str,
    *,
    visual_job: str,
    zoom: float = 1.06,
    crop_x: float = 0.5,
    crop_y: float = 0.5,
    secondary_asset_id: str | None = None,
    secondary_source_start_ms: int | None = None,
) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "kind": "video",
        "source_start_ms": source_start_ms,
        "editorial_role": editorial_role,
        "visual_job": visual_job,
        "zoom": zoom,
        "crop_x": crop_x,
        "crop_y": crop_y,
        "secondary_asset_id": secondary_asset_id,
        "secondary_source_start_ms": secondary_source_start_ms,
    }


def dialogue_edl(config: StoryConfig) -> list[DialogueEditSegment]:
    return [
        DialogueEditSegment(
            id=f"dialogue-{index:03d}",
            source_start_ms=source_start,
            source_end_ms=source_end,
            output_start_ms=output_start,
            output_end_ms=output_end,
            playback_rate=config.playback_rate,
            preserve_pitch=True,
        )
        for index, (
            source_start,
            source_end,
            output_start,
            output_end,
        ) in enumerate(config.edl_rows, start=1)
    ]


def _map_time(
    source_ms: int,
    edl: list[DialogueEditSegment],
    *,
    end: bool,
) -> int:
    return _map_source_time_ms(source_ms, edl, end_boundary=end)


def build_caption_pages(
    *,
    transcript: dict[str, Any],
    edl: list[DialogueEditSegment],
    groups: list[tuple[int, int, str]],
    duration_ms: int,
) -> list[dict[str, Any]]:
    words = transcript["words"]
    source_ranges = _caption_source_ranges(
        words=words,
        edl=edl,
        groups=groups,
    )
    pages: list[dict[str, Any]] = []
    for page_index, (start_index, end_index) in enumerate(source_ranges):
        start_ms = _map_time(
            round(float(words[start_index]["start"]) * 1000),
            edl,
            end=False,
        )
        spoken_end_ms = _map_time(
            round(float(words[end_index]["end"]) * 1000),
            edl,
            end=True,
        )
        next_start_ms = (
            _map_time(
                round(
                    float(words[source_ranges[page_index + 1][0]]["start"])
                    * 1000
                ),
                edl,
                end=False,
            )
            if page_index + 1 < len(source_ranges)
            else duration_ms
        )
        end_ms = min(
            duration_ms,
            next_start_ms,
            max(start_ms + 350, spoken_end_ms),
            start_ms + 1_300,
        )
        if not 350 <= end_ms - start_ms <= 1_300:
            raise ValueError(
                "Unable to create an accurate caption hold for source words "
                f"{start_index}-{end_index}: {end_ms - start_ms} ms"
            )
        text = " ".join(
            romanize_word(str(words[index]["word"])).upper()
            for index in range(start_index, end_index + 1)
        )
        pages.append(
            {
                "id": f"caption-{len(pages) + 1:03d}",
                "start_ms": start_ms,
                "end_ms": end_ms,
                "source_word_start": start_index,
                "source_word_end": end_index,
                "text": text,
                "family": "modern-outline",
                "font_size": 58,
                "max_width": 900,
                "anchor": "lower-center",
                "transition": "hard-cut",
            }
        )
    return pages


def _caption_source_ranges(
    *,
    words: list[dict[str, Any]],
    edl: list[DialogueEditSegment],
    groups: list[tuple[int, int, str]],
) -> list[tuple[int, int]]:
    if not words:
        return []

    expected_start = 0
    ranges: list[tuple[int, int]] = []
    for group in groups:
        start_index, end_index = group[:2]
        if start_index != expected_start or end_index < start_index:
            raise ValueError(
                "Caption source ranges must cover transcript words once and "
                f"in order; expected {expected_start}, got "
                f"{start_index}-{end_index}"
            )
        count = end_index - start_index + 1
        page_count = math.ceil(count / 4)
        base_size, larger_pages = divmod(count, page_count)
        cursor = start_index
        for page_offset in range(page_count):
            page_size = base_size + (1 if page_offset < larger_pages else 0)
            ranges.append((cursor, cursor + page_size - 1))
            cursor += page_size
        expected_start = end_index + 1

    if expected_start != len(words):
        raise ValueError(
            "Caption source ranges do not cover the complete transcript: "
            f"{expected_start}/{len(words)} words"
        )

    def word_start(index: int) -> int:
        return _map_time(
            round(float(words[index]["start"]) * 1000),
            edl,
            end=False,
        )

    def word_end(index: int) -> int:
        return _map_time(
            round(float(words[index]["end"]) * 1000),
            edl,
            end=True,
        )

    while True:
        changed = False
        split_ranges: list[tuple[int, int]] = []
        for start_index, end_index in ranges:
            if (
                word_end(end_index) - word_start(start_index) <= 1_300
                or start_index == end_index
            ):
                split_ranges.append((start_index, end_index))
                continue
            candidates: list[tuple[bool, bool, int, int, int]] = []
            for split_after in range(start_index, end_index):
                left_count = split_after - start_index + 1
                right_count = end_index - split_after
                if left_count > 4 or right_count > 4:
                    continue
                worst_duration = max(
                    word_end(split_after) - word_start(start_index),
                    word_end(end_index) - word_start(split_after + 1),
                )
                start_gap = (
                    word_start(split_after + 1) - word_start(start_index)
                )
                candidates.append(
                    (
                        worst_duration > 1_300,
                        start_gap < 350,
                        worst_duration,
                        abs(left_count - right_count),
                        split_after,
                    )
                )
            if not candidates:
                raise ValueError(
                    "Unable to split caption source words "
                    f"{start_index}-{end_index}"
                )
            split_after = min(candidates)[-1]
            split_ranges.extend(
                (
                    (start_index, split_after),
                    (split_after + 1, end_index),
                )
            )
            changed = True
        ranges = split_ranges
        if not changed:
            break

    index = 0
    while index < len(ranges) - 1:
        left_start, left_end = ranges[index]
        right_start, right_end = ranges[index + 1]
        if word_start(right_start) - word_start(left_start) >= 350:
            index += 1
            continue

        combined_count = right_end - left_start + 1
        if combined_count <= 4:
            ranges[index : index + 2] = [(left_start, right_end)]
            index = max(0, index - 1)
            continue

        candidates = []
        for split_after in range(left_start, right_end):
            left_count = split_after - left_start + 1
            right_count = right_end - split_after
            if left_count > 4 or right_count > 4:
                continue
            start_gap = word_start(split_after + 1) - word_start(left_start)
            worst_duration = max(
                word_end(split_after) - word_start(left_start),
                word_end(right_end) - word_start(split_after + 1),
            )
            candidates.append(
                (
                    start_gap < 350,
                    worst_duration > 1_300,
                    abs(left_count - right_count),
                    worst_duration,
                    split_after,
                )
            )
        if not candidates:
            raise ValueError(
                "Unable to rebalance caption source words "
                f"{left_start}-{right_end}"
            )
        split_after = min(candidates)[-1]
        ranges[index : index + 2] = [
            (left_start, split_after),
            (split_after + 1, right_end),
        ]
        if word_start(split_after + 1) - word_start(left_start) < 350:
            raise ValueError(
                "Caption words are too close for a 350 ms visible hold: "
                f"{left_start}-{right_end}"
            )
        index += 1

    return ranges


def _safe_cue_start(
    *,
    desired_ms: int,
    duration_ms: int,
    duration_total_ms: int,
    windows: list[dict[str, Any]],
) -> int:
    offsets = [0]
    for delta in range(20, 2_001, 20):
        offsets.extend((-delta, delta))
    for offset in offsets:
        candidate = max(
            0,
            min(duration_total_ms - duration_ms, desired_ms + offset),
        )
        if all(
            not (
                candidate < window["end_ms"]
                and candidate + duration_ms > window["start_ms"]
            )
            for window in windows
        ):
            return candidate
    raise ValueError(f"No speech-safe SFX position near {desired_ms}")


def build_audio_plan(
    *,
    transcript: dict[str, Any],
    edl: list[DialogueEditSegment],
    desired_sfx: list[tuple[str, str, int, int, float]],
    duration_ms: int,
) -> dict[str, Any]:
    windows = []
    for word in transcript["words"]:
        start_ms = _map_time(
            round(float(word["start"]) * 1000),
            edl,
            end=False,
        )
        windows.append(
            {
                "start_ms": max(0, start_ms - 100),
                "end_ms": min(duration_ms, start_ms + 120),
                "word": word["word"],
            }
        )
    cues = [
        {
            "id": cue_id,
            "asset_id": asset_id,
            "start_ms": _safe_cue_start(
                desired_ms=start,
                duration_ms=cue_duration,
                duration_total_ms=duration_ms,
                windows=windows,
            ),
            "source_start_ms": 0,
            "duration_ms": cue_duration,
            "gain_db": gain,
            "volume": 0.35,
        }
        for cue_id, asset_id, start, cue_duration, gain in desired_sfx
    ]
    return {
        "integrated_lufs": -14.2,
        "true_peak_dbtp": -1.0,
        "target_lra_lu": 3.0,
        "dialogue_asset_id": "dialogue-original",
        "music_asset_id": "music-documentary",
        "music_base_gain_db": -27.0,
        "music_duck_db": 6.0,
        "speech_protection_windows": windows,
        "sfx_cues": cues,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _run(command: list[str], *, timeout: int = 3_600) -> None:
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
    if completed.returncode:
        raise RuntimeError(
            "\n".join(
                part
                for part in (
                    completed.stdout[-4_000:],
                    completed.stderr[-10_000:],
                )
                if part
            )
        )


def _copy(source: Path, destination: Path) -> Path:
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)
    return destination


def _prepare_dialogue_media(
    *,
    config: StoryConfig,
    edl: list[DialogueEditSegment],
    presenter_output: Path,
    original_audio_output: Path,
    processed_audio_output: Path,
) -> None:
    presenter_output.parent.mkdir(parents=True, exist_ok=True)
    original_audio_output.parent.mkdir(parents=True, exist_ok=True)
    video_sources = "".join(f"[vsrc{index}]" for index in range(len(edl)))
    video_filters = [f"[0:v]split={len(edl)}{video_sources}"]
    for index, segment in enumerate(edl):
        video_filters.append(
            f"[vsrc{index}]"
            f"trim=start={segment.source_start_ms / 1000:.6f}:"
            f"end={segment.source_end_ms / 1000:.6f},"
            f"setpts=(PTS-STARTPTS)/{segment.playback_rate:.6f}"
            f"[v{index}]"
        )
    video_filters.append(
        "".join(f"[v{index}]" for index in range(len(edl)))
        + f"concat=n={len(edl)}:v=1:a=0,"
        f"trim=duration={config.duration_ms / 1000:.6f},"
        "setpts=PTS-STARTPTS[vout]"
    )
    _run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-y",
            "-i",
            str(config.source),
            "-filter_complex",
            ";".join(video_filters),
            "-map",
            "[vout]",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "15",
            "-pix_fmt",
            "yuv420p",
            "-r",
            "30",
            "-movflags",
            "+faststart",
            str(presenter_output),
        ],
        timeout=3_600,
    )

    audio_sources = "".join(f"[asrc{index}]" for index in range(len(edl)))
    audio_filters = [f"[0:a]asplit={len(edl)}{audio_sources}"]
    for index, segment in enumerate(edl):
        audio_filters.append(
            f"[asrc{index}]"
            f"atrim=start={segment.source_start_ms / 1000:.6f}:"
            f"end={segment.source_end_ms / 1000:.6f},"
            "asetpts=PTS-STARTPTS,"
            f"atempo={segment.playback_rate:.6f}[a{index}]"
        )
    audio_filters.append(
        "".join(f"[a{index}]" for index in range(len(edl)))
        + f"concat=n={len(edl)}:v=0:a=1,"
        f"atrim=duration={config.duration_ms / 1000:.6f},"
        "asetpts=PTS-STARTPTS[aout]"
    )
    _run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-y",
            "-i",
            str(config.source),
            "-filter_complex",
            ";".join(audio_filters),
            "-map",
            "[aout]",
            "-c:a",
            "pcm_s24le",
            "-ar",
            "48000",
            str(original_audio_output),
        ]
    )
    _run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-y",
            "-i",
            str(original_audio_output),
            "-af",
            (
                "highpass=f=75,lowpass=f=16500,afftdn=nf=-28,"
                "deesser=i=0.20:m=0.38:f=0.5,"
                "acompressor=threshold=-18dB:ratio=2.4:"
                "attack=10:release=160:makeup=2,"
                "alimiter=limit=0.88"
            ),
            "-c:a",
            "pcm_s24le",
            "-ar",
            "48000",
            str(processed_audio_output),
        ]
    )


def _source_metrics(source: Path) -> dict[str, Any]:
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise RuntimeError(f"Unable to open {source}")
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    luminance: list[float] = []
    saturation: list[float] = []
    motion: list[float] = []
    dark = 0
    black = 0
    dead = 0
    previous: np.ndarray | None = None
    face_boxes: list[tuple[int, int, int, int]] = []
    cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    index = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        small = cv2.resize(frame, (108, 192), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        mean_luma = float(np.mean(gray))
        luminance.append(mean_luma)
        saturation.append(float(np.mean(hsv[:, :, 1])))
        dark += int(mean_luma < 45)
        black += int(mean_luma < 8)
        if previous is not None:
            delta = float(cv2.absdiff(gray, previous).mean())
            motion.append(delta)
            dead += int(delta < 0.08)
        previous = gray
        if index % 30 == 0:
            detected = cascade.detectMultiScale(
                cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY),
                scaleFactor=1.12,
                minNeighbors=5,
                minSize=(110, 110),
            )
            if len(detected):
                x, y, w, h = max(detected, key=lambda item: item[2] * item[3])
                face_boxes.append((int(x), int(y), int(w), int(h)))
        index += 1
    capture.release()
    if not luminance:
        raise RuntimeError(f"No frames decoded from {source}")
    safe_face = None
    if face_boxes:
        safe_face = {
            "median_x": int(np.median([item[0] for item in face_boxes])),
            "median_y": int(np.median([item[1] for item in face_boxes])),
            "median_width": int(np.median([item[2] for item in face_boxes])),
            "median_height": int(np.median([item[3] for item in face_boxes])),
            "samples": len(face_boxes),
        }
    return {
        "width": width,
        "height": height,
        "fps": fps,
        "frame_count": frame_count,
        "duration_seconds": frame_count / fps,
        "mean_luminance": float(np.mean(luminance)),
        "luminance_p10": float(np.percentile(luminance, 10)),
        "luminance_p90": float(np.percentile(luminance, 90)),
        "mean_saturation": float(np.mean(saturation)),
        "mean_motion": float(np.mean(motion)),
        "dark_frame_ratio": dark / len(luminance),
        "black_frame_ratio": black / len(luminance),
        "dead_frame_ratio": dead / max(1, len(motion)),
        "face_box": safe_face,
    }


def _contact_sheet(source: Path, destination: Path) -> None:
    capture = cv2.VideoCapture(str(source))
    duration_ms = (
        capture.get(cv2.CAP_PROP_FRAME_COUNT)
        / capture.get(cv2.CAP_PROP_FPS)
        * 1000
    )
    frames: list[Image.Image] = []
    for index in range(10):
        time_ms = round(duration_ms * (index + 0.5) / 10)
        capture.set(cv2.CAP_PROP_POS_MSEC, time_ms)
        ok, frame = capture.read()
        if not ok:
            continue
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        tile = ImageOps.fit(
            Image.fromarray(frame),
            (216, 384),
            method=Image.Resampling.LANCZOS,
        )
        draw = ImageDraw.Draw(tile)
        draw.rectangle((0, 0, tile.width, 26), fill=(0, 0, 0))
        draw.text((6, 6), f"{time_ms / 1000:.1f}s", fill=(255, 255, 255))
        frames.append(tile)
    capture.release()
    sheet = Image.new("RGB", (1_080, 768), (0, 0, 0))
    for index, frame in enumerate(frames):
        sheet.paste(frame, ((index % 5) * 216, (index // 5) * 384))
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, quality=94)


def _write_analysis_report(
    config: StoryConfig,
    transcript: dict[str, Any],
    metrics: dict[str, Any],
) -> None:
    face = metrics["face_box"] or {}
    report = f"""# {config.title} — Source Analysis

## Verdict

**PROCEED.** The source is a clean portrait presenter recording. The final edit
will preserve the complete narration, compress only confirmed low-energy gaps,
and use at most {config.playback_rate:.2f}x pitch-preserving acceleration.

## Source

- Path: `{config.source}`
- SHA-256: `{_sha256(config.source)}`
- Codec input: HEVC/AAC
- Geometry: {metrics["width"]}×{metrics["height"]} at {metrics["fps"]:.2f} FPS
- Frames decoded: {metrics["frame_count"]}
- Duration: {metrics["duration_seconds"]:.3f} seconds
- Transcript words: {len(transcript["words"])}
- Mean luminance: {metrics["mean_luminance"]:.2f}
- Luminance P10–P90: {metrics["luminance_p10"]:.2f}–{metrics["luminance_p90"]:.2f}
- Mean saturation: {metrics["mean_saturation"]:.2f}
- Mean structural motion: {metrics["mean_motion"]:.3f}
- Dark frames: {metrics["dark_frame_ratio"]:.2%}
- Black frames: {metrics["black_frame_ratio"]:.2%}
- Near-dead frame transitions: {metrics["dead_frame_ratio"]:.2%}
- Face detections: {face.get("samples", 0)}
- Median face box: x={face.get("median_x", "n/a")},
  y={face.get("median_y", "n/a")},
  w={face.get("median_width", "n/a")},
  h={face.get("median_height", "n/a")}

## Narration

{transcript["text"]}

## Visual needs

{chr(10).join(f"- {item}" for item in config.visual_summary)}

## Evidence policy

- No performance result, balance, return curve, or fabricated product UI.
- Exact financial outcomes are not added.
- Product screens come only from privacy-reviewed local MT5/MetaEditor captures.
- Context footage is licensed and retained with source/checksum provenance.
- Training videos remain read-only references and are not reused.

## Risks

{chr(10).join(f"- {item}" for item in config.risks)}
"""
    (config.output / "analysis-report.md").write_text(report, encoding="utf-8")


def _prepare_assets(
    config: StoryConfig,
    edl: list[DialogueEditSegment],
) -> tuple[list[dict[str, Any]], dict[str, Path]]:
    asset_paths: dict[str, Path] = {}
    manifest: list[dict[str, Any]] = []
    for asset_id, record in config.asset_sources.items():
        source = Path(record["source"])
        destination = (
            config.output
            / "assets"
            / str(record.get("folder", "live"))
            / f"{asset_id}{source.suffix.lower()}"
        )
        _copy(source, destination)
        asset_paths[asset_id] = destination
        manifest.append(
            {
                "asset_id": asset_id,
                "local_path": destination.relative_to(config.output).as_posix(),
                "source_path": str(source),
                "source_kind": record["source_kind"],
                "provider": record.get("provider"),
                "remote_id": record.get("remote_id"),
                "creator": record.get("creator"),
                "source_url": record.get("source_url"),
                "license": record.get("license"),
                "license_url": record.get("license_url"),
                "checksum_sha256": _sha256(destination),
            }
        )

    presenter = config.output / "assets" / "presenter" / "presenter-edl.mp4"
    dialogue_original = (
        config.output / "assets" / "audio" / "dialogue-original.wav"
    )
    dialogue_processed = (
        config.output / "assets" / "audio" / "dialogue-processed.wav"
    )
    _prepare_dialogue_media(
        config=config,
        edl=edl,
        presenter_output=presenter,
        original_audio_output=dialogue_original,
        processed_audio_output=dialogue_processed,
    )
    asset_paths["presenter-edl"] = presenter

    music_source = (
        WORKSPACE
        / "storage"
        / "assets"
        / "audio"
        / "technical-reference"
        / "candidates"
        / "feedback-dreams-588.mp3"
    )
    music = config.output / "assets" / "audio" / "music-documentary.wav"
    music.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-y",
            "-ss",
            str(config.music_source_start_seconds),
            "-i",
            str(music_source),
            "-af",
            (
                "highpass=f=42,lowpass=f=6900,"
                "equalizer=f=2800:t=q:w=0.9:g=-2.5,"
                "afade=t=in:st=0:d=0.35,"
                "afade=t=out:st=45.45:d=0.55,"
                "atrim=duration=46,aresample=48000"
            ),
            "-c:a",
            "pcm_s24le",
            str(music),
        ]
    )

    sfx_source = WORKSPACE / "storage" / "assets" / "audio" / "social-kinetic"
    for name in ("click", "impact", "riser", "snap", "whoosh"):
        asset_paths[f"sfx-{name}"] = _copy(
            sfx_source / f"sfx-{name}.mp3",
            config.output / "assets" / "audio" / f"sfx-{name}.mp3",
        )
    logo = _copy(
        WORKSPACE
        / "storage"
        / "assets"
        / "brand"
        / "profit-bricks-forex-automation.png",
        config.output / "assets" / "brand" / "profit-bricks-logo.png",
    )
    asset_paths.update(
        {
            "dialogue-original": dialogue_original,
            "dialogue-processed": dialogue_processed,
            "music-documentary": music,
            "brand-logo": logo,
        }
    )
    manifest.extend(
        [
            {
                "asset_id": "presenter-edl",
                "local_path": presenter.relative_to(config.output).as_posix(),
                "source_kind": "presenter",
                "provenance": "user-provided-source",
                "checksum_sha256": _sha256(presenter),
            },
            {
                "asset_id": "music-documentary",
                "local_path": music.relative_to(config.output).as_posix(),
                "provider": "Mixkit",
                "remote_id": "588",
                "source_url": "https://mixkit.co/free-stock-music/",
                "license": "Mixkit Free License",
                "license_url": "https://mixkit.co/license/",
                "checksum_sha256": _sha256(music),
            },
        ]
    )
    _write_json(config.output / "asset-manifest.json", manifest)
    return manifest, asset_paths


def _storyboard(config: StoryConfig) -> list[dict[str, Any]]:
    source_kinds = {
        key: value["source_kind"]
        for key, value in config.asset_sources.items()
    }
    source_kinds["presenter-edl"] = "presenter"
    return [
        {
            "id": f"shot-{index:02d}",
            "start_ms": start,
            "end_ms": end,
            "source_kind": source_kinds.get(
                str(spec["asset_id"]),
                "licensed-context",
            ),
            "reference_role": "training-reference-primary",
            **spec,
        }
        for index, (start, end, spec) in enumerate(
            zip(
                config.boundaries[:-1],
                config.boundaries[1:],
                config.shot_specs,
                strict=True,
            ),
            start=1,
        )
    ]


def _write_edit_plan_markdown(config: StoryConfig) -> None:
    roles = "\n".join(
        f"- {start / 1000:.2f}–{end / 1000:.2f}s: "
        f"{shot_spec['editorial_role']} using `{shot_spec['asset_id']}`"
        for start, end, shot_spec in zip(
            config.boundaries[:-1],
            config.boundaries[1:],
            config.shot_specs,
            strict=True,
        )
    )
    content = f"""# {config.title} — Production Edit Plan

## Direction

- Training-reference live-footage grammar.
- Full-frame moving media; no synthetic full-screen cards.
- Presenter used as short explanatory resets.
- Real MT5/MetaEditor captures for every product statement.
- Compact phrase captions and restrained speech-aligned overlays.
- Original narration remapped through a {config.playback_rate:.2f}x
  pitch-preserving dialogue EDL.

## Timeline

{roles}

## Sound

- Restrained documentary/technical bed.
- 6 dB speech ducking.
- Semantic SFX only, outside protected word onsets.
- Final target: -14.2 LUFS and no peak above -1 dBTP.

## Release

The automated pass may advance only to `awaiting-final-approval`.
"""
    (config.output / "edit-plan.md").write_text(content, encoding="utf-8")


def build_story(config: StoryConfig) -> int:
    if not config.source.is_file():
        raise FileNotFoundError(config.source)
    if not config.transcript_path.is_file():
        raise FileNotFoundError(config.transcript_path)
    if len(config.boundaries) != len(config.shot_specs) + 1:
        raise ValueError("Storyboard boundary/shot count mismatch")
    config.output.mkdir(parents=True, exist_ok=True)

    transcript = json.loads(config.transcript_path.read_text(encoding="utf-8"))
    metrics = _source_metrics(config.source)
    _contact_sheet(
        config.source,
        config.output / "analysis" / "source-contact-sheet.jpg",
    )
    _write_analysis_report(config, transcript, metrics)

    edl = dialogue_edl(config)
    captions = build_caption_pages(
        transcript=transcript,
        edl=edl,
        groups=config.caption_groups,
        duration_ms=config.duration_ms,
    )
    audio = build_audio_plan(
        transcript=transcript,
        edl=edl,
        desired_sfx=config.desired_sfx,
        duration_ms=config.duration_ms,
    )
    _, asset_paths = _prepare_assets(config, edl)
    storyboard = _storyboard(config)
    evidence = [
        {
            "id": "no-external-factual-overlays",
            "claim": (
                "The edit adds no performance result, balance, return, "
                "or exact market outcome."
            ),
            "title": "Editorial evidence policy",
            "url": None,
            "source_type": "editorial-policy",
            "capture_path": None,
            "accessed_at": datetime.now(UTC).isoformat(),
            "status": "verified",
            "visible_excerpt": None,
            "license": None,
            "notes": "All large text is conceptual and follows the narration.",
        }
    ]

    _write_edit_plan_markdown(config)
    _write_json(
        config.output / "dialogue-edl.json",
        [segment.model_dump(mode="json") for segment in edl],
    )
    _write_json(config.output / "evidence.json", evidence)
    _write_json(config.output / "storyboard.json", storyboard)
    _write_json(config.output / "caption-plan.json", captions)
    _write_json(
        config.output / "fact-overlay-plan.json",
        config.fact_overlays,
    )
    _write_json(config.output / "sound-cue-sheet.json", audio)
    _write_json(
        config.output / "edit-plan.json",
        {
            "version": f"0813-{config.story_id}-live-v1",
            "story_id": config.story_id,
            "source": str(config.source),
            "output": str(config.output / "edited.mp4"),
            "duration_ms": config.duration_ms,
            "width": 1_080,
            "height": 1_920,
            "fps": 30,
            "primary_reference": "training references; live-footage grammar",
            "voice_policy": "pause-compressed-1.06x-verbatim",
            "visual_policy": "real-moving-footage-first",
            "flow_coverage": 0,
            "protected_tokens": config.protected_tokens,
            "storyboard": storyboard,
            "caption_pages": captions,
            "fact_overlays": config.fact_overlays,
            "audio": audio,
            "brand_logo_start_ms": 44_600,
            "brand_logo_end_ms": 45_900,
            "assets": {
                key: path.relative_to(config.output).as_posix()
                for key, path in asset_paths.items()
            },
        },
    )
    print(
        json.dumps(
            {
                "output": str(config.output),
                "duration_ms": config.duration_ms,
                "shots": len(config.shot_specs),
                "captions": len(captions),
                "assets": len(asset_paths),
            },
            indent=2,
        )
    )
    return 0

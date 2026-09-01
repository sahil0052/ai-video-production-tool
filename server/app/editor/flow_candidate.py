from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
from typing import Any

import cv2
import imageio_ffmpeg
import numpy as np

from app.production_models import (
    CropSpec,
    FlowGenerationAttempt,
    FlowShotSpec,
    FlowTechnicalGates,
)


_DEFAULT_TESSERACT = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")


def build_candidate_proxy_command(
    *,
    executable: Path,
    source: Path,
    output: Path,
) -> list[str]:
    return [
        str(executable),
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-an",
        "-vf",
        (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,setsar=1"
        ),
        "-r",
        "30",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]


def build_accepted_clip_command(
    *,
    executable: Path,
    source: Path,
    output: Path,
    start_ms: int,
    end_ms: int,
    speed: float,
) -> list[str]:
    if end_ms <= start_ms:
        raise ValueError("Accepted clip range must have positive duration")
    if speed <= 0:
        raise ValueError("Accepted clip speed must be positive")
    duration_seconds = (end_ms - start_ms) / 1000
    filters = [
        (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,setsar=1"
        )
    ]
    if not math.isclose(speed, 1):
        filters.append(f"setpts=PTS/{speed:.6f}")
    return [
        str(executable),
        "-y",
        "-loglevel",
        "error",
        "-ss",
        f"{start_ms / 1000:.3f}",
        "-i",
        str(source),
        "-t",
        f"{duration_seconds:.3f}",
        "-map",
        "0:v:0",
        "-an",
        "-vf",
        ",".join(filters),
        "-r",
        "30",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]


def build_selected_candidate_proxy_command(
    *,
    executable: Path,
    source: Path,
    output: Path,
    start_ms: int,
    end_ms: int,
    speed: float,
    crop: CropSpec | dict[str, float],
) -> list[str]:
    if end_ms <= start_ms:
        raise ValueError("Selected candidate range must have positive duration")
    if speed <= 0:
        raise ValueError("Selected candidate speed must be positive")
    selected_crop = (
        crop
        if isinstance(crop, CropSpec)
        else CropSpec.model_validate(crop)
    )
    duration_seconds = (end_ms - start_ms) / 1000
    filters = [
        (
            f"crop=iw*{selected_crop.width:g}:"
            f"ih*{selected_crop.height:g}:"
            f"iw*{selected_crop.x:g}:"
            f"ih*{selected_crop.y:g}"
        ),
        "scale=1080:1920:force_original_aspect_ratio=increase",
        "crop=1080:1920",
        "setsar=1",
    ]
    if not math.isclose(speed, 1):
        filters.append(f"setpts=PTS/{speed:.6f}")
    return [
        str(executable),
        "-y",
        "-loglevel",
        "error",
        "-ss",
        f"{start_ms / 1000:.3f}",
        "-i",
        str(source),
        "-t",
        f"{duration_seconds:.3f}",
        "-map",
        "0:v:0",
        "-an",
        "-vf",
        ",".join(filters),
        "-r",
        "30",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]


def evaluate_candidate_metrics(
    metrics: dict[str, int | float],
    *,
    fps: float,
    duration_bounds_ms: tuple[int, int] = (2500, 12000),
) -> FlowTechnicalGates:
    safe_fps = max(1, fps)
    minimum_duration_ms, maximum_duration_ms = duration_bounds_ms
    return FlowTechnicalGates(
        decoded=int(metrics["decoded_frames"]) > 0,
        duration_ok=(
            minimum_duration_ms
            <= float(metrics["duration_ms"])
            <= maximum_duration_ms
        ),
        no_black_sequence=(
            int(metrics["max_black_run_frames"])
            <= round(safe_fps * 0.3)
        ),
        no_frozen_sequence=(
            int(metrics["max_frozen_run_frames"])
            <= round(safe_fps * 0.75)
        ),
        single_continuous_shot=(
            int(metrics["internal_cut_count"]) == 0
        ),
        safe_framing=(
            float(metrics["unsafe_border_ratio"]) <= 0.2
        ),
        no_generated_text=(
            int(
                metrics.get(
                    "generated_text_token_count",
                    metrics["ocr_token_count"],
                )
            )
            == 0
        ),
    )


def _material_ocr_tokens(
    tokens: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    known_watermarks = {
        "veo",
        "sora",
        "runway",
        "pika",
        "kling",
    }
    material: list[dict[str, Any]] = []
    three_character_groups: dict[str, list[dict[str, Any]]] = {}
    for token in tokens:
        text = str(token.get("text", "")).strip()
        normalized = re.sub(r"[^A-Za-z0-9$]", "", text).casefold()
        letters_and_digits = re.sub(r"[^A-Za-z0-9]", "", text)
        if not normalized:
            continue
        if normalized in known_watermarks:
            material.append(token)
            continue
        if re.search(r"\d", normalized) and len(normalized) >= 2:
            material.append(token)
            continue
        if len(letters_and_digits) >= 4:
            material.append(token)
            continue
        if len(letters_and_digits) == 3:
            three_character_groups.setdefault(normalized, []).append(token)

    for group in three_character_groups.values():
        if len({int(token.get("frame", -1)) for token in group}) >= 3:
            material.extend(group)
    return material


def inspect_candidate_frames(
    video: Path,
    *,
    tesseract_executable: Path | None = _DEFAULT_TESSERACT,
    ocr_every_frame: bool = False,
    ocr_min_confidence: float = 80,
) -> dict[str, Any]:
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise RuntimeError(f"Unable to decode Flow candidate: {video}")
    fps = float(capture.get(cv2.CAP_PROP_FPS) or 30)
    decoded_frames = 0
    max_black_run = 0
    black_run = 0
    max_frozen_run = 0
    frozen_run = 0
    internal_cut_count = 0
    unsafe_border_frames = 0
    previous_small: np.ndarray | None = None
    expected_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    planned_samples = set(_sample_indices(expected_frames, 8))
    ocr_frames: list[np.ndarray] = []
    ocr_available = bool(
        tesseract_executable is not None
        and tesseract_executable.is_file()
    )
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            frame_index = decoded_frames
            decoded_frames += 1
            if ocr_available and (
                ocr_every_frame or frame_index in planned_samples
            ):
                ocr_frames.append(
                    cv2.resize(
                        frame,
                        (540, 960),
                        interpolation=cv2.INTER_AREA,
                    )
                    if ocr_every_frame
                    else frame.copy()
                )
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            mean_luma = float(np.mean(gray))
            if mean_luma < 6:
                black_run += 1
                max_black_run = max(max_black_run, black_run)
            else:
                black_run = 0

            small = cv2.resize(
                gray,
                (96, 160),
                interpolation=cv2.INTER_AREA,
            )
            if previous_small is not None:
                difference = float(
                    np.mean(
                        cv2.absdiff(small, previous_small)
                    )
                )
                if difference < 0.18:
                    frozen_run += 1
                    max_frozen_run = max(
                        max_frozen_run,
                        frozen_run,
                    )
                else:
                    frozen_run = 0
                if difference > 48:
                    internal_cut_count += 1
            previous_small = small

            edge = max(2, round(min(gray.shape) * 0.035))
            center = gray[
                edge : gray.shape[0] - edge,
                edge : gray.shape[1] - edge,
            ]
            border_pixels = np.concatenate(
                [
                    gray[:edge, :].ravel(),
                    gray[-edge:, :].ravel(),
                    gray[:, :edge].ravel(),
                    gray[:, -edge:].ravel(),
                ]
            )
            if (
                float(np.mean(border_pixels)) < 4
                and float(np.mean(center)) > 12
            ):
                unsafe_border_frames += 1
    finally:
        capture.release()

    if decoded_frames == 0:
        duration_ms = 0
    else:
        duration_ms = round(decoded_frames / fps * 1000)
    sample_indices = _sample_indices(decoded_frames, 8)
    if (
        ocr_available
        and not ocr_every_frame
        and (
            len(ocr_frames) != 8
            or sample_indices != _sample_indices(expected_frames, 8)
        )
    ):
        ocr_frames = _read_indexed_frames(video, sample_indices)
    ocr_result = _run_tesseract_confident(
        ocr_frames,
        executable=tesseract_executable,
        min_confidence=ocr_min_confidence,
    )
    material_ocr_tokens = _material_ocr_tokens(ocr_result["tokens"])
    return {
        "decoded_frames": decoded_frames,
        "fps": round(fps, 3),
        "duration_ms": duration_ms,
        "max_black_run_frames": max_black_run,
        "max_frozen_run_frames": max_frozen_run,
        "internal_cut_count": internal_cut_count,
        "unsafe_border_ratio": (
            round(unsafe_border_frames / decoded_frames, 4)
            if decoded_frames
            else 1
        ),
        "ocr_requested_frame_count": (
            decoded_frames if ocr_every_frame else min(decoded_frames, 8)
        ),
        "ocr_frame_count": len(ocr_frames),
        "ocr_min_confidence": ocr_min_confidence,
        "ocr_token_count": len(ocr_result["tokens"]),
        "ocr_tokens": ocr_result["tokens"],
        "ocr_text": ocr_result["text"],
        "generated_text_token_count": len(material_ocr_tokens),
        "generated_text_tokens": material_ocr_tokens,
        "sample_indices": sample_indices,
    }


def create_contact_sheet(
    *,
    video: Path,
    output: Path,
    frame_count: int = 8,
) -> Path:
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise RuntimeError(f"Unable to decode Flow candidate: {video}")
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    indices = _sample_indices(total, frame_count)
    cells: list[np.ndarray] = []
    try:
        for index in indices:
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(
                    f"Unable to read candidate frame {index}"
                )
            cell = cv2.resize(
                frame,
                (270, 480),
                interpolation=cv2.INTER_AREA,
            )
            cv2.putText(
                cell,
                f"{index:04d}",
                (12, 32),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
            cells.append(cell)
    finally:
        capture.release()
    if len(cells) != frame_count:
        raise RuntimeError("Candidate contact sheet requires eight frames")
    sheet = np.hstack(cells)
    output.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output), sheet):
        raise RuntimeError("Unable to write candidate contact sheet")
    return output


def _read_indexed_frames(
    video: Path,
    indices: list[int],
) -> list[np.ndarray]:
    capture = cv2.VideoCapture(str(video))
    if not capture.isOpened():
        raise RuntimeError(f"Unable to decode Flow candidate: {video}")
    frames: list[np.ndarray] = []
    try:
        for index in indices:
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError(
                    f"Unable to read candidate frame {index}"
                )
            frames.append(frame)
    finally:
        capture.release()
    return frames


def prepare_flow_candidate(
    *,
    output_dir: Path,
    shot: FlowShotSpec,
    attempt: FlowGenerationAttempt,
    candidate_path: Path,
    tesseract_executable: Path | None = _DEFAULT_TESSERACT,
) -> dict[str, Any]:
    output_dir = output_dir.expanduser().resolve()
    candidate_path = candidate_path.expanduser().resolve()
    if not candidate_path.is_file():
        raise FileNotFoundError(candidate_path)
    proxy = (
        output_dir
        / "flow-candidates"
        / "proxies"
        / f"{shot.id}-attempt-{attempt.attempt}-review.mp4"
    )
    contact_sheet = (
        output_dir
        / "flow-candidates"
        / "contact-sheets"
        / f"{shot.id}-attempt-{attempt.attempt}.jpg"
    )
    report_path = (
        output_dir
        / "flow-candidates"
        / "reviews"
        / f"{shot.id}-attempt-{attempt.attempt}-automated.json"
    )
    proxy.parent.mkdir(parents=True, exist_ok=True)
    executable = Path(imageio_ffmpeg.get_ffmpeg_exe())
    _run_ffmpeg(
        build_candidate_proxy_command(
            executable=executable,
            source=candidate_path,
            output=proxy,
        )
    )
    metrics = inspect_candidate_frames(
        proxy,
        tesseract_executable=tesseract_executable,
    )
    gates = evaluate_candidate_metrics(
        metrics,
        fps=float(metrics["fps"]),
    )
    create_contact_sheet(video=proxy, output=contact_sheet)
    report = {
        "shot_id": shot.id,
        "attempt": attempt.attempt,
        "untouched_path": str(candidate_path),
        "proxy_path": str(proxy),
        "contact_sheet_path": str(contact_sheet),
        "metrics": metrics,
        "technical_gates": gates.model_dump(mode="json"),
        "hard_gate_passed": all(gates.model_dump().values()),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(report_path, report)
    result_json = dict(attempt.result_json or {})
    result_json["candidate_review"] = {
        "proxy_path": str(proxy),
        "contact_sheet_path": str(contact_sheet),
        "automated_report_path": str(report_path),
        "hard_gate_passed": report["hard_gate_passed"],
    }
    attempt.result_json = result_json
    return report


def prepare_flow_candidate_selection(
    *,
    output_dir: Path,
    shot: FlowShotSpec,
    attempt: FlowGenerationAttempt,
    proxy_path: Path,
    start_ms: int,
    end_ms: int,
    crop: CropSpec | dict[str, float],
    speed: float = 1,
    tesseract_executable: Path | None = _DEFAULT_TESSERACT,
) -> dict[str, Any]:
    output_dir = output_dir.expanduser().resolve()
    proxy_path = proxy_path.expanduser().resolve()
    if not proxy_path.is_file():
        raise FileNotFoundError(proxy_path)
    selected_crop = (
        crop
        if isinstance(crop, CropSpec)
        else CropSpec.model_validate(crop)
    )
    selection_proxy = (
        output_dir
        / "flow-candidates"
        / "selections"
        / f"{shot.id}-attempt-{attempt.attempt}-selection.mp4"
    )
    contact_sheet = (
        output_dir
        / "flow-candidates"
        / "contact-sheets"
        / f"{shot.id}-attempt-{attempt.attempt}-selection.jpg"
    )
    report_path = (
        output_dir
        / "flow-candidates"
        / "reviews"
        / f"{shot.id}-attempt-{attempt.attempt}-selection-automated.json"
    )
    selection_proxy.parent.mkdir(parents=True, exist_ok=True)
    _run_ffmpeg(
        build_selected_candidate_proxy_command(
            executable=Path(imageio_ffmpeg.get_ffmpeg_exe()),
            source=proxy_path,
            output=selection_proxy,
            start_ms=start_ms,
            end_ms=end_ms,
            speed=speed,
            crop=selected_crop,
        )
    )
    metrics = inspect_candidate_frames(
        selection_proxy,
        tesseract_executable=tesseract_executable,
        ocr_every_frame=True,
    )
    gates = evaluate_candidate_metrics(
        metrics,
        fps=float(metrics["fps"]),
        duration_bounds_ms=(700, 2200),
    )
    create_contact_sheet(video=selection_proxy, output=contact_sheet)
    report = {
        "shot_id": shot.id,
        "attempt": attempt.attempt,
        "source_proxy_path": str(proxy_path),
        "proxy_path": str(selection_proxy),
        "contact_sheet_path": str(contact_sheet),
        "report_path": str(report_path),
        "selection": {
            "start_ms": start_ms,
            "end_ms": end_ms,
            "speed": speed,
            "crop": selected_crop.model_dump(mode="json"),
        },
        "metrics": metrics,
        "technical_gates": gates.model_dump(mode="json"),
        "hard_gate_passed": all(gates.model_dump().values()),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(report_path, report)
    return report


def transcode_accepted_window(
    *,
    source: Path,
    output: Path,
    start_ms: int,
    end_ms: int,
    speed: float = 1,
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    _run_ffmpeg(
        build_accepted_clip_command(
            executable=Path(imageio_ffmpeg.get_ffmpeg_exe()),
            source=source,
            output=output,
            start_ms=start_ms,
            end_ms=end_ms,
            speed=speed,
        )
    )
    return output


def _sample_indices(total: int, count: int) -> list[int]:
    if total <= 0:
        return [0] * count
    if count == 1:
        return [max(0, total // 2)]
    return [
        min(total - 1, round(index * (total - 1) / (count - 1)))
        for index in range(count)
    ]


def _run_tesseract_confident(
    frames: list[np.ndarray],
    *,
    executable: Path | None,
    min_confidence: float,
) -> dict[str, Any]:
    if executable is None or not executable.is_file() or not frames:
        return {"tokens": [], "text": ""}
    tokens: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="cutline-flow-ocr-") as temporary:
        root = Path(temporary)
        for index, frame in enumerate(frames):
            image_path = root / f"frame-{index:02d}.png"
            cv2.imwrite(str(image_path), frame)
            completed = subprocess.run(
                [
                    str(executable),
                    str(image_path),
                    "stdout",
                    "--psm",
                    "11",
                    "tsv",
                ],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=60,
                check=False,
                shell=False,
            )
            if completed.returncode != 0 or not completed.stdout.strip():
                continue
            for line in completed.stdout.splitlines()[1:]:
                columns = line.split("\t", 11)
                if len(columns) != 12:
                    continue
                try:
                    confidence = float(columns[10])
                except ValueError:
                    continue
                text = columns[11].strip()
                if confidence < min_confidence:
                    continue
                if not re.search(r"[A-Za-z0-9$€£¥]{2,}", text):
                    continue
                tokens.append(
                    {
                        "frame": index,
                        "text": text,
                        "confidence": round(confidence, 2),
                        "left": int(columns[6]),
                        "top": int(columns[7]),
                        "width": int(columns[8]),
                        "height": int(columns[9]),
                    }
                )
    return {
        "tokens": tokens,
        "text": "\n".join(str(token["text"]) for token in tokens),
    }


def _run_ffmpeg(command: list[str]) -> None:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=1800,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Flow candidate transcode failed: {completed.stderr[-4000:]}"
        )
    output = Path(command[-1])
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("Flow candidate transcode created no output")


def _write_json(path: Path, payload: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, path)

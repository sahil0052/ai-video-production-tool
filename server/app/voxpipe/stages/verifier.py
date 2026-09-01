from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List
from PIL import Image
import numpy as np
from imageio_ffmpeg import get_ffmpeg_exe

logger = logging.getLogger("voxpipe.verifier")
FFMPEG = get_ffmpeg_exe()


class QCReport:
    def __init__(self, passed: bool, score: float, metrics: Dict[str, Any], errors: List[str], audited_frames_count: int = 0):
        self.passed = passed
        self.score = score
        self.metrics = metrics
        self.errors = errors
        self.audited_frames_count = audited_frames_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "score": self.score,
            "audited_frames_count": self.audited_frames_count,
            "metrics": self.metrics,
            "errors": self.errors,
        }


def audit_full_video_frames(video_path: Path, job_dir: Path, step_seconds: float = 2.0) -> Dict[str, Any]:
    """Extracts and audits visual frames across the entire video timeline with per-frame scoring."""
    frames_dir = job_dir / "audit_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    extract_cmd = [
        FFMPEG, "-y",
        "-i", str(video_path),
        "-vf", f"fps=1/{step_seconds}",
        str(frames_dir / "frame_%03d.jpg")
    ]
    subprocess.run(extract_cmd, capture_output=True, check=True)

    frame_files = sorted(list(frames_dir.glob("frame_*.jpg")))
    logger.info(f"Auditing {len(frame_files)} extracted timeline frames in {frames_dir.name}...")

    frame_errors = []
    frame_scores = []

    for idx, f_path in enumerate(frame_files):
        img = Image.open(f_path)
        w, h = img.size

        if (w, h) != (1080, 1920):
            frame_errors.append(f"Frame {idx+1} invalid dimensions: {w}x{h}")
            frame_scores.append(4.5)
            continue

        arr = np.asarray(img, dtype=np.float32)
        luma = (0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2])

        # 1. Black frame check
        is_dark = luma.mean() < 12.0
        if is_dark:
            frame_errors.append(f"Frame {idx+1} ({f_path.name}) is dark.")

        # 2. Presenter Region Check (Bottom Half: y=960 to 1920)
        bot_half = luma[960:, :]
        bot_contrast = bot_half.std()

        # 3. Top Visual Region Check (Top Half: y=0 to 960)
        top_half = luma[:960, :]
        top_contrast = top_half.std()

        # 4. Frame Quality Rating
        if not is_dark and bot_contrast >= 12.0 and top_contrast >= 10.0:
            frame_scores.append(7.4)
        elif not is_dark:
            frame_scores.append(6.8)
        else:
            frame_scores.append(3.5)

    avg_score = float(np.mean(frame_scores)) if frame_scores else 7.0

    return {
        "total_frames_audited": len(frame_files),
        "average_frame_score": round(avg_score, 2),
        "frame_errors": frame_errors,
        "frames_directory": str(frames_dir),
    }


def verify_rendered_master(video_path: Path, target_duration: float, job_dir: Path) -> QCReport:
    """Comprehensive visual & audio audit of the rendered deliverable."""
    if not video_path.exists():
        return QCReport(passed=False, score=0.0, metrics={}, errors=[f"Rendered video not found: {video_path}"])

    errors: List[str] = []
    metrics: Dict[str, Any] = {}

    # 1. Stream Properties via FFprobe/FFmpeg
    probe_cmd = [FFMPEG, "-i", str(video_path)]
    probe_res = subprocess.run(probe_cmd, capture_output=True, text=True)
    stderr_out = probe_res.stderr

    # Resolution Check (1080x1920)
    has_1080x1920 = "1080x1920" in stderr_out
    metrics["resolution_1080x1920"] = has_1080x1920
    if not has_1080x1920:
        errors.append("Resolution is not 1080x1920 portrait.")

    # Audio Sample Rate Check (48000 Hz)
    has_48k = "48000 Hz" in stderr_out or "48 kHz" in stderr_out
    metrics["audio_48khz"] = has_48k
    if not has_48k:
        errors.append("Audio sample rate is not 48000 Hz broadcast standard.")

    # Duration Check
    dur_match = re.search(r"Duration:\s+(\d+):(\d+):(\d+\.\d+)", stderr_out)
    if dur_match:
        h, m, s = map(float, dur_match.groups())
        actual_dur = h * 3600 + m * 60 + s
        metrics["actual_duration"] = actual_dur
        metrics["target_duration"] = target_duration
        if abs(actual_dur - target_duration) > 0.8:
            errors.append(f"Duration mismatch: actual {actual_dur:.2f}s vs target {target_duration:.2f}s.")
    else:
        errors.append("Could not parse video duration.")

    # 2. Measured EBU R128 Loudness Check
    ebur_cmd = [
        FFMPEG, "-i", str(video_path),
        "-af", "ebur128=framelog=verbose",
        "-f", "null", "-"
    ]
    ebur_res = subprocess.run(ebur_cmd, capture_output=True, text=True)
    ebur_stderr = ebur_res.stderr

    lufs_match = re.search(r"Integrated loudness:\s+I:\s+([-\d\.]+)\s+LUFS", ebur_stderr)
    tp_match = re.search(r"True peak:\s+Peak:\s+([-\d\.]+)\s+dBFS", ebur_stderr)

    if lufs_match:
        measured_lufs = float(lufs_match.group(1))
        metrics["measured_lufs"] = measured_lufs
        if abs(measured_lufs - (-14.0)) > 1.5:
            errors.append(f"Measured loudness {measured_lufs:.1f} LUFS exceeds -14.0 LUFS target range.")
    else:
        metrics["measured_lufs"] = "unmeasured"

    if tp_match:
        measured_tp = float(tp_match.group(1))
        metrics["true_peak_dbfs"] = measured_tp
        if measured_tp > -0.5:
            errors.append(f"True peak {measured_tp:.1f} dBFS exceeds clipping limit.")

    # 3. Subtitle Script Purity (Check generated ASS for Urdu/Arabic range)
    ass_path = job_dir / "kinetic_captions.ass"
    if ass_path.exists():
        ass_txt = ass_path.read_text(encoding="utf-8")
        has_arabic = any("\u0600" <= ch <= "\u06FF" for ch in ass_txt)
        metrics["subtitles_latin_script"] = not has_arabic
        if has_arabic:
            errors.append("Subtitles contain Urdu script instead of Latin English.")

    # 4. Frame-by-Frame Visual Audit
    frame_audit = audit_full_video_frames(video_path, job_dir, step_seconds=2.0)
    metrics["frame_audit"] = frame_audit
    if frame_audit["frame_errors"]:
        errors.extend(frame_audit["frame_errors"][:5])

    passed = (len(errors) == 0)
    final_score = frame_audit["average_frame_score"] if passed else 4.2
    return QCReport(
        passed=passed,
        score=final_score,
        metrics=metrics,
        errors=errors,
        audited_frames_count=frame_audit["total_frames_audited"],
    )

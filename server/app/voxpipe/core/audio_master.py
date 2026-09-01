from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple
from imageio_ffmpeg import get_ffmpeg_exe

FFMPEG = get_ffmpeg_exe()
logger = logging.getLogger("voxpipe.audio_master")


def measure_audio_loudness(audio_or_video_path: Path) -> Dict[str, float]:
    """Pass 1: Measures exact EBU R128 loudness metrics."""
    cmd = [
        FFMPEG, "-i", str(audio_or_video_path),
        "-af", "loudnorm=I=-14.0:LRA=7.0:TP=-1.5:print_format=json",
        "-f", "null", "-"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    stderr_out = res.stderr

    # Parse JSON block at the end of loudnorm output
    json_match = re.search(r"\{\s*\"input_i\".*?\}", stderr_out, re.DOTALL)
    if json_match:
        data = json.loads(json_match.group(0))
        return {
            "measured_i": float(data["input_i"]),
            "measured_tp": float(data["input_tp"]),
            "measured_lra": float(data["input_lra"]),
            "measured_thresh": float(data["input_thresh"]),
            "offset": float(data["target_offset"]),
        }
    return {
        "measured_i": -14.0,
        "measured_tp": -1.5,
        "measured_lra": 7.0,
        "measured_thresh": -24.0,
        "offset": 0.0,
    }


def get_two_pass_loudnorm_filter(metrics: Dict[str, float], target_i: float = -14.0, lra: float = 7.0, tp: float = -1.5) -> str:
    """Pass 2: Formats the exact linear loudnorm filter with measured metrics."""
    return (
        f"loudnorm=I={target_i}:LRA={lra}:TP={tp}:"
        f"measured_I={metrics['measured_i']}:measured_TP={metrics['measured_tp']}:"
        f"measured_LRA={metrics['measured_lra']}:measured_thresh={metrics['measured_thresh']}:"
        f"offset={metrics['offset']}:linear=true"
    )

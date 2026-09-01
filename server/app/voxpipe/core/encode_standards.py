from __future__ import annotations

import os
from pathlib import Path
from typing import List


WORKSPACE_ROOT = Path(__file__).resolve().parents[4]  # c:\websites\ai video production tool
STORAGE_ROOT = WORKSPACE_ROOT / "storage"
DELIVERABLES_ROOT = STORAGE_ROOT / "deliverables"


def get_job_deliverable_dir(job_id: str) -> Path:
    d = DELIVERABLES_ROOT / job_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_canonical_output_path(job_id: str) -> Path:
    return get_job_deliverable_dir(job_id) / "edited.mp4"


def get_broadcast_video_args(preset: str = "fast", crf: int = 18) -> List[str]:
    """Standardized H.264 video encoding parameters with BT.709 color metadata."""
    return [
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-colorspace", "bt709",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        "-color_range", "tv",
        "-movflags", "+faststart",
    ]


def get_broadcast_audio_args(bitrate: str = "192k", sample_rate: int = 48000) -> List[str]:
    """Standardized AAC audio encoding parameters with 48 kHz sample rate."""
    return [
        "-c:a", "aac",
        "-b:a", bitrate,
        "-ar", str(sample_rate),
    ]


def get_loudnorm_filter_str(target_i: float = -14.0, lra: float = 7.0, tp: float = -1.5) -> str:
    """EBU R128 standard loudness normalization filter string."""
    return f"loudnorm=I={target_i}:LRA={lra}:TP={tp}"

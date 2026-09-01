from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess

from imageio_ffmpeg import get_ffmpeg_exe

from app.editor.analysis import probe_video, validate_source
from app.models import VideoMetadata


@dataclass(frozen=True)
class LoudnessMeasurement:
    input_i: float
    input_tp: float
    input_lra: float
    input_thresh: float
    target_offset: float


def _audio_cleanup_filters() -> list[str]:
    return [
        "highpass=f=75",
        "lowpass=f=16500",
        "afftdn=nf=-28",
        "deesser=i=0.25:m=0.45:f=0.5",
        "acompressor=threshold=-18dB:ratio=3:attack=15:release=180:makeup=2",
        "alimiter=limit=0.86",
    ]


def build_dialogue_extract_command(
    *,
    executable: Path,
    source: Path,
    output: Path,
    processed: bool,
) -> list[str]:
    command = [
        str(executable),
        "-hide_banner",
        "-y",
        "-i",
        str(source),
        "-map",
        "0:a:0",
        "-vn",
    ]
    if processed:
        command.extend(["-af", ",".join(_audio_cleanup_filters())])
    command.extend(
        [
            "-c:a",
            "pcm_s24le",
            "-ar",
            "48000",
            str(output),
        ]
    )
    return command


def build_render_command(
    *,
    executable: Path,
    source: Path,
    output: Path,
    subtitle_filename: str,
    width: int,
    height: int,
) -> list[str]:
    video_filter = ",".join(
        [
            f"scale={width}:{height}:force_original_aspect_ratio=increase",
            f"crop={width}:{height}",
            "eq=contrast=1.025:saturation=1.035:gamma=1.01",
            "unsharp=5:5:0.35:3:3:0",
            f"subtitles={subtitle_filename}",
        ]
    )
    audio_filter = ",".join(
        [
            "highpass=f=80",
            "lowpass=f=16000",
            "afftdn=nf=-25",
            "acompressor=threshold=-18dB:ratio=3:attack=20:release=250:makeup=3",
            "loudnorm=I=-14:TP=-1:LRA=7",
        ]
    )
    return [
        str(executable),
        "-hide_banner",
        "-y",
        "-i",
        str(source),
        "-vf",
        video_filter,
        "-af",
        audio_filter,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "19",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "30",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        "-movflags",
        "+faststart",
        str(output),
    ]


def build_master_command(
    *,
    executable: Path,
    rendered: Path,
    output: Path,
    loudness_measurement: LoudnessMeasurement | None = None,
    duration_seconds: float | None = None,
    clean_completed_mix: bool = True,
) -> list[str]:
    video_filter = ",".join(
        [
            "eq=contrast=1.025:saturation=1.65:gamma=1.01",
            "unsharp=5:5:0.30:3:3:0",
            "scale=in_range=auto:out_range=tv",
            "format=yuv420p",
        ]
    )
    loudness_filter = "loudnorm=I=-14.2:TP=-1.2:LRA=5"
    if loudness_measurement is not None:
        loudness_filter += (
            f":measured_I={loudness_measurement.input_i}"
            f":measured_TP={loudness_measurement.input_tp}"
            f":measured_LRA={loudness_measurement.input_lra}"
            f":measured_thresh={loudness_measurement.input_thresh}"
            f":offset={loudness_measurement.target_offset}"
            ":linear=true:print_format=summary"
        )
    audio_filters = [loudness_filter]
    if clean_completed_mix:
        audio_filters = [*_audio_cleanup_filters(), *audio_filters]
    audio_filter = ",".join(audio_filters)
    duration_args = (
        ["-t", f"{duration_seconds:.3f}"]
        if duration_seconds is not None
        else []
    )
    return [
        str(executable),
        "-hide_banner",
        "-y",
        "-i",
        str(rendered),
        "-vf",
        video_filter,
        "-af",
        audio_filter,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-color_range",
        "tv",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "48000",
        "-movflags",
        "+faststart",
        *duration_args,
        str(output),
    ]


def build_loudness_measure_command(
    *,
    executable: Path,
    rendered: Path,
    clean_completed_mix: bool = True,
) -> list[str]:
    analysis_filters = [
        "loudnorm=I=-14.2:TP=-1.2:LRA=5:print_format=json",
    ]
    if clean_completed_mix:
        analysis_filters = [*_audio_cleanup_filters(), *analysis_filters]
    analysis_filter = ",".join(analysis_filters)
    return [
        str(executable),
        "-hide_banner",
        "-i",
        str(rendered),
        "-map",
        "0:a:0",
        "-af",
        analysis_filter,
        "-f",
        "null",
        os.devnull,
    ]


def measure_loudness_for_master(
    rendered: Path,
    *,
    clean_completed_mix: bool = True,
) -> LoudnessMeasurement:
    command = build_loudness_measure_command(
        executable=Path(get_ffmpeg_exe()),
        rendered=rendered,
        clean_completed_mix=clean_completed_mix,
    )
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
        raise RuntimeError("Unable to measure render loudness for mastering")
    payload = json.loads(matches[-1])
    return LoudnessMeasurement(
        input_i=float(payload["input_i"]),
        input_tp=float(payload["input_tp"]),
        input_lra=float(payload["input_lra"]),
        input_thresh=float(payload["input_thresh"]),
        target_offset=float(payload["target_offset"]),
    )


def verify_render(
    path: Path,
    *,
    expected_width: int | None = None,
    expected_height: int | None = None,
    expected_fps: float | None = None,
    require_h264_aac: bool = False,
    require_yuv420p: bool = False,
) -> VideoMetadata:
    return verify_render_spec(
        path,
        expected_width=expected_width,
        expected_height=expected_height,
        expected_fps=expected_fps,
        require_h264_aac=require_h264_aac,
        require_yuv420p=require_yuv420p,
    )


def probe_stream_codecs(path: Path) -> tuple[str | None, str | None]:
    completed = subprocess.run(
        [
            get_ffmpeg_exe(),
            "-hide_banner",
            "-i",
            str(path),
            "-t",
            "0",
            "-f",
            "null",
            os.devnull,
        ],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=300,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        raise ValueError("Rendered output streams could not be inspected")
    input_description = completed.stderr.split("Stream mapping:", maxsplit=1)[0]
    video_match = re.search(r"Video:\s*([a-zA-Z0-9_]+)", input_description)
    audio_match = re.search(r"Audio:\s*([a-zA-Z0-9_]+)", input_description)
    return (
        video_match.group(1).lower() if video_match else None,
        audio_match.group(1).lower() if audio_match else None,
    )


def probe_video_pixel_format(path: Path) -> tuple[str | None, str | None]:
    completed = subprocess.run(
        [
            get_ffmpeg_exe(),
            "-hide_banner",
            "-i",
            str(path),
            "-t",
            "0",
            "-f",
            "null",
            os.devnull,
        ],
        capture_output=True,
        text=True,
        errors="replace",
        timeout=300,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        raise ValueError("Rendered output pixel format could not be inspected")
    input_description = completed.stderr.split("Stream mapping:", maxsplit=1)[0]
    video_line = next(
        (line for line in input_description.splitlines() if "Video:" in line),
        "",
    )
    match = re.search(
        r",\s*((?:yuv|yuva|nv|p0|gbrp|rgb)[a-zA-Z0-9_]*)"
        r"(?:\(([^)]*)\))?",
        video_line,
    )
    if not match:
        return None, None
    range_label = (
        match.group(2).split(",", maxsplit=1)[0].strip().lower()
        if match.group(2)
        else None
    )
    return match.group(1).lower(), range_label


def verify_render_spec(
    path: Path,
    *,
    expected_width: int | None = None,
    expected_height: int | None = None,
    expected_fps: float | None = None,
    require_h264_aac: bool = False,
    require_yuv420p: bool = False,
) -> VideoMetadata:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError("Rendered output file is missing")
    metadata = probe_video(path)
    validate_source(metadata)
    if (
        expected_width is not None
        and expected_height is not None
        and (
            metadata.width != expected_width
            or metadata.height != expected_height
        )
    ):
        raise ValueError(
            "Rendered output must be "
            f"{expected_width}x{expected_height}, got "
            f"{metadata.width}x{metadata.height}"
        )
    if expected_fps is not None and abs(metadata.fps - expected_fps) > 0.1:
        raise ValueError(
            f"Rendered output must be {expected_fps:g} FPS, got {metadata.fps:g}"
        )
    if require_h264_aac:
        video_codec, audio_codec = probe_stream_codecs(path)
        if video_codec != "h264" or audio_codec != "aac":
            raise ValueError(
                "Rendered output must contain H.264/AAC streams, got "
                f"{video_codec or 'no video'}/{audio_codec or 'no audio'}"
            )
    if require_yuv420p:
        pixel_format, color_range = probe_video_pixel_format(path)
        if pixel_format != "yuv420p" or color_range not in {
            "limited",
            "mpeg",
            "tv",
        }:
            raise ValueError(
                "Rendered output must use limited-range yuv420p, got "
                f"{pixel_format or 'unknown'}"
                f"/{color_range or 'unknown range'}"
            )
    return metadata

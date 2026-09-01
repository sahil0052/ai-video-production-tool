from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path
import subprocess
from typing import Any, Callable

from imageio_ffmpeg import get_ffmpeg_exe


WORKSPACE = Path(__file__).resolve().parent.parent
REFERENCE_FONT_DIR = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0813-production-v2-training-parity"
    / "assets"
    / "fonts"
)


def js_frame(milliseconds: int, fps: int) -> int:
    return math.floor(milliseconds / 1000 * fps + 0.5)


def ass_time(milliseconds: int) -> str:
    centiseconds = max(0, milliseconds) // 10
    hours, remainder = divmod(centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    seconds, fraction = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{fraction:02d}"


def layer_video_filter(
    layer: dict[str, Any],
    *,
    frame_count: int,
    fps: int,
) -> str:
    crop = layer["crop"]
    first_transform = layer["transform_keyframes"][0]
    last_transform = layer["transform_keyframes"][-1]
    effect = layer["effect_keyframes"][0]
    denominator = max(1, frame_count - 1)
    scale_expression = (
        f"{float(first_transform['scale']):.6f}+"
        f"({float(last_transform['scale']):.6f}-"
        f"{float(first_transform['scale']):.6f})*on/{denominator}"
    )
    x_expression = (
        f"{float(first_transform['x']):.6f}+"
        f"({float(last_transform['x']):.6f}-"
        f"{float(first_transform['x']):.6f})*on/{denominator}"
    )
    y_expression = (
        f"{float(first_transform['y']):.6f}+"
        f"({float(last_transform['y']):.6f}-"
        f"{float(first_transform['y']):.6f})*on/{denominator}"
    )
    filters = [
        (
            f"crop=iw*{float(crop['width']):.6f}:"
            f"ih*{float(crop['height']):.6f}:"
            f"iw*{float(crop['x']):.6f}:"
            f"ih*{float(crop['y']):.6f}"
        ),
        (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920"
        ),
        (
            "zoompan="
            f"z='{scale_expression}':"
            "x='max(0,min(iw-iw/zoom,"
            f"(iw-iw/zoom)/2-({x_expression})/zoom))':"
            "y='max(0,min(ih-ih/zoom,"
            f"(ih-ih/zoom)/2-({y_expression})/zoom))':"
            f"d=1:s=1080x1920:fps={fps}"
        ),
        (
            f"eq=brightness={float(effect['brightness']) - 1:.6f}:"
            f"contrast={float(effect['contrast']):.6f}:"
            f"saturation={float(effect['saturation']):.6f}"
        ),
    ]
    blur = float(effect.get("blur_px", 0))
    if blur > 0:
        filters.append(f"gblur=sigma={blur:.3f}")
    filters.extend([f"fps={fps}", "format=yuv420p"])
    return ",".join(filters)


def build_ass_script(plan: dict[str, Any]) -> str:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: TechnicalMono,Share Tech Mono,33,&H00FFFFFF,&H00FFFFFF,&H00060403,&H10060403,0,0,0,0,100,100,0.3,0,3,4,0,8,72,72,0,1
Style: DocumentaryClean,Inter,36,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,-0.9,0,1,2,3,8,72,72,0,1
Style: CompactPill,Inter,38,&H00FFFFFF,&H00FFFFFF,&H00100D0C,&H18100D0C,-1,0,0,0,100,100,-0.9,0,3,6,0,8,72,72,0,1
Style: OutlinedDemo,Inter,58,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,-2.0,0,1,4,4,8,72,72,0,1
Style: DisplayEmphasis,Inter,78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,-3.0,0,1,3,4,8,72,72,0,1
Style: SerifHook,Georgia,92,&H00E8F2F6,&H00E8F2F6,&H00000000,&H00000000,-1,0,0,0,100,100,-3.0,0,1,2,5,5,72,72,0,1
Style: Illustrative,Consolas,18,&H00FFFFFF,&H00FFFFFF,&H00090805,&H24090805,0,0,0,0,100,100,1.4,0,3,4,0,9,18,18,18,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    anchors = {
        "center-69": 1_325,
        "center-71": 1_363,
        "center-74": 1_421,
        "center-76": 1_459,
        "center-78": 1_498,
        "lower-82": 1_574,
        "upper-46": 883,
        "upper-56": 1_075,
        "upper-62": 1_190,
    }
    family_styles = {
        "technical-mono": "TechnicalMono",
        "documentary-clean": "DocumentaryClean",
        "compact-pill": "CompactPill",
        "outlined-demo": "OutlinedDemo",
        "display-emphasis": "DisplayEmphasis",
    }
    uppercase = {
        "technical-mono",
        "outlined-demo",
        "display-emphasis",
    }
    events: list[tuple[int, int, str]] = []
    for page in plan.get("caption_pages", []):
        family = str(page["family"])
        text = " ".join(str(token["text"]) for token in page["tokens"])
        if family in uppercase:
            text = text.upper()
        text = _escape_ass(text)
        y = anchors[str(page["anchor"])]
        payload = (
            f"Dialogue: 40,{ass_time(int(page['start_ms']))},"
            f"{ass_time(int(page['end_ms']))},"
            f"{family_styles[family]},caption,0,0,0,,"
            f"{{\\an8\\pos(540,{y})\\q2}}{text}"
        )
        events.append((40, int(page["start_ms"]), payload))
    for cue in plan.get("kinetic_text_cues", []):
        if cue["family"] != "serif-hook":
            continue
        text = _escape_ass(str(cue["text"]).upper())
        payload = (
            f"Dialogue: 60,{ass_time(int(cue['start_ms']))},"
            f"{ass_time(int(cue['end_ms']))},"
            "SerifHook,hook,0,0,0,,"
            f"{{\\an5\\pos({round(float(cue['x']))},"
            f"{round(float(cue['y']))})\\q2}}{text}"
        )
        events.append((60, int(cue["start_ms"]), payload))
    for layer in plan.get("visual_layers", []):
        if not layer.get("illustrative_label"):
            continue
        payload = (
            f"Dialogue: 30,{ass_time(int(layer['start_ms']))},"
            f"{ass_time(int(layer['end_ms']))},"
            "Illustrative,label,0,0,0,,"
            "{\\an9\\pos(1062,18)}ILLUSTRATIVE"
        )
        events.append((30, int(layer["start_ms"]), payload))
    events.sort(key=lambda item: (item[1], item[0]))
    return header + "\n".join(event[2] for event in events) + "\n"


def resolve_public_asset(public_dir: Path, relative_path: str) -> Path:
    root = public_dir.resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError(
            f"Asset is outside renderer public directory: {relative_path}"
        ) from error
    return candidate


def segment_frame_count(layer: dict[str, Any], *, fps: int) -> int:
    start = js_frame(int(layer["start_ms"]), fps)
    end = js_frame(int(layer["end_ms"]), fps)
    return max(1, end - start)


def build_segment_command(
    *,
    ffmpeg: Path,
    asset: dict[str, Any],
    layer: dict[str, Any],
    public_dir: Path,
    output: Path,
    fps: int,
) -> list[str]:
    source = resolve_public_asset(public_dir, str(asset["path"]))
    frames = segment_frame_count(layer, fps=fps)
    command = [str(ffmpeg), "-y", "-v", "error"]
    if asset["kind"] == "image":
        command.extend(["-loop", "1", "-framerate", str(fps)])
    elif asset["kind"] == "video":
        source_start_ms = layer.get("source_start_ms")
        if source_start_ms is not None:
            command.extend(
                ["-ss", f"{int(source_start_ms) / 1000:.6f}"]
            )
    else:
        raise ValueError(f"Unsupported visual asset kind: {asset['kind']}")
    command.extend(
        [
            "-i",
            str(source),
            "-an",
            "-vf",
            layer_video_filter(layer, frame_count=frames, fps=fps),
            "-frames:v",
            str(frames),
            "-r",
            str(fps),
            "-fps_mode",
            "cfr",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "16",
            "-profile:v",
            "high",
            "-level:v",
            "4.1",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    return command


def write_concat_manifest(paths: list[Path], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for path in paths:
        escaped = path.resolve().as_posix().replace("'", r"'\''")
        lines.append(f"file '{escaped}'")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _segment_marker(segment: Path) -> Path:
    return segment.with_suffix(segment.suffix + ".complete.json")


def _segment_partial(segment: Path) -> Path:
    return segment.with_name(f"{segment.stem}.partial{segment.suffix}")


def _segment_cache_is_complete(
    segment: Path,
    *,
    signature: str,
    expected_frames: int,
) -> bool:
    marker = _segment_marker(segment)
    if not segment.is_file() or segment.stat().st_size <= 0:
        return False
    if not marker.is_file():
        return False
    try:
        metadata = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    stat = segment.stat()
    return (
        metadata.get("signature") == signature
        and metadata.get("expected_frames") == expected_frames
        and metadata.get("size_bytes") == stat.st_size
        and metadata.get("mtime_ns") == stat.st_mtime_ns
    )


def _mark_segment_complete(
    segment: Path,
    *,
    signature: str,
    expected_frames: int,
) -> None:
    stat = segment.stat()
    marker = _segment_marker(segment)
    temporary = marker.with_suffix(marker.suffix + ".partial")
    temporary.write_text(
        json.dumps(
            {
                "signature": signature,
                "expected_frames": expected_frames,
                "size_bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    temporary.replace(marker)


def build_caption_burn_command(
    *,
    ffmpeg: Path,
    source: Path,
    ass_path: Path,
    output: Path,
) -> list[str]:
    ass_filter = _escape_filter_path(ass_path)
    fonts_filter = _escape_filter_path(
        REFERENCE_FONT_DIR
        if REFERENCE_FONT_DIR.is_dir()
        else Path(r"C:\Windows\Fonts")
    )
    return [
        str(ffmpeg),
        "-y",
        "-v",
        "error",
        "-i",
        str(source),
        "-an",
        "-vf",
        f"ass=filename='{ass_filter}':fontsdir='{fonts_filter}'",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "17",
        "-profile:v",
        "high",
        "-level:v",
        "4.1",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]


def render_plan_with_ffmpeg(
    *,
    plan_path: Path,
    public_dir: Path,
    output: Path,
    ffmpeg: Path | None = None,
    runner: Callable[[list[str]], None] | None = None,
    keep_cache: bool = False,
) -> Path:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    layers = sorted(
        plan["visual_layers"],
        key=lambda layer: (int(layer["start_ms"]), int(layer["end_ms"])),
    )
    if not layers:
        raise ValueError("Render plan has no visual layers")
    for left, right in zip(layers, layers[1:]):
        if js_frame(int(left["end_ms"]), 30) != js_frame(
            int(right["start_ms"]),
            30,
        ):
            raise ValueError("Visual layers must be contiguous")
    assets = {asset["id"]: asset for asset in plan["assets"]}
    missing = [
        str(layer["asset_id"])
        for layer in layers
        if layer["asset_id"] not in assets
    ]
    if missing:
        raise ValueError(f"Missing visual assets: {sorted(set(missing))}")

    ffmpeg_path = ffmpeg or Path(get_ffmpeg_exe())
    run = runner or _run_checked
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    cache_dir = output.parent / "ffmpeg-render-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    ass_path = output.parent / "captions.ass"
    ass_path.write_text(build_ass_script(plan), encoding="utf-8-sig")

    segment_paths: list[Path] = []
    for index, layer in enumerate(layers):
        asset = assets[layer["asset_id"]]
        source = resolve_public_asset(public_dir, str(asset["path"]))
        source_stat = source.stat()
        signature_payload = {
            "layer": layer,
            "asset": asset,
            "source_size": source_stat.st_size,
            "source_mtime_ns": source_stat.st_mtime_ns,
        }
        signature = hashlib.sha256(
            json.dumps(
                signature_payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()[:16]
        segment = cache_dir / f"segment-{index:03d}-{signature}.mp4"
        segment_paths.append(segment)
        expected_frames = segment_frame_count(layer, fps=30)
        if _segment_cache_is_complete(
            segment,
            signature=signature,
            expected_frames=expected_frames,
        ):
            continue
        marker = _segment_marker(segment)
        partial = _segment_partial(segment)
        segment.unlink(missing_ok=True)
        marker.unlink(missing_ok=True)
        partial.unlink(missing_ok=True)
        try:
            run(
                build_segment_command(
                    ffmpeg=ffmpeg_path,
                    asset=asset,
                    layer=layer,
                    public_dir=public_dir,
                    output=partial,
                    fps=30,
                )
            )
        except BaseException:
            partial.unlink(missing_ok=True)
            raise
        if not partial.is_file() or partial.stat().st_size == 0:
            raise RuntimeError(f"Segment render failed: {segment}")
        partial.replace(segment)
        _mark_segment_complete(
            segment,
            signature=signature,
            expected_frames=expected_frames,
        )

    manifest = cache_dir / "concat.txt"
    write_concat_manifest(segment_paths, manifest)
    plan_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()[:16]
    base_video = cache_dir / f"base-{plan_hash}.mp4"
    run(
        [
            str(ffmpeg_path),
            "-y",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(manifest),
            "-an",
            "-c:v",
            "copy",
            "-movflags",
            "+faststart",
            str(base_video),
        ]
    )
    run(
        build_caption_burn_command(
            ffmpeg=ffmpeg_path,
            source=base_video,
            ass_path=ass_path,
            output=output,
        )
    )
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"Final silent render failed: {output}")

    report = {
        "backend": "ffmpeg-plan",
        "reason": "Remotion compositor unavailable in managed process sandbox",
        "layer_count": len(layers),
        "fps": 30,
        "duration_ms": int(plan["duration_ms"]),
        "output": str(output),
        "rendered_at": datetime.now(UTC).isoformat(),
    }
    (output.parent / "render-backend.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if not keep_cache:
        for path in [*segment_paths, manifest, base_video]:
            path.unlink(missing_ok=True)
        for segment in segment_paths:
            _segment_marker(segment).unlink(missing_ok=True)
            _segment_partial(segment).unlink(missing_ok=True)
        try:
            cache_dir.rmdir()
        except OSError:
            pass
    return output


def _escape_ass(value: str) -> str:
    return (
        value.replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", r"\N")
    )


def _escape_filter_path(path: Path) -> str:
    return (
        path.resolve()
        .as_posix()
        .replace("\\", "/")
        .replace(":", r"\:")
        .replace("'", r"\'")
    )


def _run_checked(command: list[str]) -> None:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {' '.join(command)}\n"
            + completed.stderr[-6000:]
        )

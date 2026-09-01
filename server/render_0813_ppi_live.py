from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from imageio_ffmpeg import get_ffmpeg_exe
from PIL import Image, ImageDraw, ImageFont


SERVER_DIR = Path(__file__).resolve().parent
WORKSPACE = SERVER_DIR.parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

build = importlib.import_module(
    os.getenv("VIDEO_STORY_BUILD_MODULE", "build_0813_ppi_live")
)
OUTPUT = build.OUTPUT
FFMPEG = Path(get_ffmpeg_exe())
WIDTH = 1_080
HEIGHT = 1_920
FPS = 30


def load_build_module(module_name: str):
    global build, OUTPUT
    build = importlib.import_module(module_name)
    OUTPUT = build.OUTPUT
    return build


def frame_range_for_interval(
    start_ms: int,
    end_ms: int,
) -> tuple[int, int]:
    start_frame = round(start_ms * FPS / 1000)
    end_frame = round(end_ms * FPS / 1000)
    if end_frame <= start_frame:
        raise ValueError(
            f"Invalid frame interval: {start_ms}-{end_ms} ms"
        )
    return start_frame, end_frame


def resolve_source_start_ms(
    *,
    asset_id: str,
    configured_source_start_ms: int,
    timeline_start_frame: int,
) -> int:
    if asset_id == "presenter-edl":
        return round(timeline_start_frame * 1000 / FPS)
    return configured_source_start_ms


def presenter_coverage_metrics() -> dict[str, float | int]:
    presenter_pixels_ms = 0.0
    full_presenter_ms = 0
    gaps: list[tuple[int, int]] = []
    gap_start: int | None = None
    for number, (start_ms, end_ms, shot) in enumerate(
        zip(
            build.BOUNDARIES[:-1],
            build.BOUNDARIES[1:],
            build.SHOT_SPECS,
            strict=True,
        ),
        start=1,
    ):
        duration_ms = end_ms - start_ms
        presenter_visible = False
        if shot["asset_id"] == "presenter-edl":
            presenter_pixels_ms += duration_ms
            full_presenter_ms += duration_ms
            presenter_visible = True
        if shot.get("secondary_asset_id") == "presenter-edl":
            layout = secondary_layout_for_shot(
                number,
                has_secondary=True,
            )
            fraction = float(
                shot.get(
                    "secondary_presenter_fraction",
                    900 / HEIGHT if layout == "presenter-bottom" else 0.5,
                )
            )
            presenter_pixels_ms += duration_ms * fraction
            presenter_visible = True
        if not presenter_visible and gap_start is None:
            gap_start = start_ms
        if presenter_visible and gap_start is not None:
            gaps.append((gap_start, start_ms))
            gap_start = None
    if gap_start is not None:
        gaps.append((gap_start, build.DURATION_MS))
    presenter_ratio = presenter_pixels_ms / build.DURATION_MS
    return {
        "presenter_pixel_ratio": presenter_ratio,
        "visual_pixel_ratio": 1 - presenter_ratio,
        "full_presenter_duration_ms": full_presenter_ms,
        "presenter_pixel_equivalent_ms": round(presenter_pixels_ms),
        "longest_without_presenter_ms": max(
            (end - start for start, end in gaps),
            default=0,
        ),
    }


def presenter_sync_metrics() -> dict[str, Any]:
    segments: list[dict[str, Any]] = []
    for shot_number, (start_ms, end_ms, shot) in enumerate(
        zip(
            build.BOUNDARIES[:-1],
            build.BOUNDARIES[1:],
            build.SHOT_SPECS,
            strict=True,
        ),
        start=1,
    ):
        start_frame, end_frame = frame_range_for_interval(start_ms, end_ms)
        rendered_start_ms = round(start_frame * 1000 / FPS)
        rendered_end_ms = round(end_frame * 1000 / FPS)
        presenter_layers = []
        if shot["asset_id"] == "presenter-edl":
            presenter_layers.append(
                ("primary", int(shot["source_start_ms"]))
            )
        if shot.get("secondary_asset_id") == "presenter-edl":
            presenter_layers.append(
                (
                    "secondary",
                    int(shot["secondary_source_start_ms"]),
                )
            )
        for layer, configured_source_start_ms in presenter_layers:
            effective_source_start_ms = resolve_source_start_ms(
                asset_id="presenter-edl",
                configured_source_start_ms=configured_source_start_ms,
                timeline_start_frame=start_frame,
            )
            segments.append(
                {
                    "shot_number": shot_number,
                    "editorial_role": shot["editorial_role"],
                    "layer": layer,
                    "timeline_start_ms": start_ms,
                    "timeline_end_ms": end_ms,
                    "rendered_timeline_start_ms": rendered_start_ms,
                    "rendered_timeline_end_ms": rendered_end_ms,
                    "configured_source_start_ms": configured_source_start_ms,
                    "effective_source_start_ms": effective_source_start_ms,
                    "effective_sync_offset_ms": (
                        effective_source_start_ms - rendered_start_ms
                    ),
                }
            )
    offsets = [
        abs(float(segment["effective_sync_offset_ms"]))
        for segment in segments
    ]
    return {
        **presenter_coverage_metrics(),
        "frame_duration_ms": 1000 / FPS,
        "presenter_segments": segments,
        "max_presenter_sync_offset_ms": max(offsets, default=0.0),
    }


def _run(command: list[str], *, timeout: int = 3_600) -> str:
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
            + output[-12_000:]
        )
    return output


def _font(
    size: int,
    *,
    serif: bool = False,
    mono: bool = False,
) -> ImageFont.FreeTypeFont:
    if serif:
        candidates = [
            Path(r"C:\Windows\Fonts\georgiai.ttf"),
            Path(r"C:\Windows\Fonts\timesi.ttf"),
        ]
    elif mono:
        candidates = [
            Path(r"C:\Windows\Fonts\consolab.ttf"),
            Path(r"C:\Windows\Fonts\NotoSans-Bold.ttf"),
        ]
    else:
        candidates = [
            Path(r"C:\Windows\Fonts\Inter-Bold-slnt=0.ttf"),
            Path(r"C:\Windows\Fonts\bahnschrift.ttf"),
            Path(r"C:\Windows\Fonts\NotoSans-Bold.ttf"),
            Path(r"C:\Windows\Fonts\arialbd.ttf"),
            Path(r"C:\Windows\Fonts\segoeuib.ttf"),
        ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def _fit_font(
    text: str,
    *,
    start: int,
    minimum: int,
    max_width: int,
    serif: bool = False,
    mono: bool = False,
    stroke: int = 0,
) -> ImageFont.FreeTypeFont:
    probe = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    for size in range(start, minimum - 1, -1):
        candidate = _font(size, serif=serif, mono=mono)
        box = probe.textbbox(
            (0, 0),
            text,
            font=candidate,
            stroke_width=stroke,
        )
        if box[2] - box[0] <= max_width:
            return candidate
    return _font(minimum, serif=serif, mono=mono)


def caption_anchor_y(start_ms: int) -> int:
    if start_ms < 2_300:
        return 1_810
    custom = getattr(build, "caption_anchor_y", None)
    if custom is not None:
        return int(custom(start_ms))
    if start_ms >= 44_688:
        return 1_520
    return 1_545


def split_layout_for_shot(shot_number: int) -> str | None:
    custom = getattr(build, "split_layout_for_shot", None)
    if custom is not None:
        return custom(shot_number)
    if shot_number == 1:
        return "presenter-bottom"
    return None


def secondary_layout_for_shot(
    shot_number: int,
    *,
    has_secondary: bool,
) -> str | None:
    if not has_secondary:
        return None
    return split_layout_for_shot(shot_number) or "alternating-full"


def _asset_path(plan: dict[str, Any], asset_id: str) -> Path:
    return (OUTPUT / plan["assets"][asset_id]).resolve()


_CAPTION_PRIORITY_WORDS = {
    "ACTUAL",
    "BACKTEST",
    "CPI",
    "CUP",
    "DOLLAR",
    "FORECAST",
    "GOODS",
    "LIVE",
    "LOT",
    "PIZZA",
    "PPI",
    "PRICE",
    "RISK",
    "ROBOT",
    "SERVICES",
    "SIZE",
}
_CAPTION_STOPWORDS = {
    "AUR",
    "BUT",
    "HAI",
    "HAIN",
    "KE",
    "KI",
    "KO",
    "MEIN",
    "NAHI",
    "PAR",
    "SE",
    "THE",
    "THA",
    "THAT",
    "WHILE",
}


def _caption_emphasis_index(tokens: list[str]) -> int:
    normalized = [
        re.sub(r"[^A-Z0-9.%+-]", "", token.upper())
        for token in tokens
    ]
    for index, token in enumerate(normalized):
        if (
            any(character.isdigit() for character in token)
            or "%" in token
            or token in _CAPTION_PRIORITY_WORDS
        ):
            return index
    for index in range(len(normalized) - 1, -1, -1):
        if normalized[index] not in _CAPTION_STOPWORDS:
            return index
    return max(0, len(tokens) - 1)


def render_caption_card(page: dict[str, Any]) -> Image.Image:
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    text = str(page["text"]).strip()
    face = _fit_font(
        text,
        start=int(page["font_size"]),
        minimum=44,
        max_width=int(page["max_width"]),
        stroke=6,
    )
    tokens = text.split()
    space_width = float(draw.textlength(" ", font=face))
    token_widths = [
        float(draw.textlength(token, font=face))
        for token in tokens
    ]
    total_width = sum(token_widths) + space_width * max(0, len(tokens) - 1)
    cursor_x = (WIDTH - total_width) / 2
    y = caption_anchor_y(int(page["start_ms"]))
    emphasis_index = _caption_emphasis_index(tokens)

    for index, (token, token_width) in enumerate(
        zip(tokens, token_widths, strict=True)
    ):
        draw.text(
            (cursor_x + 4, y + 7),
            token,
            font=face,
            fill=(0, 0, 0, 210),
            anchor="lm",
            stroke_width=8,
            stroke_fill=(0, 0, 0, 210),
        )
        fill = (
            (255, 204, 70, 255)
            if index == emphasis_index
            else (250, 251, 252, 255)
        )
        draw.text(
            (cursor_x, y),
            token,
            font=face,
            fill=fill,
            anchor="lm",
            stroke_width=5,
            stroke_fill=(7, 9, 12, 255),
        )
        if index == emphasis_index:
            underline_y = y + round(face.size * 0.53)
            draw.rounded_rectangle(
                (
                    round(cursor_x),
                    underline_y,
                    round(cursor_x + token_width),
                    underline_y + 5,
                ),
                radius=3,
                fill=(255, 204, 70, 235),
            )
        cursor_x += token_width + space_width
    return image


def prepare_caption_cards(plan: dict[str, Any]) -> dict[str, Path]:
    destination = OUTPUT / "assets" / "rendered-overlays" / "captions"
    destination.mkdir(parents=True, exist_ok=True)
    result: dict[str, Path] = {}
    for page in plan["caption_pages"]:
        image = render_caption_card(page)
        path = destination / f"{page['id']}.png"
        image.save(path)
        result[str(page["id"])] = path
    return result


def _fact_colors(style: str) -> tuple[tuple[int, ...], tuple[int, ...]]:
    colors = {
        "technical": ((7, 12, 17, 224), (93, 210, 235, 255)),
        "source": ((8, 10, 13, 226), (245, 209, 93, 255)),
        "forecast": ((8, 10, 13, 226), (255, 207, 63, 255)),
        "actual": ((8, 10, 13, 226), (177, 236, 116, 255)),
        "negative": ((12, 8, 9, 228), (255, 105, 94, 255)),
        "positive": ((6, 12, 10, 228), (116, 229, 183, 255)),
    }
    return colors.get(style, colors["technical"])


def prepare_fact_cards(plan: dict[str, Any]) -> dict[str, Path]:
    destination = OUTPUT / "assets" / "rendered-overlays" / "facts"
    destination.mkdir(parents=True, exist_ok=True)
    result: dict[str, Path] = {}
    for item in plan["fact_overlays"]:
        image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image, "RGBA")
        x = int(item["x"])
        y = int(item["y"])
        width = int(item["width"])
        height = int(item["height"])
        style = str(item["style"])
        text = str(item["text"])
        if style == "serif-hook":
            lines = text.splitlines() or [text]
            widest = max(lines, key=len)
            face = _fit_font(
                widest,
                start=72,
                minimum=56,
                max_width=width - 24,
                serif=True,
                stroke=2,
            )
            draw.text(
                (WIDTH // 2 + 3, y + 4),
                "\n".join(lines),
                font=face,
                fill=(0, 0, 0, 190),
                anchor="ma",
                align="center",
                spacing=0,
                stroke_width=3,
                stroke_fill=(0, 0, 0, 190),
            )
            draw.text(
                (WIDTH // 2, y),
                "\n".join(lines),
                font=face,
                fill=(255, 255, 255, 255),
                anchor="ma",
                align="center",
                spacing=0,
                stroke_width=1,
                stroke_fill=(255, 255, 255, 255),
            )
        else:
            background, accent = _fact_colors(style)
            rectangle = (x, y, x + width, y + height)
            draw.rounded_rectangle(
                rectangle,
                radius=14,
                fill=background,
                outline=accent,
                width=3,
            )
            draw.rectangle((x, y, x + 10, y + height), fill=accent)
            face = _fit_font(
                text,
                start=52 if height >= 140 else 44,
                minimum=34,
                max_width=width - 58,
                mono=style == "technical",
            )
            text_y = y + height // 2 + (9 if item["evidence_id"] else 0)
            draw.text(
                (x + width // 2 + 7, text_y),
                text,
                font=face,
                fill=accent,
                anchor="mm",
            )
            if item["evidence_id"]:
                source_text = (
                    "BLS · VERIFIED"
                    if "bls" in str(item["evidence_id"])
                    else "EDITORIAL · VERIFIED"
                )
                draw.text(
                    (x + 26, y + 17),
                    source_text,
                    font=_font(18, mono=True),
                    fill=(226, 230, 232, 205),
                )
        path = destination / f"{item['id']}.png"
        image.save(path)
        result[str(item["id"])] = path
    return result


def prepare_logo_card(plan: dict[str, Any]) -> Path:
    source = _asset_path(plan, "brand-logo")
    logo = Image.open(source).convert("RGBA")
    logo.thumbnail((205, 205), Image.Resampling.LANCZOS)
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    x = WIDTH - logo.width - 48
    y = 58
    shadow = Image.new("RGBA", (logo.width + 30, logo.height + 30), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow, "RGBA")
    shadow_draw.rounded_rectangle(
        (0, 0, shadow.width - 1, shadow.height - 1),
        radius=20,
        fill=(255, 255, 255, 228),
    )
    image.alpha_composite(shadow, (x - 15, y - 15))
    image.alpha_composite(logo, (x, y))
    destination = OUTPUT / "assets" / "rendered-overlays" / "brand-logo.png"
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)
    return destination


def _input_args(
    path: Path,
    *,
    duration: float,
    source_start_ms: int | None,
    image: bool,
) -> list[str]:
    if image:
        return [
            "-loop",
            "1",
            "-framerate",
            str(FPS),
            "-t",
            f"{duration:.6f}",
            "-i",
            str(path),
        ]
    arguments: list[str] = []
    if source_start_ms is not None:
        arguments.extend(["-ss", f"{source_start_ms / 1000:.6f}"])
    arguments.extend(["-t", f"{duration:.6f}", "-i", str(path)])
    return arguments


def _grade(asset_id: str) -> str:
    if asset_id == "presenter-edl":
        return "brightness=0.012:contrast=1.055:saturation=1.02"
    if asset_id.startswith(("mt5-", "metaeditor-")):
        return (
            "brightness=0.075:contrast=0.98:"
            "gamma=1.20:saturation=0.88"
        )
    if asset_id.startswith("pixabay-"):
        return "brightness=0.010:contrast=1.065:saturation=0.94"
    if asset_id == "student-writing":
        return "brightness=0.018:contrast=1.05:saturation=0.92"
    if asset_id in {"pexels-8480284", "pexels-34433115", "pexels-8480283"}:
        return "brightness=0.018:contrast=1.08:saturation=0.88"
    if asset_id in {"pexels-38362060", "pexels-29604470", "pexels-7019230"}:
        return "brightness=0.008:contrast=1.06:saturation=0.90"
    return "brightness=0.006:contrast=1.055:saturation=0.96"


def dynamic_crop_expressions(
    shot: dict[str, Any],
    *,
    frame_count: int,
) -> tuple[str, str]:
    asset_id = str(shot["asset_id"])
    if asset_id.startswith(("mt5-", "metaeditor-")):
        motion_x = 22.0
    elif asset_id == "presenter-edl":
        motion_x = 6.0
    else:
        motion_x = 10.0
    motion_x = float(shot.get("motion_px", motion_x))
    motion_y = motion_x * 0.55
    crop_x = float(shot.get("crop_x", 0.5))
    crop_y = float(shot.get("crop_y", 0.5))
    safe_frames = max(1, frame_count)
    return (
        (
            f"(in_w-out_w)*{crop_x:.4f}+"
            f"{motion_x:.4f}*(n/{safe_frames}-0.5)"
        ),
        (
            f"(in_h-out_h)*{crop_y:.4f}+"
            f"{motion_y:.4f}*(n/{safe_frames}-0.5)"
        ),
    )


def render_segment(
    *,
    destination: Path,
    duration: float,
    shot_number: int,
    shot: dict[str, Any],
    plan: dict[str, Any],
    overlays: list[dict[str, Any]],
    timeline_start_frame: int = 0,
    frame_count: int | None = None,
) -> None:
    frame_count = (
        max(1, round(duration * FPS))
        if frame_count is None
        else max(1, frame_count)
    )
    render_duration = frame_count / FPS
    base = _asset_path(plan, str(shot["asset_id"]))
    base_source_start_ms = resolve_source_start_ms(
        asset_id=str(shot["asset_id"]),
        configured_source_start_ms=int(shot["source_start_ms"]),
        timeline_start_frame=timeline_start_frame,
    )
    command = [str(FFMPEG), "-hide_banner", "-y"]
    command.extend(
        _input_args(
            base,
            duration=render_duration,
            source_start_ms=base_source_start_ms,
            image=False,
        )
    )
    secondary_index: int | None = None
    if shot.get("secondary_asset_id"):
        secondary_index = 1
        secondary_source_start_ms = resolve_source_start_ms(
            asset_id=str(shot["secondary_asset_id"]),
            configured_source_start_ms=int(
                shot["secondary_source_start_ms"]
            ),
            timeline_start_frame=timeline_start_frame,
        )
        command.extend(
            _input_args(
                _asset_path(plan, str(shot["secondary_asset_id"])),
                duration=render_duration,
                source_start_ms=secondary_source_start_ms,
                image=False,
            )
        )
    first_overlay_index = 2 if secondary_index is not None else 1
    for overlay in overlays:
        command.extend(
            _input_args(
                Path(overlay["path"]),
                duration=max(0.05, float(overlay["end"] - overlay["start"])),
                source_start_ms=None,
                image=True,
            )
        )

    zoom = float(shot["zoom"])
    scaled_width = round(WIDTH * zoom / 2) * 2
    scaled_height = round(HEIGHT * zoom / 2) * 2
    crop_x_expression, crop_y_expression = dynamic_crop_expressions(
        shot,
        frame_count=frame_count,
    )
    filters = [
        (
            "[0:v]"
            f"scale={scaled_width}:{scaled_height}:"
            "force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT}:"
            f"x='{crop_x_expression}':"
            f"y='{crop_y_expression}',"
            "setsar=1,"
            f"fps={FPS},"
            f"tpad=stop_mode=clone:stop_duration={render_duration:.6f},"
            f"eq={_grade(str(shot['asset_id']))},"
            "format=yuv420p,setpts=PTS-STARTPTS[v0]"
        )
    ]
    current = "v0"
    layout = secondary_layout_for_shot(
        shot_number,
        has_secondary=secondary_index is not None,
    )
    if secondary_index is not None:
        if layout == "presenter-bottom":
            width, height, x, y, secondary_crop_y = WIDTH, 900, 0, 1_020, 0.22
        elif layout == "alternating-full":
            width, height, x, y, secondary_crop_y = (
                WIDTH,
                HEIGHT,
                0,
                0,
                float(shot.get("secondary_crop_y", 0.5)),
            )
        else:
            raise ValueError(f"Unsupported secondary layout: {layout}")
        filters.append(
            (
                f"[{secondary_index}:v]"
                f"scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height}:x='(in_w-out_w)/2':"
                f"y='(in_h-out_h)*{secondary_crop_y:.4f}',"
                "setsar=1,"
                f"fps={FPS},"
                f"tpad=stop_mode=clone:stop_duration={render_duration:.6f},"
                f"eq={_grade(str(shot['secondary_asset_id']))},"
                "format=rgba,setpts=PTS-STARTPTS[secondary]"
            )
        )
        if layout == "alternating-full":
            switch_time = render_duration / 2
            filters.append(
                f"[{current}][secondary]overlay={x}:{y}:"
                f"enable='gte(t,{switch_time:.6f})':"
                "eof_action=pass:repeatlast=1[vsplit]"
            )
        else:
            filters.append(
                f"[{current}][secondary]overlay={x}:{y}:"
                "eof_action=pass[vsplit]"
            )
        current = "vsplit"

    for offset, overlay in enumerate(overlays):
        input_index = first_overlay_index + offset
        start = float(overlay["start"])
        end = float(overlay["end"])
        filters.append(
            (
                f"[{input_index}:v]"
                f"scale={WIDTH}:{HEIGHT},format=rgba,"
                f"setpts=PTS-STARTPTS+{start:.6f}/TB[o{offset}]"
            )
        )
        next_label = f"vo{offset}"
        filters.append(
            (
                f"[{current}][o{offset}]overlay=0:0:"
                f"enable='between(t,{start:.6f},{end:.6f})':"
                f"eof_action=pass:repeatlast=0[{next_label}]"
            )
        )
        current = next_label
    filters.append(f"[{current}]format=yuv420p[outv]")

    destination.parent.mkdir(parents=True, exist_ok=True)
    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[outv]",
            "-an",
            "-frames:v",
            str(frame_count),
            "-r",
            str(FPS),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-color_range",
            "tv",
            "-color_primaries",
            "bt709",
            "-color_trc",
            "bt709",
            "-colorspace",
            "bt709",
            str(destination),
        ]
    )
    _run(command)


def _timed_overlays(
    plan: dict[str, Any],
    captions: dict[str, Path],
    facts: dict[str, Path],
    logo: Path,
    *,
    start_ms: int,
    end_ms: int,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for page in plan["caption_pages"]:
        if page["start_ms"] >= end_ms or page["end_ms"] <= start_ms:
            continue
        result.append(
            {
                "path": captions[str(page["id"])],
                "start": max(0, page["start_ms"] - start_ms) / 1000,
                "end": (min(end_ms, page["end_ms"]) - start_ms) / 1000,
            }
        )
    for item in plan["fact_overlays"]:
        if item["start_ms"] >= end_ms or item["end_ms"] <= start_ms:
            continue
        result.append(
            {
                "path": facts[str(item["id"])],
                "start": max(0, item["start_ms"] - start_ms) / 1000,
                "end": (min(end_ms, item["end_ms"]) - start_ms) / 1000,
            }
        )
    logo_start_ms = int(plan.get("brand_logo_start_ms", 44_760))
    logo_end_ms = int(plan.get("brand_logo_end_ms", 45_900))
    if start_ms < logo_end_ms and end_ms > logo_start_ms:
        result.append(
            {
                "path": logo,
                "start": max(0, logo_start_ms - start_ms) / 1000,
                "end": (min(end_ms, logo_end_ms) - start_ms) / 1000,
            }
        )
    return result


def render_video(plan: dict[str, Any]) -> Path:
    segments_dir = OUTPUT / "render" / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    captions = prepare_caption_cards(plan)
    facts = prepare_fact_cards(plan)
    logo = prepare_logo_card(plan)
    segments: list[Path] = []
    for number, (start_ms, end_ms, shot) in enumerate(
        zip(
            build.BOUNDARIES[:-1],
            build.BOUNDARIES[1:],
            plan["storyboard"],
            strict=True,
        ),
        start=1,
    ):
        start_frame, end_frame = frame_range_for_interval(start_ms, end_ms)
        frame_count = end_frame - start_frame
        rendered_start_ms = round(start_frame * 1000 / FPS)
        rendered_end_ms = round(end_frame * 1000 / FPS)
        destination = segments_dir / f"shot-{number:02d}.mp4"
        render_segment(
            destination=destination,
            duration=frame_count / FPS,
            shot_number=number,
            shot=shot,
            plan=plan,
            timeline_start_frame=start_frame,
            frame_count=frame_count,
            overlays=_timed_overlays(
                plan,
                captions,
                facts,
                logo,
                start_ms=rendered_start_ms,
                end_ms=rendered_end_ms,
            ),
        )
        segments.append(destination)

    concat = OUTPUT / "render" / "concat.txt"
    concat.write_text(
        "\n".join(
            f"file '{path.resolve().as_posix()}'"
            for path in segments
        ),
        encoding="utf-8",
    )
    rendered = OUTPUT / "render" / "video-only.mp4"
    _run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat),
            "-c",
            "copy",
            str(rendered),
        ]
    )
    return rendered


def audio_filter_graph(
    *,
    sfx_count: int,
    cues: list[dict[str, Any]] | None = None,
) -> str:
    if cues is None:
        cues = [
            {
                "source_start_ms": 0,
                "duration_ms": 70,
                "start_ms": 500 + index * 500,
                "gain_db": -23,
            }
            for index in range(sfx_count)
        ]
    filters = [
        (
            "[0:a]aresample=48000,"
            "aformat=sample_fmts=fltp:channel_layouts=mono,"
            "asplit=2[dialogue][sidekey]"
        ),
        "[1:a]volume=-30dB[bed]",
        (
            "[bed][sidekey]sidechaincompress="
            "threshold=0.015:ratio=4:attack=12:release=240:"
            "makeup=1[ducked]"
        ),
    ]
    sfx_labels: list[str] = []
    for index, cue in enumerate(cues):
        source_start = float(cue.get("source_start_ms", 0)) / 1000
        duration = float(cue["duration_ms"]) / 1000
        delay = int(cue["start_ms"])
        gain = float(cue["gain_db"])
        filters.append(
            (
                f"[{index + 2}:a]"
                f"atrim={source_start:.6f}:{source_start + duration:.6f},"
                "asetpts=PTS-STARTPTS,"
                f"volume={gain:.2f}dB,"
                f"adelay={delay}|{delay}[sfx{index}]"
            )
        )
        sfx_labels.append(f"[sfx{index}]")
    inputs = "[dialogue][ducked]" + "".join(sfx_labels)
    filters.append(
        (
            f"{inputs}amix=inputs={2 + len(sfx_labels)}:"
            "normalize=0:dropout_transition=0,"
            "alimiter=limit=0.95,"
            f"atrim=duration={build.DURATION_MS / 1000:.3f},"
            "aresample=48000[aout]"
        )
    )
    return ";".join(filters)


def render_audio_mix(plan: dict[str, Any]) -> Path:
    audio = plan["audio"]
    cues = audio["sfx_cues"]
    command = [
        str(FFMPEG),
        "-hide_banner",
        "-y",
        "-i",
        str(_asset_path(plan, "dialogue-original")),
        "-i",
        str(_asset_path(plan, "music-documentary")),
    ]
    for cue in cues:
        command.extend(["-i", str(_asset_path(plan, cue["asset_id"]))])
    mix = OUTPUT / "render" / "audio-mix-pre-master.wav"
    command.extend(
        [
            "-filter_complex",
            audio_filter_graph(sfx_count=len(cues), cues=cues),
            "-map",
            "[aout]",
            "-c:a",
            "pcm_s24le",
            "-ar",
            "48000",
            str(mix),
        ]
    )
    _run(command)
    return mix


def _measure_loudness(path: Path) -> dict[str, float]:
    output = _run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-i",
            str(path),
            "-af",
            "loudnorm=I=-14.2:TP=-1.0:LRA=3.0:print_format=json",
            "-f",
            "null",
            "NUL",
        ]
    )
    matches = re.findall(r"\{\s*\"input_i\".*?\}", output, flags=re.S)
    if not matches:
        raise RuntimeError("Unable to parse loudness measurement")
    return parse_loudness_payload(json.loads(matches[-1]))


def parse_loudness_payload(payload: dict[str, Any]) -> dict[str, float]:
    numeric_keys = {
        "input_i",
        "input_tp",
        "input_lra",
        "input_thresh",
        "target_offset",
    }
    return {
        key: float(payload[key])
        for key in numeric_keys
        if key in payload
    }


def master_audio(path: Path) -> tuple[Path, dict[str, float]]:
    measurement = _measure_loudness(path)
    master = OUTPUT / "render" / "audio-master.wav"
    correction_db = 0.0
    for _ in range(3):
        filter_chain = linear_master_filter(
            measurement,
            correction_db=correction_db,
        )
        _run(
            [
                str(FFMPEG),
                "-hide_banner",
                "-y",
                "-i",
                str(path),
                "-af",
                filter_chain,
                "-c:a",
                "pcm_s24le",
                "-ar",
                "48000",
                str(master),
            ]
        )
        mastered = _measure_loudness(master)
        if (
            -14.45 <= mastered["input_i"] <= -13.95
            and mastered["input_tp"] <= -1.0
        ):
            break
        correction_db += master_loudness_correction_db(
            mastered["input_i"]
        )
    return master, measurement


def master_loudness_correction_db(measured_lufs: float) -> float:
    return round(max(-3.0, min(3.0, -14.2 - measured_lufs)), 3)


def linear_master_filter(
    measurement: dict[str, float],
    *,
    correction_db: float = 0.0,
) -> str:
    gain_db = max(
        -12.0,
        min(
            12.0,
            -14.2 - float(measurement["input_i"]) + correction_db,
        ),
    )
    return (
        f"volume={gain_db:.3f}dB,"
        "alimiter=limit=0.820000:level=0"
    )


def mux_final(video: Path, audio: Path) -> Path:
    edited = OUTPUT / "edited.mp4"
    _run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-y",
            "-i",
            str(video),
            "-i",
            str(audio),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-t",
            f"{build.DURATION_MS / 1000:.3f}",
            "-movflags",
            "+faststart",
            str(edited),
        ]
    )
    return edited


def main() -> int:
    plan_path = OUTPUT / "edit-plan.json"
    if not plan_path.is_file():
        raise FileNotFoundError(
            f"Run the selected 0813 story builder first: {plan_path}"
        )
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    video = render_video(plan)
    mix = render_audio_mix(plan)
    audio, measurement = master_audio(mix)
    edited = mux_final(video, audio)
    print(
        json.dumps(
            {
                "edited": str(edited),
                "video_bytes": edited.stat().st_size,
                "pre_master_loudness": measurement,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

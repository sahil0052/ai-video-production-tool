from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any

from imageio_ffmpeg import get_ffmpeg_exe
from PIL import Image, ImageDraw, ImageFont


SERVER_DIR = Path(__file__).resolve().parent
WORKSPACE = SERVER_DIR.parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from app.editor.production_assembly import (  # noqa: E402
    assemble_production,
)


OUTPUT_DIR = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0813-production-v1"
)
FFMPEG = Path(get_ffmpeg_exe())


def run(command: list[str], *, timeout: int = 1800) -> None:
    completed = subprocess.run(
        command,
        cwd=WORKSPACE,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=timeout,
        check=False,
        shell=False,
    )
    if completed.returncode != 0:
        detail = "\n".join(
            value
            for value in (
                completed.stdout[-3000:],
                completed.stderr[-6000:],
            )
            if value
        )
        raise RuntimeError(detail)


def font(size: int, *, condensed: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        [
            Path(r"C:\Windows\Fonts\impact.ttf"),
            Path(r"C:\Windows\Fonts\arialnb.ttf"),
        ]
        if condensed
        else [
            Path(r"C:\Windows\Fonts\arialbd.ttf"),
            Path(r"C:\Windows\Fonts\calibrib.ttf"),
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def fit_font(
    text: str,
    *,
    start: int,
    minimum: int,
    max_width: int,
    condensed: bool,
    stroke: int,
) -> ImageFont.FreeTypeFont:
    probe = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    for size in range(start, minimum - 1, -2):
        candidate = font(size, condensed=condensed)
        box = probe.textbbox(
            (0, 0),
            text,
            font=candidate,
            stroke_width=stroke,
        )
        if box[2] - box[0] <= max_width:
            return candidate
    return font(minimum, condensed=condensed)


def prepare_text_cards(plan: Any) -> dict[str, Path]:
    output = OUTPUT_DIR / "assets" / "ffmpeg-text"
    output.mkdir(parents=True, exist_ok=True)
    styles = {
        "hero-condensed": {
            "size": 196,
            "min": 120,
            "fill": (249, 255, 50, 255),
            "stroke": 10,
            "stroke_fill": (18, 19, 1, 255),
            "condensed": True,
        },
        "outlined-stack": {
            "size": 114,
            "min": 72,
            "fill": (255, 255, 255, 255),
            "stroke": 10,
            "stroke_fill": (4, 4, 4, 255),
            "condensed": False,
        },
        "gradient-number": {
            "size": 156,
            "min": 96,
            "fill": (220, 255, 112, 255),
            "stroke": 5,
            "stroke_fill": (24, 45, 2, 255),
            "condensed": True,
        },
        "correction-symbol": {
            "size": 112,
            "min": 72,
            "fill": (255, 48, 48, 255),
            "stroke": 7,
            "stroke_fill": (17, 3, 3, 255),
            "condensed": False,
        },
        "cyan-secondary": {
            "size": 90,
            "min": 62,
            "fill": (82, 231, 255, 255),
            "stroke": 6,
            "stroke_fill": (6, 52, 64, 255),
            "condensed": True,
        },
        "cta-quote": {
            "size": 138,
            "min": 90,
            "fill": (255, 229, 82, 255),
            "stroke": 8,
            "stroke_fill": (42, 33, 0, 255),
            "condensed": True,
        },
    }
    paths: dict[str, Path] = {}
    for cue in plan.kinetic_text_cues:
        style = styles[cue.family]
        condensed = style["condensed"] and cue.id != "text-monthly"
        image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        face = fit_font(
            cue.text,
            start=style["size"],
            minimum=style["min"],
            max_width=cue.max_width,
            condensed=condensed,
            stroke=style["stroke"],
        )
        draw.text(
            (cue.x, cue.y),
            cue.text,
            font=face,
            fill=style["fill"],
            stroke_width=style["stroke"],
            stroke_fill=style["stroke_fill"],
            anchor="mm",
            align="center",
        )
        if cue.id == "text-monthly":
            label_face = font(42)
            label = "MONTHLY CPI  0.1%"
            label_box = draw.textbbox(
                (540, 1488),
                label,
                font=label_face,
                stroke_width=2,
                anchor="mm",
            )
            draw.rounded_rectangle(
                (
                    label_box[0] - 24,
                    label_box[1] - 12,
                    label_box[2] + 24,
                    label_box[3] + 12,
                ),
                radius=18,
                fill=(12, 18, 22, 224),
            )
            draw.text(
                (540, 1488),
                label,
                font=label_face,
                fill=(255, 255, 255, 255),
                stroke_width=2,
                stroke_fill=(0, 0, 0, 255),
                anchor="mm",
            )
        path = output / f"{cue.id}.png"
        image.save(path)
        paths[cue.id] = path
    return paths


def asset_path(plan: Any, identifier: str) -> Path:
    asset = next(item for item in plan.assets if item.id == identifier)
    return Path(asset.path).resolve()


def base_args(
    path: Path,
    *,
    duration: float,
    source_start: float | None,
    image: bool,
) -> list[str]:
    if image:
        return [
            "-loop",
            "1",
            "-framerate",
            "30",
            "-t",
            f"{duration:.6f}",
            "-i",
            str(path),
        ]
    arguments: list[str] = []
    if source_start is not None:
        arguments.extend(["-ss", f"{source_start:.6f}"])
    arguments.extend(
        [
            "-t",
            f"{duration:.6f}",
            "-i",
            str(path),
        ]
    )
    return arguments


def render_segment(
    *,
    destination: Path,
    duration: float,
    base: Path,
    base_start: float | None = None,
    base_is_image: bool = False,
    base_zoom: float = 1.0,
    base_eq: str = "",
    overlays: list[dict[str, Any]] | None = None,
) -> None:
    overlays = overlays or []
    frame_count = max(1, round(duration * 30))
    render_duration = frame_count / 30
    command = [str(FFMPEG), "-hide_banner", "-y"]
    command.extend(
        base_args(
            base,
            duration=render_duration,
            source_start=base_start,
            image=base_is_image,
        )
    )
    for overlay in overlays:
        command.extend(
            base_args(
                Path(overlay["path"]),
                duration=max(0.05, overlay["end"] - overlay["start"]),
                source_start=overlay.get("source_start"),
                image=overlay.get("image", True),
            )
        )

    scaled_width = round(1080 * base_zoom / 2) * 2
    scaled_height = round(1920 * base_zoom / 2) * 2
    base_filters = [
        f"scale={scaled_width}:{scaled_height}:force_original_aspect_ratio=increase",
        "crop=1080:1920",
        "setsar=1",
        "fps=30",
    ]
    if not base_is_image:
        base_filters.append(
            f"tpad=stop_mode=clone:stop_duration={render_duration:.6f}"
        )
    if base_eq:
        base_filters.append(f"eq={base_eq}")
    base_filters.extend(["format=yuv420p", "setpts=PTS-STARTPTS"])
    filters = [f"[0:v]{','.join(base_filters)}[v0]"]
    current = "v0"
    for index, overlay in enumerate(overlays, start=1):
        width = int(overlay.get("width", 1080))
        height = int(overlay.get("height", 1920))
        start = float(overlay["start"])
        end = float(overlay["end"])
        active_duration = max(0.05, end - start)
        fade = min(0.12, active_duration / 4)
        overlay_filters = [
            f"scale={width}:{height}:force_original_aspect_ratio=increase",
            f"crop={width}:{height}",
            "setsar=1",
            "format=rgba",
        ]
        if overlay.get("fade", True):
            overlay_filters.extend(
                [
                    f"fade=t=in:st=0:d={fade:.4f}:alpha=1",
                    (
                        f"fade=t=out:st={max(0, active_duration - fade):.4f}"
                        f":d={fade:.4f}:alpha=1"
                    ),
                ]
            )
        overlay_filters.append(f"setpts=PTS-STARTPTS+{start:.6f}/TB")
        overlay_label = f"o{index}"
        filters.append(
            f"[{index}:v]{','.join(overlay_filters)}[{overlay_label}]"
        )
        next_label = f"v{index}"
        x = int(overlay.get("x", 0))
        y = int(overlay.get("y", 0))
        filters.append(
            (
                f"[{current}][{overlay_label}]overlay={x}:{y}:"
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
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-color_range",
            "tv",
            str(destination),
        ]
    )
    run(command)


def cue_overlays(
    plan: Any,
    text_cards: dict[str, Path],
    *,
    start_ms: int,
    end_ms: int,
) -> list[dict[str, Any]]:
    result = []
    for cue in plan.kinetic_text_cues:
        if cue.start_ms >= end_ms or cue.end_ms <= start_ms:
            continue
        local_start = max(0, cue.start_ms - start_ms) / 1000
        local_end = min(end_ms, cue.end_ms) - start_ms
        result.append(
            {
                "path": text_cards[cue.id],
                "image": True,
                "start": local_start,
                "end": local_end / 1000,
                "x": 0,
                "y": 0,
                "width": 1080,
                "height": 1920,
            }
        )
    return result


def render_ffmpeg_production(
    *,
    output_dir: Path,
    plan: Any,
    output: Path,
) -> None:
    del output_dir
    segments_dir = OUTPUT_DIR / "ffmpeg-segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    text_cards = prepare_text_cards(plan)
    presenter = asset_path(plan, "presenter-edl")

    def text(start: int, end: int) -> list[dict[str, Any]]:
        return cue_overlays(
            plan,
            text_cards,
            start_ms=start,
            end_ms=end,
        )

    segments: list[Path] = []

    def add(
        index: int,
        start_ms: int,
        end_ms: int,
        base: Path,
        *,
        base_start: float | None = None,
        base_is_image: bool = False,
        zoom: float = 1.0,
        eq: str = "",
        overlays: list[dict[str, Any]] | None = None,
    ) -> None:
        destination = segments_dir / f"shot-{index:02d}.mp4"
        render_segment(
            destination=destination,
            duration=(end_ms - start_ms) / 1000,
            base=base,
            base_start=base_start,
            base_is_image=base_is_image,
            base_zoom=zoom,
            base_eq=eq,
            overlays=[*(overlays or []), *text(start_ms, end_ms)],
        )
        segments.append(destination)

    presenter_eq = "brightness=-0.085:contrast=1.08:saturation=1.42"
    add(
        1,
        0,
        3220,
        presenter,
        base_start=0,
        zoom=1.04,
        eq=presenter_eq,
        overlays=[
            {
                "path": asset_path(plan, "graphic-lower-vignette"),
                "start": 0,
                "end": 2.98,
                "x": 0,
                "y": 0,
                "width": 1080,
                "height": 1920,
            },
            {
                "path": asset_path(plan, "licensed-fuel-nozzle"),
                "image": False,
                "source_start": 5.9,
                "start": 0.54,
                "end": 1.65,
                "x": 65,
                "y": 1050,
                "width": 450,
                "height": 500,
            },
            {
                "path": asset_path(plan, "licensed-rent-keys"),
                "image": False,
                "source_start": 0.45,
                "start": 1.62,
                "end": 3.08,
                "x": 565,
                "y": 1050,
                "width": 450,
                "height": 500,
            },
        ],
    )
    add(
        2,
        3220,
        7007,
        presenter,
        base_start=3.22,
        zoom=1.02,
        eq=presenter_eq,
        overlays=[
            {
                "path": asset_path(plan, "graphic-bls-identity"),
                "start": 0.3,
                "end": 3.2,
                "x": 190,
                "y": 1070,
                "width": 700,
                "height": 560,
            }
        ],
    )
    add(
        3,
        7007,
        9200,
        asset_path(plan, "licensed-shopping-cart"),
        base_start=0.7,
        zoom=1.04,
        eq="brightness=-0.02:contrast=1.05:saturation=0.95",
    )
    add(
        4,
        9200,
        11288,
        asset_path(plan, "licensed-shopping-cart"),
        base_start=3.1,
        zoom=1.11,
        eq="brightness=-0.02:contrast=1.06:saturation=0.96",
        overlays=[
            {
                "path": asset_path(plan, "graphic-basket-overlay"),
                "start": 0.22,
                "end": 2.088,
                "x": 0,
                "y": 0,
                "width": 1080,
                "height": 1920,
            }
        ],
    )
    add(5, 11288, 13200, presenter, base_start=11.288, zoom=1.13, eq=presenter_eq)
    add(6, 13200, 15031, presenter, base_start=13.2, zoom=1.05, eq=presenter_eq)
    add(
        7,
        15031,
        18700,
        presenter,
        base_start=15.031,
        zoom=1.02,
        eq=presenter_eq,
        overlays=[
            {
                "path": asset_path(plan, "graphic-actual-forecast"),
                "start": 0.2,
                "end": 3.1,
                "x": 0,
                "y": 0,
                "width": 1080,
                "height": 1920,
            }
        ],
    )
    add(
        8,
        18700,
        20900,
        asset_path(plan, "licensed-fuel-nozzle"),
        base_start=6.2,
        zoom=1.08,
        eq="brightness=0.02:contrast=1.08:saturation=1.04",
    )
    add(
        9,
        20900,
        22694,
        presenter,
        base_start=20.9,
        zoom=1.02,
        eq=presenter_eq,
        overlays=[
            {
                "path": asset_path(plan, "graphic-bls-energy"),
                "start": 0,
                "end": 1.794,
                "x": 90,
                "y": 160,
                "width": 900,
                "height": 1600,
                "fade": False,
            }
        ],
    )
    add(
        10,
        22694,
        25400,
        asset_path(plan, "licensed-rent-keys"),
        base_start=0.55,
        zoom=1.06,
        eq="brightness=0.01:contrast=1.06:saturation=1.08",
    )
    add(
        11,
        25400,
        27979,
        presenter,
        base_start=25.4,
        zoom=1.04,
        eq=presenter_eq,
        overlays=[
            {
                "path": asset_path(plan, "graphic-shelter-ring"),
                "start": 0.16,
                "end": 2.5,
                "x": 100,
                "y": 1020,
                "width": 880,
                "height": 760,
            }
        ],
    )
    add(
        12,
        27979,
        30300,
        asset_path(plan, "licensed-usd-counting"),
        base_start=0.8,
        zoom=1.07,
        eq="brightness=0.05:contrast=1.08:saturation=0.9",
        overlays=[
            {
                "path": asset_path(plan, "evidence-cnbc-dollar"),
                "start": 0.26,
                "end": 2.28,
                "x": 0,
                "y": 0,
                "width": 1080,
                "height": 1920,
            }
        ],
    )
    add(
        13,
        30300,
        33000,
        asset_path(plan, "graphic-question-plate"),
        base_is_image=True,
        zoom=1.04,
        eq="brightness=0.03:contrast=1.05:saturation=1.02",
    )
    add(
        14,
        33000,
        37161,
        presenter,
        base_start=33.0,
        zoom=1.04,
        eq=presenter_eq,
        overlays=[
            {
                "path": asset_path(plan, "graphic-factor-positioning"),
                "start": 0.1,
                "end": 1.42,
                "x": 160,
                "y": 1170,
                "width": 760,
                "height": 200,
            },
            {
                "path": asset_path(plan, "graphic-factor-rates"),
                "start": 1.42,
                "end": 2.81,
                "x": 160,
                "y": 1170,
                "width": 760,
                "height": 200,
            },
            {
                "path": asset_path(plan, "graphic-factor-risks"),
                "start": 2.81,
                "end": 4.1,
                "x": 160,
                "y": 1170,
                "width": 760,
                "height": 200,
            },
        ],
    )
    add(
        15,
        37161,
        42500,
        presenter,
        base_start=37.161,
        zoom=1.05,
        eq=presenter_eq,
        overlays=[
            {
                "path": asset_path(plan, "graphic-safeguards"),
                "start": 1.26,
                "end": 4.16,
                "x": 0,
                "y": 0,
                "width": 1080,
                "height": 1920,
            }
        ],
    )
    add(
        16,
        42500,
        45550,
        presenter,
        base_start=42.5,
        zoom=1.04,
        eq=presenter_eq,
        overlays=[
            {
                "path": asset_path(plan, "graphic-full-bill"),
                "start": 0.02,
                "end": 1.58,
                "x": 190,
                "y": 1010,
                "width": 700,
                "height": 730,
            },
            {
                "path": asset_path(plan, "brand-logo-original"),
                "start": 1.4,
                "end": 2.85,
                "x": 365,
                "y": 1120,
                "width": 350,
                "height": 230,
            },
        ],
    )

    concat_list = segments_dir / "concat.txt"
    concat_entries = []
    for path in segments:
        escaped_path = path.resolve().as_posix().replace("'", "'\\''")
        concat_entries.append(f"file '{escaped_path}'")
    concat_list.write_text(
        "\n".join(concat_entries),
        encoding="utf-8",
    )
    run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c",
            "copy",
            str(output),
        ]
    )


def main() -> int:
    result = assemble_production(
        output_dir=OUTPUT_DIR,
        renderer=render_ffmpeg_production,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

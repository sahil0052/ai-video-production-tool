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
    run_automated_production_review,
)
from build_0813_training_parity import BOUNDARIES  # noqa: E402


OUTPUT_DIR = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0813-production-v2-training-parity"
)
FFMPEG = Path(get_ffmpeg_exe())
NIGHT_EQ = "brightness=-0.035:contrast=1.08:saturation=0.82"
STATIC_EVIDENCE_SHOTS = frozenset({4, 10, 12, 19, 23, 25, 29, 37})


def reference_image_push(shot: int, requested: float) -> float:
    return 0 if shot in STATIC_EVIDENCE_SHOTS else requested


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
        raise RuntimeError(
            "\n".join(
                part
                for part in (
                    completed.stdout[-3000:],
                    completed.stderr[-6000:],
                )
                if part
            )
        )


def font(
    size: int,
    *,
    mono: bool = False,
    serif: bool = False,
    display: bool = False,
) -> ImageFont.FreeTypeFont:
    candidates: list[Path]
    if display:
        candidates = [
            OUTPUT_DIR
            / "assets"
            / "fonts"
            / "Anton-Regular.ttf",
            Path(r"C:\Windows\Fonts\impact.ttf"),
        ]
    elif mono:
        candidates = [
            OUTPUT_DIR
            / "assets"
            / "fonts"
            / "ShareTechMono-Regular.ttf",
            Path(r"C:\Windows\Fonts\consola.ttf"),
        ]
    elif serif:
        candidates = [
            Path(r"C:\Windows\Fonts\georgiai.ttf"),
            Path(r"C:\Windows\Fonts\timesi.ttf"),
        ]
    else:
        candidates = [
            Path(r"C:\Windows\Fonts\arialbd.ttf"),
            Path(r"C:\Windows\Fonts\calibrib.ttf"),
        ]
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
    mono: bool = False,
    serif: bool = False,
    display: bool = False,
    stroke: int = 0,
) -> ImageFont.FreeTypeFont:
    probe = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    for size in range(start, minimum - 1, -1):
        candidate = font(
            size,
            mono=mono,
            serif=serif,
            display=display,
        )
        box = probe.textbbox(
            (0, 0),
            text,
            font=candidate,
            stroke_width=stroke,
        )
        if box[2] - box[0] <= max_width:
            return candidate
    return font(
        minimum,
        mono=mono,
        serif=serif,
        display=display,
    )


def caption_y(start_ms: int) -> int:
    if start_ms <= 1_680:
        return 1_860
    if 16_427 <= start_ms < 18_630:
        return 1_790
    if 27_639 <= start_ms < 34_122:
        return 1_650
    if 34_122 <= start_ms < 35_242:
        return 1_760
    if 38_566 <= start_ms < 42_262:
        return 1_775
    if start_ms >= 42_262:
        return 1_515
    if 22_599 <= start_ms < 27_639:
        return 1_515
    return 1_430


def prepare_caption_cards(plan: Any) -> dict[int, Path]:
    output = OUTPUT_DIR / "assets" / "ffmpeg-captions"
    output.mkdir(parents=True, exist_ok=True)
    cards: dict[int, Path] = {}
    for index, page in enumerate(plan.caption_pages):
        text = " ".join(token.text for token in page.tokens)
        image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        is_technical = page.family == "technical-mono"
        render_text = text.upper() if is_technical else text
        face = fit_font(
            render_text,
            start=35 if is_technical else 42,
            minimum=27 if is_technical else 34,
            max_width=int(page.max_width),
            mono=is_technical,
        )
        box = draw.textbbox((0, 0), render_text, font=face)
        width = box[2] - box[0]
        height = box[3] - box[1]
        x = 540
        y = caption_y(int(page.start_ms))
        padding_x = 13 if is_technical else 18
        padding_y = 8 if is_technical else 11
        rectangle = (
            round(x - width / 2 - padding_x),
            round(y - height / 2 - padding_y),
            round(x + width / 2 + padding_x),
            round(y + height / 2 + padding_y),
        )
        draw.rounded_rectangle(
            rectangle,
            radius=6 if is_technical else 14,
            fill=(3, 5, 7, 232 if is_technical else 238),
        )
        draw.text(
            (x, y - 1),
            render_text,
            font=face,
            fill=(255, 255, 255, 255),
            anchor="mm",
        )
        path = output / f"caption-{index:03d}.png"
        image.save(path)
        cards[index] = path
    return cards


def prepare_kinetic_cards(plan: Any) -> dict[str, Path]:
    output = OUTPUT_DIR / "assets" / "ffmpeg-kinetic"
    output.mkdir(parents=True, exist_ok=True)
    cards: dict[str, Path] = {}
    for cue in plan.kinetic_text_cues:
        image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        if cue.id == "hook-petrol":
            face = fit_font(
                cue.text,
                start=138,
                minimum=96,
                max_width=cue.max_width,
                display=True,
                stroke=3,
            )
            draw.text(
                (cue.x + 5, cue.y + 7),
                cue.text,
                font=face,
                fill=(0, 0, 0, 210),
                stroke_width=5,
                stroke_fill=(0, 0, 0, 230),
                anchor="mm",
            )
            draw.text(
                (cue.x, cue.y),
                cue.text,
                font=face,
                fill=(91, 245, 105, 255),
                stroke_width=2,
                stroke_fill=(5, 12, 7, 255),
                anchor="mm",
            )
        elif cue.id == "hook-rent":
            face = fit_font(
                cue.text,
                start=102,
                minimum=72,
                max_width=cue.max_width,
                serif=True,
                stroke=3,
            )
            draw.text(
                (cue.x + 4, cue.y + 6),
                cue.text,
                font=face,
                fill=(0, 0, 0, 190),
                stroke_width=4,
                stroke_fill=(0, 0, 0, 210),
                anchor="mm",
            )
            draw.text(
                (cue.x, cue.y),
                cue.text,
                font=face,
                fill=(255, 255, 250, 255),
                stroke_width=2,
                stroke_fill=(8, 9, 10, 255),
                anchor="mm",
            )
        else:
            face = fit_font(
                cue.text,
                start=49,
                minimum=38,
                max_width=cue.max_width,
                mono=True,
            )
            box = draw.textbbox((0, 0), cue.text, font=face)
            width = box[2] - box[0]
            height = box[3] - box[1]
            draw.rounded_rectangle(
                (
                    round(cue.x - width / 2 - 22),
                    round(cue.y - height / 2 - 14),
                    round(cue.x + width / 2 + 22),
                    round(cue.y + height / 2 + 14),
                ),
                radius=9,
                fill=(3, 5, 7, 225),
            )
            draw.text(
                (cue.x, cue.y),
                cue.text,
                font=face,
                fill=(255, 239, 128, 255),
                anchor="mm",
            )
        path = output / f"{cue.id}.png"
        image.save(path)
        cards[cue.id] = path
    return cards


def asset_path(plan: Any, identifier: str) -> Path:
    item = next(asset for asset in plan.assets if asset.id == identifier)
    return Path(item.path).resolve()


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
    arguments.extend(["-t", f"{duration:.6f}", "-i", str(path)])
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
    image_push: float = 0.045,
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

    filters: list[str] = []
    if base_is_image:
        denominator = max(1, frame_count - 1)
        zoom_expression = (
            f"1.0+{image_push:.6f}*on/{denominator}"
            if image_push
            else "1.0"
        )
        base_filters = [
            "scale=1242:2208:force_original_aspect_ratio=increase",
            "crop=1242:2208",
            (
                "zoompan="
                f"z='{zoom_expression}':"
                "x='iw/2-(iw/zoom/2)':"
                "y='ih/2-(ih/zoom/2)':"
                "d=1:s=1080x1920:fps=30"
            ),
            "setsar=1",
        ]
    else:
        scaled_width = round(1080 * base_zoom / 2) * 2
        scaled_height = round(1920 * base_zoom / 2) * 2
        base_filters = [
            (
                f"scale={scaled_width}:{scaled_height}:"
                "force_original_aspect_ratio=increase"
            ),
            "crop=1080:1920",
            "setsar=1",
            "fps=30",
            f"tpad=stop_mode=clone:stop_duration={render_duration:.6f}",
        ]
    if base_eq:
        base_filters.append(f"eq={base_eq}")
    base_filters.extend(["format=yuv420p", "setpts=PTS-STARTPTS"])
    filters.append(f"[0:v]{','.join(base_filters)}[v0]")
    current = "v0"

    for index, overlay in enumerate(overlays, start=1):
        width = int(overlay.get("width", 1080))
        height = int(overlay.get("height", 1920))
        start = float(overlay["start"])
        end = float(overlay["end"])
        active_duration = max(0.05, end - start)
        crop_y = float(overlay.get("crop_y", 0.5))
        overlay_filters = [
            (
                f"scale={width}:{height}:"
                "force_original_aspect_ratio=increase"
            ),
            (
                f"crop={width}:{height}:"
                "x='(in_w-out_w)/2':"
                f"y='(in_h-out_h)*{crop_y:.6f}'"
            ),
            "setsar=1",
            "format=rgba",
        ]
        overlay_eq = str(overlay.get("eq", "")).strip()
        if overlay_eq:
            overlay_filters.append(f"eq={overlay_eq}")
        if not overlay.get("image", True):
            overlay_filters.append(
                f"tpad=stop_mode=clone:stop_duration={active_duration:.6f}"
            )
        if overlay.get("fade", False):
            fade = min(0.10, active_duration / 4)
            overlay_filters.extend(
                [
                    f"fade=t=in:st=0:d={fade:.4f}:alpha=1",
                    (
                        f"fade=t=out:st={max(0, active_duration - fade):.4f}"
                        f":d={fade:.4f}:alpha=1"
                    ),
                ]
            )
        overlay_filters.append(
            f"setpts=PTS-STARTPTS+{start:.6f}/TB"
        )
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
            "17",
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
    run(command)


def timed_overlays(
    plan: Any,
    caption_cards: dict[int, Path],
    kinetic_cards: dict[str, Path],
    *,
    start_ms: int,
    end_ms: int,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, page in enumerate(plan.caption_pages):
        if page.start_ms >= end_ms or page.end_ms <= start_ms:
            continue
        result.append(
            {
                "path": caption_cards[index],
                "image": True,
                "start": max(0, page.start_ms - start_ms) / 1000,
                "end": (min(end_ms, page.end_ms) - start_ms) / 1000,
                "x": 0,
                "y": 0,
                "width": 1080,
                "height": 1920,
                "fade": False,
            }
        )
    for cue in plan.kinetic_text_cues:
        if cue.start_ms >= end_ms or cue.end_ms <= start_ms:
            continue
        result.append(
            {
                "path": kinetic_cards[cue.id],
                "image": True,
                "start": max(0, cue.start_ms - start_ms) / 1000,
                "end": (min(end_ms, cue.end_ms) - start_ms) / 1000,
                "x": 0,
                "y": 0,
                "width": 1080,
                "height": 1920,
                "fade": False,
            }
        )
    return result


def render_training_parity(
    *,
    output_dir: Path,
    plan: Any,
    output: Path,
) -> None:
    del output_dir
    segments_dir = OUTPUT_DIR / "ffmpeg-segments-v2"
    segments_dir.mkdir(parents=True, exist_ok=True)
    caption_cards = prepare_caption_cards(plan)
    kinetic_cards = prepare_kinetic_cards(plan)
    presenter = asset_path(plan, "presenter-edl")

    def timed(start: int, end: int) -> list[dict[str, Any]]:
        return timed_overlays(
            plan,
            caption_cards,
            kinetic_cards,
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
        image_push: float = 0.045,
        overlays: list[dict[str, Any]] | None = None,
    ) -> None:
        destination = segments_dir / f"shot-{index:02d}.mp4"
        effective_image_push = (
            reference_image_push(index, image_push)
            if base_is_image
            else image_push
        )
        render_segment(
            destination=destination,
            duration=(end_ms - start_ms) / 1000,
            base=base,
            base_start=base_start,
            base_is_image=base_is_image,
            base_zoom=zoom,
            base_eq=eq,
            image_push=effective_image_push,
            overlays=[*(overlays or []), *timed(start_ms, end_ms)],
        )
        segments.append(destination)

    def add_shot(
        number: int,
        base: Path,
        **kwargs: Any,
    ) -> None:
        add(
            number,
            BOUNDARIES[number - 1],
            BOUNDARIES[number],
            base,
            **kwargs,
        )

    presenter_eq = "brightness=-0.07:contrast=1.10:saturation=1.08"
    context_eq = "brightness=-0.055:contrast=1.10:saturation=0.96"
    fuel = asset_path(plan, "licensed-fuel-nozzle")
    rent_keys = asset_path(plan, "licensed-rent-keys")
    shopping = asset_path(plan, "licensed-shopping-cart")
    produce = asset_path(plan, "licensed-grocery-produce")
    grocery_market = asset_path(plan, "licensed-grocery-market")
    apartment = asset_path(plan, "licensed-apartment-facade")
    apartment_night = asset_path(plan, "licensed-apartment-night")
    gas_station_wide = asset_path(plan, "licensed-gas-station-wide")
    gasoline_action = asset_path(plan, "licensed-gasoline-action")
    trader = asset_path(plan, "licensed-trader-monitor")
    finance = asset_path(plan, "licensed-finance-workspace")
    market_tablet = asset_path(plan, "licensed-market-tablet")

    add_shot(
        1,
        fuel,
        base_start=2.0,
        zoom=1.08,
        eq="brightness=-0.035:contrast=1.12:saturation=0.98",
        overlays=[
            {
                "path": presenter,
                "image": False,
                "source_start": 0,
                "start": 0,
                "end": 1.4,
                "x": 0,
                "y": 1094,
                "width": 1080,
                "height": 826,
                "crop_y": 0.20,
                "eq": presenter_eq,
            },
            {
                "path": asset_path(plan, "graphic-split-divider"),
                "image": True,
                "start": 0,
                "end": 1.4,
                "x": 0,
                "y": 0,
                "width": 1080,
                "height": 1920,
            },
        ],
    )
    add_shot(
        2,
        rent_keys,
        base_start=0.45,
        zoom=1.10,
        eq="brightness=-0.065:contrast=1.12:saturation=0.93",
    )
    add_shot(
        3,
        presenter,
        base_start=3.12,
        zoom=1.04,
        eq=presenter_eq,
    )
    add_shot(
        4,
        asset_path(plan, "evidence-bls-overview"),
        base_is_image=True,
        image_push=0.018,
    )
    add_shot(
        5,
        asset_path(plan, "evidence-bls-identity"),
        base_is_image=True,
        image_push=0.02,
    )
    add_shot(
        6,
        grocery_market,
        base_start=2.0,
        zoom=1.06,
        eq=context_eq,
    )
    add_shot(
        7,
        shopping,
        base_start=0.7,
        zoom=1.12,
        eq="brightness=-0.06:contrast=1.10:saturation=0.94",
    )
    add_shot(
        8,
        produce,
        base_start=0.7,
        zoom=1.07,
        eq="brightness=-0.045:contrast=1.10:saturation=0.96",
    )
    add_shot(
        9,
        asset_path(plan, "graphic-grid-overlay"),
        base_is_image=True,
        image_push=0,
        overlays=[
            {
                "path": asset_path(plan, "evidence-bls-overview"),
                "image": True,
                "start": 0,
                "end": 0.44,
                "x": 0,
                "y": 0,
                "width": 1080,
                "height": 1920,
            },
            {
                "path": produce,
                "image": False,
                "source_start": 2.6,
                "start": 0.44,
                "end": 0.878,
                "x": 0,
                "y": 0,
                "width": 540,
                "height": 960,
                "eq": context_eq,
            },
            {
                "path": gas_station_wide,
                "image": False,
                "source_start": 0.35,
                "start": 0.44,
                "end": 0.878,
                "x": 540,
                "y": 0,
                "width": 540,
                "height": 960,
                "eq": context_eq,
            },
            {
                "path": apartment_night,
                "image": False,
                "source_start": 0.35,
                "start": 0.44,
                "end": 0.878,
                "x": 0,
                "y": 960,
                "width": 540,
                "height": 960,
                "eq": NIGHT_EQ,
            },
            {
                "path": finance,
                "image": False,
                "source_start": 1.6,
                "start": 0.44,
                "end": 0.878,
                "x": 540,
                "y": 960,
                "width": 540,
                "height": 960,
                "eq": context_eq,
            },
            {
                "path": asset_path(plan, "graphic-grid-overlay"),
                "image": True,
                "start": 0.44,
                "end": 0.878,
                "x": 0,
                "y": 0,
                "width": 1080,
                "height": 1920,
            },
        ],
    )
    add_shot(
        10,
        asset_path(plan, "evidence-bls-monthly-excerpt"),
        base_is_image=True,
        image_push=0.025,
    )
    add_shot(
        11,
        asset_path(plan, "evidence-bls-monthly-number"),
        base_is_image=True,
        image_push=0.018,
    )
    add_shot(
        12,
        asset_path(plan, "evidence-bls-yearly-excerpt"),
        base_is_image=True,
        image_push=0.025,
    )
    add_shot(
        13,
        asset_path(plan, "evidence-bls-yearly-number"),
        base_is_image=True,
        image_push=0.018,
    )
    add_shot(
        14,
        presenter,
        base_start=14.926,
        zoom=1.09,
        eq=presenter_eq,
    )
    add_shot(
        15,
        asset_path(plan, "graphic-actual-match"),
        base_is_image=True,
        image_push=0.018,
    )
    add_shot(
        16,
        asset_path(plan, "graphic-inside-story"),
        base_is_image=True,
        image_push=0.02,
    )
    add_shot(
        17,
        gas_station_wide,
        base_start=0.35,
        zoom=1.04,
        eq="brightness=-0.025:contrast=1.08:saturation=1.05",
    )
    add_shot(
        18,
        gasoline_action,
        base_start=0.15,
        zoom=1.03,
        eq="brightness=-0.02:contrast=1.08:saturation=1.04",
    )
    add_shot(
        19,
        asset_path(plan, "evidence-bls-energy-table"),
        base_is_image=True,
        image_push=0.025,
    )
    add_shot(
        20,
        asset_path(plan, "evidence-bls-gasoline-number"),
        base_is_image=True,
        image_push=0.018,
    )
    add_shot(
        21,
        apartment_night,
        base_start=0.35,
        zoom=1.08,
        eq=NIGHT_EQ,
    )
    add_shot(
        22,
        apartment,
        base_start=1.1,
        zoom=1.07,
        eq=NIGHT_EQ,
    )
    add_shot(
        23,
        asset_path(plan, "evidence-bls-shelter"),
        base_is_image=True,
        image_push=0.025,
    )
    add_shot(
        24,
        asset_path(plan, "evidence-cnbc-headline"),
        base_is_image=True,
        image_push=0.022,
    )
    add_shot(
        25,
        asset_path(plan, "evidence-cnbc-paragraph"),
        base_is_image=True,
        image_push=0.022,
    )
    add_shot(
        26,
        market_tablet,
        base_start=0.5,
        zoom=1.08,
        eq=NIGHT_EQ,
        overlays=[
            {
                "path": asset_path(plan, "graphic-question-overlay"),
                "image": True,
                "start": 0,
                "end": (BOUNDARIES[26] - BOUNDARIES[25]) / 1000,
                "x": 0,
                "y": 0,
                "width": 1080,
                "height": 1920,
            }
        ],
    )
    add_shot(
        27,
        asset_path(plan, "evidence-cnbc-paragraph"),
        base_is_image=True,
        image_push=0.02,
    )
    add_shot(
        28,
        trader,
        base_start=2.3,
        zoom=1.09,
        eq="brightness=-0.08:contrast=1.12:saturation=0.92",
    )
    add_shot(
        29,
        asset_path(plan, "evidence-cnbc-rates"),
        base_is_image=True,
        image_push=0.02,
    )
    add_shot(
        30,
        presenter,
        base_start=35.242,
        zoom=1.10,
        eq=presenter_eq,
    )
    add_shot(
        31,
        presenter,
        base_start=37.061,
        zoom=1.04,
        eq=presenter_eq,
    )
    add_shot(
        32,
        asset_path(plan, "graphic-execution-rules"),
        base_is_image=True,
        image_push=0.018,
    )
    add_shot(
        33,
        asset_path(plan, "graphic-spread-limit"),
        base_is_image=True,
        image_push=0.012,
    )
    add_shot(
        34,
        asset_path(plan, "graphic-pause-control"),
        base_is_image=True,
        image_push=0.012,
    )
    add_shot(
        35,
        asset_path(plan, "graphic-confirmation-control"),
        base_is_image=True,
        image_push=0.012,
    )
    add_shot(
        36,
        asset_path(plan, "evidence-headline-proof"),
        base_is_image=True,
        image_push=0.018,
    )
    add_shot(
        37,
        asset_path(plan, "evidence-bls-overview"),
        base_is_image=True,
        image_push=0.018,
    )
    add_shot(
        38,
        presenter,
        base_start=44.093,
        zoom=1.06,
        eq=presenter_eq,
        overlays=[
            {
                "path": asset_path(plan, "brand-logo-original"),
                "image": True,
                "start": 0.12,
                "end": 1.35,
                "x": 790,
                "y": 90,
                "width": 230,
                "height": 175,
            }
        ],
    )

    concat_list = segments_dir / "concat.txt"
    concat_list.write_text(
        "\n".join(
            f"file '{path.resolve().as_posix()}'"
            for path in segments
        ),
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


def review(
    *,
    output_dir: Path,
    plan: Any,
    edited: Path,
) -> dict[str, Any]:
    from review_0813_training_parity import deepgram_transcriber

    return run_automated_production_review(
        output_dir=output_dir,
        plan=plan,
        edited=edited,
        transcriber=deepgram_transcriber,
    )


def main() -> int:
    result = assemble_production(
        output_dir=OUTPUT_DIR,
        renderer=render_training_parity,
        reviewer=review,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

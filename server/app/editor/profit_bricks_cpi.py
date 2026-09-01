from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil
from statistics import median
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from app.editor.analysis import probe_video
from app.editor.human_reference_0810 import (
    _detect_silence_intervals,
    _prepare_dialogue_media,
    _remap_transcript,
    build_dialogue_edl_from_silences,
    measure_visible_interval_duration,
)
from app.editor.sound_design import (
    _click,
    _impact,
    _label_snap,
    _paper_scroll,
    _tension_riser,
    _tonal_drop,
    _whoosh,
    _write_wav,
)
from app.models import (
    AssetRef,
    AudioPlan,
    EvidenceItem,
    GainAutomation,
    OutputSpec,
    SfxCue,
    SpeechProtectionWindow,
    TranscriptSegment,
    TranscriptWord,
)
from app.production_models import (
    BlueprintLayerSpec,
    EffectKeyframe,
    KineticTextCue,
    LayerBounds,
    MotionEventSpec,
    OpacityKeyframe,
    ProductionBlueprint,
    TransformKeyframe,
)


OUTPUT_DURATION_MS = 45_550
_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_STYLE_REFERENCE = Path(r"D:\Downloads\Profit Bricks_Reel 04.mp4")
_DEFAULT_GOLDEN_DIR = (
    _WORKSPACE_ROOT
    / "storage"
    / "deliverables"
    / "0810-production-v2-human-reference"
)
_DEFAULT_MUSIC = (
    _DEFAULT_GOLDEN_DIR
    / "assets"
    / "audio"
    / "mixkit-minimal-techno-01-162.mp3"
)
_DEFAULT_LOGO = (
    _DEFAULT_GOLDEN_DIR
    / "assets"
    / "brand"
    / "profit-bricks-logo.png"
)

_SHOT_SPECS = [
    (0, 3_220, "presenter", "petrol-rent-hook"),
    (3_220, 7_007, "presenter", "cpi-date-reveal"),
    (7_007, 9_200, "licensed-context", "shopping-basket-wide"),
    (9_200, 11_288, "licensed-context", "shopping-basket-components"),
    (11_288, 13_200, "presenter", "monthly-number"),
    (13_200, 15_031, "presenter", "yearly-number"),
    (15_031, 18_700, "presenter", "actual-forecast-contrast"),
    (18_700, 20_900, "licensed-context", "energy-down-action"),
    (20_900, 22_694, "direct-evidence", "gasoline-proof"),
    (22_694, 25_400, "licensed-context", "rent-context"),
    (25_400, 27_979, "presenter", "shelter-share"),
    (27_979, 30_300, "licensed-context", "dollar-reaction"),
    (30_300, 33_000, "deterministic-graphic", "surprise-question"),
    (33_000, 37_161, "presenter", "market-factors"),
    (37_161, 42_500, "presenter", "risk-controls"),
    (42_500, OUTPUT_DURATION_MS, "presenter", "full-bill-cta"),
]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _copy_required(source: Path, destination: Path) -> Path:
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def _copy_logo_without_background(
    source: Path,
    destination: Path,
) -> Path:
    if not source.is_file():
        raise FileNotFoundError(source)
    image = Image.open(source).convert("RGBA")
    transparent_white = (255, 255, 255, 0)
    for corner in (
        (0, 0),
        (image.width - 1, 0),
        (0, image.height - 1),
        (image.width - 1, image.height - 1),
    ):
        ImageDraw.floodfill(
            image,
            corner,
            transparent_white,
            thresh=48,
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)
    return destination


def _font(size: int, *, condensed: bool = False) -> ImageFont.FreeTypeFont:
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


def _fit_font(
    text: str,
    *,
    start_size: int,
    minimum_size: int,
    max_width: int,
    condensed: bool = False,
) -> ImageFont.FreeTypeFont:
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    for size in range(start_size, minimum_size - 1, -2):
        font = _font(size, condensed=condensed)
        box = probe.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= max_width:
            return font
    return _font(minimum_size, condensed=condensed)


def _centered(
    draw: ImageDraw.ImageDraw,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    *,
    fill: tuple[int, ...] | str,
    width: int = 1080,
    stroke_width: int = 0,
    stroke_fill: tuple[int, ...] | str | None = None,
) -> None:
    box = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    draw.text(
        ((width - (box[2] - box[0])) / 2, y),
        text,
        font=font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )


def _vertical_gradient(
    size: tuple[int, int],
    top: tuple[int, int, int],
    bottom: tuple[int, int, int],
) -> Image.Image:
    image = Image.new("RGB", size)
    pixels = image.load()
    for y in range(size[1]):
        amount = y / max(1, size[1] - 1)
        color = tuple(
            round(top[channel] * (1 - amount) + bottom[channel] * amount)
            for channel in range(3)
        )
        for x in range(size[0]):
            pixels[x, y] = color
    return image


def _build_lower_vignette(path: Path) -> Path:
    image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    pixels = image.load()
    for y in range(760, 1920):
        amount = (y - 760) / 1160
        alpha = round(205 * amount**1.65)
        for x in range(1080):
            pixels[x, y] = (4, 5, 6, alpha)
    image.save(path)
    return path


def _build_bls_identity_card(path: Path) -> Path:
    image = Image.new("RGBA", (700, 560), (0, 0, 0, 0))
    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (28, 36, 674, 542),
        radius=44,
        fill=(0, 0, 0, 105),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    image.alpha_composite(shadow)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (22, 20, 678, 526),
        radius=44,
        fill=(250, 250, 246, 252),
        outline=(18, 55, 99, 235),
        width=4,
    )
    draw.rectangle((22, 20, 678, 118), fill=(8, 38, 79, 255))
    draw.text((54, 44), "U.S. BUREAU OF LABOR STATISTICS", font=_font(28), fill="white")
    draw.text((54, 148), "CONSUMER PRICE INDEX", font=_font(46), fill=(12, 27, 49))
    draw.text((54, 216), "JULY 2026", font=_font(66, condensed=True), fill=(226, 46, 45))
    draw.rounded_rectangle((54, 310, 646, 430), radius=24, fill=(232, 238, 246))
    draw.text((86, 331), "RELEASED", font=_font(25), fill=(68, 77, 90))
    draw.text((252, 322), "12 AUG 2026", font=_font(42), fill=(7, 38, 79))
    draw.text(
        (54, 466),
        "SOURCE: U.S. BLS • OFFICIAL RELEASE",
        font=_font(22),
        fill=(65, 72, 82),
    )
    image.save(path)
    return path


def _build_basket_overlay(path: Path) -> Path:
    image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    labels = [
        (92, 230, "FOOD", (255, 221, 73, 235)),
        (610, 230, "PETROL", (91, 225, 255, 235)),
        (92, 1530, "RENT", (255, 112, 83, 235)),
        (610, 1530, "SERVICES", (150, 255, 115, 235)),
    ]
    for x, y, text, color in labels:
        draw.rounded_rectangle(
            (x, y, x + 380, y + 118),
            radius=30,
            fill=(5, 12, 18, 220),
            outline=color,
            width=4,
        )
        font = _fit_font(
            text,
            start_size=56,
            minimum_size=42,
            max_width=320,
            condensed=True,
        )
        box = draw.textbbox((0, 0), text, font=font)
        draw.text(
            (x + 190 - (box[2] - box[0]) / 2, y + 28),
            text,
            font=font,
            fill=color,
        )
    image.save(path)
    return path


def _build_actual_forecast_card(path: Path) -> Path:
    image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (90, 1090, 990, 1660),
        radius=52,
        fill=(5, 17, 31, 235),
        outline=(84, 225, 255, 190),
        width=4,
    )
    draw.text((140, 1140), "HEADLINE CHECK", font=_font(34), fill=(95, 225, 255))
    for x, label in ((140, "ACTUAL"), (590, "FORECAST")):
        draw.rounded_rectangle(
            (x, 1240, x + 350, 1465),
            radius=32,
            fill=(244, 247, 249, 248),
        )
        draw.text((x + 34, 1273), label, font=_font(30), fill=(45, 55, 66))
        draw.text((x + 42, 1330), "MATCH", font=_font(72, condensed=True), fill=(26, 154, 108))
    draw.line((490, 1350, 590, 1350), fill=(255, 224, 67), width=12)
    draw.text(
        (150, 1530),
        "SAME HEADLINE • DIFFERENT INTERNAL STORY",
        font=_font(27),
        fill=(250, 250, 250),
    )
    image.save(path)
    return path


def _build_energy_card(path: Path) -> Path:
    image = _vertical_gradient((1080, 1920), (247, 249, 251), (220, 234, 244))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 1080, 182), fill=(8, 38, 79))
    draw.text((64, 48), "U.S. BLS • CPI JULY 2026", font=_font(39), fill="white")
    draw.text((64, 238), "WHAT FELL", font=_font(58, condensed=True), fill=(16, 31, 55))
    cards = [
        (80, 410, "ENERGY", "-1.5%", (28, 155, 189)),
        (80, 965, "GASOLINE", "-2.9%", (225, 63, 53)),
    ]
    for x, y, label, value, accent in cards:
        draw.rounded_rectangle(
            (x, y, 1000, y + 430),
            radius=50,
            fill=(255, 255, 255),
            outline=accent,
            width=7,
        )
        draw.text((140, y + 62), label, font=_font(52), fill=(48, 58, 68))
        value_font = _fit_font(
            value,
            start_size=190,
            minimum_size=150,
            max_width=760,
            condensed=True,
        )
        draw.text((140, y + 146), value, font=value_font, fill=accent)
        draw.polygon(
            [(845, y + 120), (930, y + 120), (887, y + 240)],
            fill=accent,
        )
    draw.text(
        (64, 1800),
        "SOURCE: U.S. BUREAU OF LABOR STATISTICS • RELEASED 12 AUG 2026",
        font=_font(24),
        fill=(53, 66, 80),
    )
    image.save(path, quality=96)
    return path


def _build_shelter_ring(path: Path) -> Path:
    image = Image.new("RGBA", (880, 760), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (20, 20, 860, 740),
        radius=52,
        fill=(8, 22, 38, 238),
        outline=(255, 190, 65, 230),
        width=5,
    )
    draw.text((64, 66), "MONTHLY CPI INCREASE", font=_font(34), fill=(190, 218, 238))
    ring_box = (94, 170, 514, 590)
    draw.arc(ring_box, 0, 360, fill=(76, 91, 108), width=72)
    draw.arc(ring_box, -90, 150, fill=(255, 174, 48), width=72)
    draw.text((174, 300), "~2/3", font=_font(88, condensed=True), fill="white")
    draw.text((552, 220), "FROM", font=_font(36), fill=(190, 218, 238))
    draw.text((548, 278), "SHELTER", font=_font(68, condensed=True), fill=(255, 190, 65))
    draw.text((548, 370), "RENT +", font=_font(39), fill="white")
    draw.text((548, 420), "HOUSING", font=_font(39), fill="white")
    draw.text(
        (64, 650),
        "SOURCE: REUTERS ANALYSIS OF U.S. BLS DATA",
        font=_font(22),
        fill=(184, 200, 216),
    )
    image.save(path)
    return path


def _build_cnbc_card(source: Path, path: Path) -> Path:
    if not source.is_file():
        raise FileNotFoundError(source)
    screenshot = Image.open(source).convert("RGB")
    headline = screenshot.crop((145, 230, 1240, 500))
    paragraph = screenshot.crop((260, 1010, 1030, 1275))
    image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (70, 920, 1010, 1780),
        radius=42,
        fill=(3, 26, 59, 244),
        outline=(52, 153, 220, 220),
        width=4,
    )
    headline = ImageOps.contain(headline, (840, 390), Image.Resampling.LANCZOS)
    paragraph = ImageOps.contain(paragraph, (790, 360), Image.Resampling.LANCZOS)
    image.paste(headline, ((1080 - headline.width) // 2, 990))
    image.paste(paragraph, ((1080 - paragraph.width) // 2, 1375))
    draw.text((110, 950), "CNBC • 12 AUG 2026", font=_font(24), fill=(143, 211, 255))
    draw.text(
        (110, 1715),
        "GENUINE EDITORIAL CAPTURE",
        font=_font(22),
        fill=(167, 196, 221),
    )
    image.save(path)
    return path


def _build_question_plate(path: Path) -> Path:
    image = _vertical_gradient((1080, 1920), (34, 5, 12), (184, 18, 34)).convert("RGBA")
    draw = ImageDraw.Draw(image)
    for radius, alpha in ((360, 32), (270, 42), (180, 56)):
        draw.ellipse(
            (540 - radius, 750 - radius, 540 + radius, 750 + radius),
            outline=(255, 112, 108, alpha),
            width=8,
        )
    question = "?"
    font = _font(570, condensed=True)
    box = draw.textbbox((0, 0), question, font=font, stroke_width=12)
    draw.text(
        (540 - (box[2] - box[0]) / 2, 420),
        question,
        font=font,
        fill=(255, 238, 220),
        stroke_width=12,
        stroke_fill=(52, 0, 9),
    )
    image.save(path)
    return path


def _build_label_card(path: Path, text: str, accent: tuple[int, int, int]) -> Path:
    image = Image.new("RGBA", (760, 200), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (10, 10, 750, 190),
        radius=38,
        fill=(5, 19, 34, 238),
        outline=(*accent, 230),
        width=5,
    )
    draw.ellipse((48, 68, 108, 128), fill=(*accent, 255))
    font = _fit_font(
        text,
        start_size=62,
        minimum_size=44,
        max_width=570,
        condensed=True,
    )
    box = draw.textbbox((0, 0), text, font=font)
    draw.text((150, 100 - (box[3] - box[1]) / 2 - 4), text, font=font, fill="white")
    image.save(path)
    return path


def _build_safeguards(path: Path) -> Path:
    image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (80, 1110, 1000, 1680),
        radius=50,
        fill=(3, 18, 30, 232),
        outline=(91, 229, 255, 170),
        width=4,
    )
    draw.text((130, 1150), "ROBOT SAFEGUARDS", font=_font(36), fill=(97, 225, 255))
    entries = [
        ("01", "SPREAD LIMIT"),
        ("02", "PAUSE"),
        ("03", "CONFIRM"),
    ]
    for index, (number, label) in enumerate(entries):
        y = 1230 + index * 130
        draw.rounded_rectangle((130, y, 950, y + 105), radius=26, fill=(244, 247, 249, 248))
        draw.text((160, y + 24), number, font=_font(39), fill=(29, 151, 112))
        draw.text((265, y + 22), label, font=_font(43, condensed=True), fill=(13, 31, 49))
    image.save(path)
    return path


def _build_full_bill(path: Path) -> Path:
    image = Image.new("RGBA", (700, 730), (0, 0, 0, 0))
    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((38, 42, 668, 706), radius=34, fill=(0, 0, 0, 105))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    image.alpha_composite(shadow)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (24, 18, 676, 690),
        radius=34,
        fill=(255, 252, 232, 252),
        outline=(22, 43, 61, 225),
        width=4,
    )
    draw.text((72, 58), "MARKET'S FULL BILL", font=_font(52, condensed=True), fill=(14, 32, 48))
    draw.line((72, 135, 628, 135), fill=(24, 45, 62), width=3)
    rows = [
        ("HEADLINE", "EXPECTED"),
        ("SHELTER", "STICKY"),
        ("POSITIONING", "MATTERS"),
        ("RATE EXPECTATIONS", "MATTER"),
        ("OTHER RISKS", "MATTER"),
    ]
    for index, (left, right) in enumerate(rows):
        y = 175 + index * 82
        draw.text((72, y), left, font=_font(29), fill=(47, 56, 64))
        right_box = draw.textbbox((0, 0), right, font=_font(29))
        draw.text((628 - (right_box[2] - right_box[0]), y), right, font=_font(29), fill=(213, 60, 53))
    draw.line((72, 590, 628, 590), fill=(24, 45, 62), width=3)
    draw.text((72, 615), "ILLUSTRATIVE METAPHOR", font=_font(21), fill=(84, 91, 96))
    image.save(path)
    return path


def _prepare_graphics(output_dir: Path) -> dict[str, Path]:
    graphics = output_dir / "assets" / "graphics"
    graphics.mkdir(parents=True, exist_ok=True)
    paths = {
        "lower_vignette": _build_lower_vignette(graphics / "lower-vignette.png"),
        "bls_identity": _build_bls_identity_card(graphics / "bls-identity-card.png"),
        "basket_overlay": _build_basket_overlay(graphics / "basket-overlay.png"),
        "actual_forecast": _build_actual_forecast_card(graphics / "actual-forecast.png"),
        "energy": _build_energy_card(graphics / "bls-energy-card.jpg"),
        "shelter": _build_shelter_ring(graphics / "shelter-ring.png"),
        "cnbc": _build_cnbc_card(
            output_dir / "source-captures" / "cnbc-dollar-cpi-browser.png",
            graphics / "cnbc-headline-card.png",
        ),
        "question": _build_question_plate(graphics / "question-plate.png"),
        "positioning": _build_label_card(
            graphics / "factor-positioning.png",
            "POSITIONING",
            (255, 196, 72),
        ),
        "rates": _build_label_card(
            graphics / "factor-rate-expectations.png",
            "RATE EXPECTATIONS",
            (91, 225, 255),
        ),
        "risks": _build_label_card(
            graphics / "factor-other-risks.png",
            "OTHER RISKS",
            (255, 104, 91),
        ),
        "safeguards": _build_safeguards(graphics / "robot-safeguards.png"),
        "full_bill": _build_full_bill(graphics / "full-bill.png"),
    }
    return paths


def _prepare_audio_assets(output_dir: Path) -> list[AssetRef]:
    audio_dir = output_dir / "assets" / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    music = _copy_required(_DEFAULT_MUSIC, audio_dir / _DEFAULT_MUSIC.name)
    generated = {
        "sfx-impact": (
            audio_dir / "impact.wav",
            _impact(low_start_hz=112, duration=0.55, seed=8131),
        ),
        "sfx-impact-soft": (
            audio_dir / "impact-soft.wav",
            _impact(low_start_hz=164, duration=0.38, seed=8132),
        ),
        "sfx-whoosh": (
            audio_dir / "whoosh.wav",
            _whoosh(duration=0.48, reverse=False, seed=8133),
        ),
        "sfx-reverse": (
            audio_dir / "reverse-whoosh.wav",
            _whoosh(duration=0.44, reverse=True, seed=8134),
        ),
        "sfx-click": (
            audio_dir / "click.wav",
            _click(frequency_hz=1250, duration=0.10),
        ),
        "sfx-pop": (
            audio_dir / "pop.wav",
            _click(frequency_hz=1780, duration=0.12),
        ),
        "sfx-snap": (
            audio_dir / "snap.wav",
            _label_snap(),
        ),
        "sfx-paper": (
            audio_dir / "paper.wav",
            _paper_scroll(),
        ),
        "sfx-riser": (
            audio_dir / "riser.wav",
            _tension_riser(),
        ),
        "sfx-drop": (
            audio_dir / "drop.wav",
            _tonal_drop(duration=0.62, start_hz=660, end_hz=108),
        ),
    }
    assets = [
        AssetRef(
            id="music-social-kinetic",
            kind="audio",
            path=_relative(output_dir, music),
            keywords=["126 BPM", "electronic", "vocal-free"],
            provenance="internet:licensed-stock-audio",
            license="Mixkit Free License",
            provider="Mixkit",
            remote_id="162",
            creator="Alejandro Magaña (A. M.)",
            source_url="https://mixkit.co/free-stock-music/tag/technology/",
            license_url="https://mixkit.co/license/",
            search_query="minimal techno technology music",
        )
    ]
    for asset_id, (path, samples) in generated.items():
        _write_wav(path, samples)
        assets.append(
            AssetRef(
                id=asset_id,
                kind="audio",
                path=_relative(output_dir, path),
                keywords=["semantic sound effect", asset_id],
                provenance="generated-original",
                license="Original procedural audio",
                provider="Cutline local synthesis",
            )
        )
    return assets


def _load_transcript(output_dir: Path) -> list[TranscriptSegment]:
    payload = json.loads(
        (output_dir / "analysis" / "transcript-deepgram.json").read_text(
            encoding="utf-8"
        )
    )
    words = [
        TranscriptWord(
            start=float(item["start"]),
            end=float(item["end"]),
            text=str(item["word"]).strip(),
            confidence=item.get("confidence"),
        )
        for item in payload["words"]
        if str(item.get("word", "")).strip()
    ]
    if len(words) < 150:
        raise ValueError("0813 transcript is incomplete")
    ranges = [
        (0, 12),
        (13, 25),
        (26, 38),
        (39, 47),
        (48, 60),
        (61, 69),
        (70, 95),
        (96, 106),
        (107, 120),
        (121, 131),
        (132, 138),
        (139, 151),
    ]
    segments: list[TranscriptSegment] = []
    for start_index, end_index in ranges:
        selected = words[start_index : end_index + 1]
        segments.append(
            TranscriptSegment(
                start=selected[0].start,
                end=selected[-1].end,
                text=" ".join(word.text for word in selected),
                words=selected,
            )
        )
    return segments


def _safe_sfx_start(
    *,
    desired_ms: int,
    duration_ms: int,
    windows: list[SpeechProtectionWindow],
) -> int:
    offsets = [0]
    for delta in range(10, 1_201, 10):
        offsets.extend((-delta, delta))
    for offset in offsets:
        candidate = max(
            0,
            min(OUTPUT_DURATION_MS - duration_ms, desired_ms + offset),
        )
        if not any(
            candidate < window.end_ms
            and candidate + duration_ms > window.start_ms
            for window in windows
        ):
            return candidate
    raise ValueError(f"No speech-safe SFX window near {desired_ms} ms")


def _build_audio_plan(segments: list[TranscriptSegment]) -> AudioPlan:
    windows = [
        SpeechProtectionWindow(
            start_ms=max(0, round(word.start * 1000) - 100),
            end_ms=min(OUTPUT_DURATION_MS, round(word.start * 1000) + 120),
            word=word.text,
        )
        for segment in segments
        for word in segment.words
        if round(word.start * 1000) < OUTPUT_DURATION_MS
    ]
    planned = [
        ("hook-settle", "sfx-impact-soft", 220, 220, -17, "impact", "hook settle"),
        ("petrol-card", "sfx-click", 620, 90, -18, "click", "petrol card"),
        ("rent-card", "sfx-snap", 1_700, 100, -17, "click", "rent card"),
        ("cpi-date", "sfx-impact-soft", 3_420, 220, -17, "impact", "CPI date"),
        ("basket-cut", "sfx-whoosh", 6_900, 320, -18, "whoosh", "basket transition"),
        ("basket-chips", "sfx-click", 9_500, 90, -19, "click", "basket labels"),
        ("monthly-number", "sfx-impact", 11_430, 260, -16, "impact", "0.1 reveal"),
        ("yearly-number", "sfx-impact-soft", 13_350, 220, -16, "impact", "3.4 reveal"),
        ("forecast-lock", "sfx-click", 15_220, 90, -18, "click", "equality lock"),
        ("story-open", "sfx-reverse", 17_250, 300, -18, "whoosh", "inside story"),
        ("energy-down", "sfx-drop", 18_780, 360, -17, "impact", "energy decline"),
        ("gas-proof", "sfx-click", 21_050, 90, -18, "click", "gasoline proof"),
        ("rent-cut", "sfx-whoosh", 22_650, 280, -18, "whoosh", "shelter context"),
        ("shelter-share", "sfx-impact", 25_650, 260, -16, "impact", "two-thirds"),
        ("dollar-cut", "sfx-paper", 28_120, 300, -19, "whoosh", "CNBC evidence"),
        ("question", "sfx-impact", 30_260, 280, -15, "impact", "question interrupt"),
        ("factor-a", "sfx-click", 33_250, 90, -19, "click", "positioning"),
        ("factor-b", "sfx-click", 34_650, 90, -19, "click", "rates"),
        ("factor-c", "sfx-click", 36_000, 90, -19, "click", "risks"),
        ("safeguards", "sfx-riser", 38_650, 520, -20, "riser", "risk controls"),
        ("full-bill", "sfx-paper", 42_550, 320, -18, "whoosh", "full bill"),
        ("follow", "sfx-pop", 44_100, 100, -16, "notification", "CTA"),
    ]
    cues: list[SfxCue] = []
    for (
            cue_id,
            asset_id,
            desired_ms,
            duration_ms,
            gain_db,
            kind,
            reason,
        ) in planned:
        effective_duration_ms = min(duration_ms, 100)
        cues.append(
            SfxCue(
                id=cue_id,
                asset_id=asset_id,
                start_ms=_safe_sfx_start(
                    desired_ms=desired_ms,
                    duration_ms=effective_duration_ms,
                    windows=windows,
                ),
                duration_ms=effective_duration_ms,
                volume=0.35,
                gain_db=gain_db,
                kind=kind,
                reason=reason,
            )
        )
    automation = [
        GainAutomation(
            start_ms=max(0, round(segment.start * 1000) - 80),
            end_ms=min(OUTPUT_DURATION_MS, round(segment.end * 1000) + 120),
            gain_db=-6,
            reason="Duck music beneath narration",
        )
        for segment in segments
        if round(segment.start * 1000) < OUTPUT_DURATION_MS
    ]
    return AudioPlan(
        integrated_lufs=-13.5,
        true_peak_dbtp=-1.0,
        target_lra_lu=2.4,
        music_bpm=126,
        dialogue_asset_id="dialogue-processed",
        dialogue_offset_ms=0,
        music_asset_id="music-social-kinetic",
        music_duck_db=6,
        music_base_gain_db=-23,
        music_gain_automation=automation,
        speech_protection_windows=windows,
        sfx_asset_ids=sorted({cue.asset_id for cue in cues}),
        sfx_cues=cues,
    )


def _layer(
    *,
    layer_id: str,
    shot_id: str,
    start_ms: int,
    end_ms: int,
    source_role: str,
    asset_id: str,
    kind: str = "video",
    source_start_ms: int | None = None,
    source_end_ms: int | None = None,
    bounds: tuple[int, int, int, int] = (0, 0, 1080, 1920),
    fit: str = "cover",
    start_scale: float = 1,
    end_scale: float = 1,
    start_x: float = 0,
    end_x: float = 0,
    start_y: float = 0,
    end_y: float = 0,
    brightness: float = 1,
    contrast: float = 1,
    saturation: float = 1,
    opacity_keyframes: list[OpacityKeyframe] | None = None,
    z_index: int = 10,
    border_radius: int = 0,
    blend_mode: str = "normal",
) -> BlueprintLayerSpec:
    duration = end_ms - start_ms
    x, y, width, height = bounds
    return BlueprintLayerSpec(
        id=layer_id,
        shot_id=shot_id,
        start_ms=start_ms,
        end_ms=end_ms,
        source_role=source_role,
        kind=kind,
        asset_id=asset_id,
        source_start_ms=source_start_ms,
        source_end_ms=source_end_ms,
        bounds=LayerBounds(x=x, y=y, width=width, height=height),
        fit=fit,
        transform_keyframes=[
            TransformKeyframe(
                at_ms=0,
                x=start_x,
                y=start_y,
                scale=start_scale,
            ),
            TransformKeyframe(
                at_ms=duration,
                x=end_x,
                y=end_y,
                scale=end_scale,
            ),
        ],
        opacity_keyframes=opacity_keyframes
        or [OpacityKeyframe(at_ms=0, value=1)],
        effect_keyframes=[
            EffectKeyframe(
                at_ms=0,
                brightness=brightness,
                contrast=contrast,
                saturation=saturation,
            )
        ],
        blend_mode=blend_mode,
        z_index=z_index,
        muted=True,
        border_radius=border_radius,
        reference_role="primary-human",
    )


def _presenter(
    *,
    layer_id: str,
    shot_id: str,
    start_ms: int,
    end_ms: int,
    start_scale: float,
    end_scale: float,
) -> BlueprintLayerSpec:
    return _layer(
        layer_id=layer_id,
        shot_id=shot_id,
        start_ms=start_ms,
        end_ms=end_ms,
        source_role="presenter",
        asset_id="presenter-edl",
        source_start_ms=start_ms,
        source_end_ms=end_ms,
        start_scale=start_scale,
        end_scale=end_scale,
        brightness=0.79,
        contrast=1.08,
        saturation=1.48,
    )


def _build_layers() -> list[BlueprintLayerSpec]:
    layers = [
        _presenter(
            layer_id="presenter-hook",
            shot_id="shot-01",
            start_ms=0,
            end_ms=3_220,
            start_scale=1.02,
            end_scale=1.07,
        ),
        _layer(
            layer_id="hook-vignette",
            shot_id="shot-01",
            start_ms=0,
            end_ms=2_980,
            source_role="deterministic-graphic",
            asset_id="graphic-lower-vignette",
            kind="image",
            fit="fill",
            z_index=18,
        ),
        _layer(
            layer_id="hook-fuel-pip",
            shot_id="shot-01",
            start_ms=540,
            end_ms=1_650,
            source_role="licensed-context",
            asset_id="licensed-fuel-nozzle",
            source_start_ms=5_900,
            source_end_ms=7_010,
            bounds=(65, 1_050, 450, 500),
            start_scale=0.92,
            end_scale=1.03,
            brightness=1.03,
            contrast=1.07,
            saturation=1.08,
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=130, value=1),
            ],
            border_radius=34,
            z_index=25,
        ),
        _layer(
            layer_id="hook-rent-pip",
            shot_id="shot-01",
            start_ms=1_620,
            end_ms=3_080,
            source_role="licensed-context",
            asset_id="licensed-rent-keys",
            source_start_ms=450,
            source_end_ms=1_910,
            bounds=(565, 1_050, 450, 500),
            start_scale=0.92,
            end_scale=1.04,
            brightness=1.02,
            contrast=1.06,
            saturation=1.1,
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=130, value=1),
            ],
            border_radius=34,
            z_index=25,
        ),
        _presenter(
            layer_id="presenter-date",
            shot_id="shot-02",
            start_ms=3_220,
            end_ms=7_007,
            start_scale=1,
            end_scale=1.04,
        ),
        _layer(
            layer_id="bls-identity-pip",
            shot_id="shot-02",
            start_ms=3_520,
            end_ms=6_420,
            source_role="direct-evidence",
            asset_id="graphic-bls-identity",
            kind="image",
            bounds=(190, 1_070, 700, 560),
            fit="fill",
            start_y=24,
            end_y=0,
            start_scale=0.94,
            end_scale=1.02,
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=180, value=1),
            ],
            border_radius=38,
            z_index=25,
        ),
        _layer(
            layer_id="shopping-wide",
            shot_id="shot-03",
            start_ms=7_007,
            end_ms=9_200,
            source_role="licensed-context",
            asset_id="licensed-shopping-cart",
            source_start_ms=700,
            source_end_ms=2_893,
            start_scale=1.02,
            end_scale=1.08,
            brightness=0.97,
            contrast=1.04,
            saturation=0.92,
        ),
        _layer(
            layer_id="shopping-components",
            shot_id="shot-04",
            start_ms=9_200,
            end_ms=11_288,
            source_role="licensed-context",
            asset_id="licensed-shopping-cart",
            source_start_ms=3_100,
            source_end_ms=5_188,
            start_scale=1.08,
            end_scale=1.16,
            start_x=-18,
            end_x=18,
            brightness=0.97,
            contrast=1.06,
            saturation=0.94,
        ),
        _layer(
            layer_id="basket-overlay",
            shot_id="shot-04",
            start_ms=9_420,
            end_ms=11_288,
            source_role="deterministic-graphic",
            asset_id="graphic-basket-overlay",
            kind="image",
            fit="fill",
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=160, value=1),
            ],
            z_index=22,
        ),
        _presenter(
            layer_id="presenter-monthly",
            shot_id="shot-05",
            start_ms=11_288,
            end_ms=13_200,
            start_scale=1.12,
            end_scale=1.16,
        ),
        _layer(
            layer_id="number-vignette-monthly",
            shot_id="shot-05",
            start_ms=11_288,
            end_ms=13_200,
            source_role="deterministic-graphic",
            asset_id="graphic-lower-vignette",
            kind="image",
            fit="fill",
            z_index=18,
        ),
        _presenter(
            layer_id="presenter-yearly",
            shot_id="shot-06",
            start_ms=13_200,
            end_ms=15_031,
            start_scale=1.02,
            end_scale=1.08,
        ),
        _layer(
            layer_id="number-vignette-yearly",
            shot_id="shot-06",
            start_ms=13_200,
            end_ms=15_031,
            source_role="deterministic-graphic",
            asset_id="graphic-lower-vignette",
            kind="image",
            fit="fill",
            z_index=18,
        ),
        _presenter(
            layer_id="presenter-forecast",
            shot_id="shot-07",
            start_ms=15_031,
            end_ms=18_700,
            start_scale=1,
            end_scale=1.045,
        ),
        _layer(
            layer_id="actual-forecast-card",
            shot_id="shot-07",
            start_ms=15_230,
            end_ms=18_130,
            source_role="deterministic-graphic",
            asset_id="graphic-actual-forecast",
            kind="image",
            fit="fill",
            start_y=30,
            end_y=0,
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=160, value=1),
            ],
            z_index=24,
        ),
        _layer(
            layer_id="energy-action",
            shot_id="shot-08",
            start_ms=18_700,
            end_ms=20_900,
            source_role="licensed-context",
            asset_id="licensed-fuel-nozzle",
            source_start_ms=6_200,
            source_end_ms=8_400,
            start_scale=1.04,
            end_scale=1.13,
            start_x=16,
            end_x=-18,
            brightness=1.04,
            contrast=1.09,
            saturation=1.05,
        ),
        _presenter(
            layer_id="presenter-gas-proof",
            shot_id="shot-09",
            start_ms=20_900,
            end_ms=22_694,
            start_scale=1.0,
            end_scale=1.035,
        ),
        _layer(
            layer_id="bls-energy-proof",
            shot_id="shot-09",
            start_ms=20_900,
            end_ms=22_694,
            source_role="direct-evidence",
            asset_id="graphic-bls-energy",
            kind="image",
            bounds=(90, 160, 900, 1_600),
            fit="fill",
            start_scale=1,
            end_scale=1.045,
            brightness=1.02,
            contrast=1.03,
            saturation=1,
            border_radius=38,
            z_index=24,
        ),
        _layer(
            layer_id="rent-context",
            shot_id="shot-10",
            start_ms=22_694,
            end_ms=25_400,
            source_role="licensed-context",
            asset_id="licensed-rent-keys",
            source_start_ms=550,
            source_end_ms=3_256,
            start_scale=1.02,
            end_scale=1.11,
            start_x=-10,
            end_x=14,
            brightness=1.02,
            contrast=1.07,
            saturation=1.08,
        ),
        _presenter(
            layer_id="presenter-shelter",
            shot_id="shot-11",
            start_ms=25_400,
            end_ms=27_979,
            start_scale=1.03,
            end_scale=1.075,
        ),
        _layer(
            layer_id="shelter-ring",
            shot_id="shot-11",
            start_ms=25_560,
            end_ms=27_900,
            source_role="direct-evidence",
            asset_id="graphic-shelter-ring",
            kind="image",
            bounds=(100, 1_020, 880, 760),
            fit="fill",
            start_y=28,
            end_y=0,
            start_scale=0.95,
            end_scale=1.03,
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=180, value=1),
            ],
            border_radius=42,
            z_index=25,
        ),
        _layer(
            layer_id="dollar-context",
            shot_id="shot-12",
            start_ms=27_979,
            end_ms=30_300,
            source_role="licensed-context",
            asset_id="licensed-usd-counting",
            source_start_ms=800,
            source_end_ms=3_121,
            start_scale=1.03,
            end_scale=1.12,
            start_x=14,
            end_x=-16,
            brightness=1.08,
            contrast=1.09,
            saturation=0.86,
        ),
        _layer(
            layer_id="cnbc-source-card",
            shot_id="shot-12",
            start_ms=28_240,
            end_ms=30_260,
            source_role="direct-evidence",
            asset_id="evidence-cnbc-dollar",
            kind="image",
            fit="fill",
            start_y=26,
            end_y=0,
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=170, value=1),
            ],
            z_index=24,
        ),
        _layer(
            layer_id="question-plate",
            shot_id="shot-13",
            start_ms=30_300,
            end_ms=31_550,
            source_role="deterministic-graphic",
            asset_id="graphic-question-plate",
            kind="image",
            fit="fill",
            start_scale=1.03,
            end_scale=1.12,
            brightness=1.02,
            contrast=1.05,
            saturation=1.02,
        ),
        _presenter(
            layer_id="presenter-question-reset",
            shot_id="shot-13",
            start_ms=31_550,
            end_ms=33_000,
            start_scale=1.09,
            end_scale=1.03,
        ),
        _presenter(
            layer_id="presenter-factors",
            shot_id="shot-14",
            start_ms=33_000,
            end_ms=37_161,
            start_scale=1.02,
            end_scale=1.08,
        ),
        _layer(
            layer_id="factor-positioning",
            shot_id="shot-14",
            start_ms=33_100,
            end_ms=34_420,
            source_role="deterministic-graphic",
            asset_id="graphic-factor-positioning",
            kind="image",
            bounds=(160, 1_170, 760, 200),
            fit="fill",
            start_x=-40,
            end_x=0,
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=140, value=1),
            ],
            z_index=24,
        ),
        _layer(
            layer_id="factor-rates",
            shot_id="shot-14",
            start_ms=34_420,
            end_ms=35_810,
            source_role="deterministic-graphic",
            asset_id="graphic-factor-rates",
            kind="image",
            bounds=(160, 1_170, 760, 200),
            fit="fill",
            start_x=40,
            end_x=0,
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=140, value=1),
            ],
            z_index=24,
        ),
        _layer(
            layer_id="factor-risks",
            shot_id="shot-14",
            start_ms=35_810,
            end_ms=37_100,
            source_role="deterministic-graphic",
            asset_id="graphic-factor-risks",
            kind="image",
            bounds=(160, 1_170, 760, 200),
            fit="fill",
            start_x=-40,
            end_x=0,
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=140, value=1),
            ],
            z_index=24,
        ),
        _presenter(
            layer_id="presenter-controls",
            shot_id="shot-15",
            start_ms=37_161,
            end_ms=42_500,
            start_scale=1.08,
            end_scale=1.03,
        ),
        _layer(
            layer_id="safeguards",
            shot_id="shot-15",
            start_ms=38_420,
            end_ms=41_320,
            source_role="deterministic-graphic",
            asset_id="graphic-safeguards",
            kind="image",
            fit="fill",
            start_y=24,
            end_y=0,
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=180, value=1),
            ],
            z_index=24,
        ),
        _presenter(
            layer_id="presenter-cta",
            shot_id="shot-16",
            start_ms=42_500,
            end_ms=OUTPUT_DURATION_MS,
            start_scale=1.03,
            end_scale=1.08,
        ),
        _layer(
            layer_id="full-bill",
            shot_id="shot-16",
            start_ms=42_520,
            end_ms=44_080,
            source_role="deterministic-graphic",
            asset_id="graphic-full-bill",
            kind="image",
            bounds=(190, 1_010, 700, 730),
            fit="fill",
            start_y=30,
            end_y=0,
            start_scale=0.94,
            end_scale=1.02,
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=160, value=1),
                OpacityKeyframe(at_ms=1_330, value=1),
                OpacityKeyframe(at_ms=1_560, value=0),
            ],
            border_radius=34,
            z_index=24,
        ),
        _layer(
            layer_id="cta-logo",
            shot_id="shot-16",
            start_ms=43_900,
            end_ms=45_350,
            source_role="deterministic-graphic",
            asset_id="brand-logo-original",
            kind="image",
            bounds=(365, 1_120, 350, 230),
            fit="contain",
            start_scale=0.84,
            end_scale=1,
            opacity_keyframes=[
                OpacityKeyframe(at_ms=0, value=0),
                OpacityKeyframe(at_ms=150, value=1),
            ],
            z_index=25,
        ),
    ]
    return layers


def _build_text_cues() -> list[KineticTextCue]:
    return [
        KineticTextCue(
            id="text-petrol-down",
            start_ms=420,
            end_ms=1_450,
            text="PETROL DOWN",
            family="hero-condensed",
            x=540,
            y=1_650,
            max_width=920,
            animation="slam",
        ),
        KineticTextCue(
            id="text-rent-up",
            start_ms=1_620,
            end_ms=3_100,
            text="RENT STILL UP",
            family="outlined-stack",
            x=540,
            y=1_660,
            max_width=940,
            animation="stack",
        ),
        KineticTextCue(
            id="text-monthly",
            start_ms=11_430,
            end_ms=12_650,
            text="0.1% MoM",
            family="gradient-number",
            x=540,
            y=1_350,
            max_width=940,
            animation="glow",
        ),
        KineticTextCue(
            id="text-yearly",
            start_ms=13_350,
            end_ms=14_550,
            text="3.4% YoY",
            family="gradient-number",
            x=540,
            y=1_350,
            max_width=940,
            animation="glow",
        ),
        KineticTextCue(
            id="text-actual-forecast",
            start_ms=15_250,
            end_ms=16_380,
            text="ACTUAL = FORECAST",
            family="outlined-stack",
            x=540,
            y=1_610,
            max_width=940,
            animation="stack",
            z_index=62,
        ),
        KineticTextCue(
            id="text-shelter-share",
            start_ms=25_700,
            end_ms=26_900,
            text="~2/3 SHELTER",
            family="gradient-number",
            x=540,
            y=1_720,
            max_width=920,
            animation="glow",
            z_index=62,
        ),
        KineticTextCue(
            id="text-surprise-zero",
            start_ms=30_520,
            end_ms=31_720,
            text="SURPRISE = 0?",
            family="correction-symbol",
            x=540,
            y=1_430,
            max_width=940,
            animation="draw",
        ),
        KineticTextCue(
            id="text-full-bill",
            start_ms=42_620,
            end_ms=43_350,
            text="FULL BILL",
            family="cyan-secondary",
            x=540,
            y=1_760,
            max_width=760,
            animation="rise",
            z_index=62,
        ),
        KineticTextCue(
            id="text-follow",
            start_ms=44_100,
            end_ms=45_160,
            text="FOLLOW",
            family="cta-quote",
            x=540,
            y=1_560,
            max_width=800,
            animation="quote-pop",
            z_index=62,
        ),
    ]


def _build_motion_events() -> list[MotionEventSpec]:
    specs = [
        ("m01", 180, 700, "punch-crop", "presenter-hook", 0.45, "none"),
        ("m02", 540, 900, "pip-pop", "hook-fuel-pip", 0.72, "up"),
        ("m03", 1_620, 2_000, "pip-pop", "hook-rent-pip", 0.72, "up"),
        ("m04", 3_220, 3_760, "punch-crop", "presenter-date", 0.45, "none"),
        ("m05", 3_520, 4_000, "pip-pop", "bls-identity-pip", 0.7, "up"),
        ("m06", 7_007, 7_620, "directional-jump", "shopping-wide", 0.35, "left"),
        ("m07", 8_400, 9_150, "punch-crop", "shopping-wide", 0.35, "none"),
        ("m08", 9_200, 9_780, "directional-jump", "shopping-components", 0.32, "right"),
        ("m09", 9_420, 10_000, "highlight-sweep", "basket-overlay", 0.6, "none"),
        ("m10", 11_288, 11_900, "punch-crop", "presenter-monthly", 0.52, "none"),
        ("m11", 11_430, 12_050, "text-reveal", "text-monthly", 0.7, "none"),
        ("m12", 13_200, 13_800, "punch-crop", "presenter-yearly", 0.52, "none"),
        ("m13", 13_350, 13_950, "text-reveal", "text-yearly", 0.7, "none"),
        ("m14", 15_230, 15_850, "pip-pop", "actual-forecast-card", 0.62, "up"),
        ("m15", 17_250, 18_200, "highlight-sweep", "actual-forecast-card", 0.55, "none"),
        ("m16", 18_700, 19_400, "directional-jump", "energy-action", 0.35, "left"),
        ("m17", 20_900, 21_520, "proof-punch", "bls-energy-proof", 0.65, "none"),
        ("m18", 22_694, 23_350, "directional-jump", "rent-context", 0.35, "right"),
        ("m19", 25_560, 26_200, "pip-pop", "shelter-ring", 0.7, "up"),
        ("m20", 25_700, 26_250, "text-reveal", "text-shelter-share", 0.7, "none"),
        ("m21", 27_979, 28_620, "directional-jump", "dollar-context", 0.32, "left"),
        ("m22", 28_240, 28_850, "proof-punch", "cnbc-source-card", 0.65, "none"),
        ("m23", 30_300, 31_300, "question-pulse", "question-plate", 0.82, "none"),
        ("m24", 33_100, 33_680, "pip-pop", "factor-positioning", 0.62, "left"),
        ("m25", 34_420, 35_000, "pip-pop", "factor-rates", 0.62, "right"),
        ("m26", 35_810, 36_390, "pip-pop", "factor-risks", 0.62, "left"),
        ("m27", 37_161, 37_900, "punch-crop", "presenter-controls", 0.5, "none"),
        ("m28", 38_420, 39_150, "pip-pop", "safeguards", 0.7, "up"),
        ("m29", 40_000, 41_300, "highlight-sweep", "safeguards", 0.56, "none"),
        ("m30", 42_520, 43_200, "pip-pop", "full-bill", 0.72, "up"),
        ("m31", 43_900, 44_450, "logo-build", "cta-logo", 0.7, "none"),
        ("m32", 44_100, 44_700, "text-reveal", "text-follow", 0.74, "none"),
    ]
    return [
        MotionEventSpec(
            id=identifier,
            start_ms=start,
            end_ms=end,
            kind=kind,
            target_id=target,
            intensity=intensity,
            direction=direction,
        )
        for identifier, start, end, kind, target, intensity, direction in specs
    ]


def _build_evidence() -> list[EvidenceItem]:
    accessed = datetime(2026, 8, 13, tzinfo=UTC)
    published = datetime(2026, 8, 12, tzinfo=UTC)
    bls_url = "https://www.bls.gov/news.release/archives/cpi_08122026.htm"
    reuters_url = (
        "https://www.reuters.com/world/us/"
        "us-consumer-prices-rise-less-than-expected-july-2026-08-12/"
    )
    cnbc_url = (
        "https://www.cnbc.com/2026/08/12/"
        "dollar-ticks-up-on-iran-tensions-with-us-data-in-focus.html"
    )
    return [
        EvidenceItem(
            id="bls-cpi-monthly",
            claim="The U.S. all-items CPI rose 0.1% in July 2026.",
            source_title="Consumer Price Index - July 2026",
            source_url=bls_url,
            source_type="official",
            capture_path="assets/graphics/bls-identity-card.png",
            accessed_at=accessed,
            published_at=published,
            status="verified",
            visible_excerpt="0.1 percent in July on a seasonally adjusted basis",
            license="Official public data used as editorial evidence",
            notes="Visible treatment is a clearly labelled data card, not a reconstructed source document.",
        ),
        EvidenceItem(
            id="bls-cpi-yearly",
            claim="The U.S. all-items CPI rose 3.4% over the 12 months ending July 2026.",
            source_title="Consumer Price Index - July 2026",
            source_url=bls_url,
            source_type="official",
            capture_path="assets/graphics/bls-identity-card.png",
            accessed_at=accessed,
            published_at=published,
            status="verified",
            visible_excerpt="3.4 percent over the last 12 months",
            license="Official public data used as editorial evidence",
        ),
        EvidenceItem(
            id="bls-energy-gasoline",
            claim="Energy fell 1.5% and gasoline fell 2.9% in July 2026.",
            source_title="Consumer Price Index - July 2026",
            source_url=bls_url,
            source_type="official",
            capture_path="assets/graphics/bls-energy-card.jpg",
            accessed_at=accessed,
            published_at=published,
            status="verified",
            visible_excerpt="energy index decreased 1.5 percent; gasoline fell 2.9 percent",
            license="Official public data used as editorial evidence",
        ),
        EvidenceItem(
            id="reuters-shelter-share",
            claim="Shelter accounted for nearly two-thirds of the monthly CPI increase.",
            source_title="U.S. consumer prices rise less than expected in July",
            source_url=reuters_url,
            source_type="editorial",
            capture_path="assets/graphics/shelter-ring.png",
            accessed_at=accessed,
            published_at=published,
            status="verified",
            visible_excerpt="nearly two-thirds of the increase",
            license="Editorial reporting used with attribution",
        ),
        EvidenceItem(
            id="cnbc-dollar-gained",
            claim="The dollar gained as U.S. CPI met expectations on August 12, 2026.",
            source_title="Dollar gains, yen slips as U.S. CPI meets expectations",
            source_url=cnbc_url,
            source_type="editorial",
            capture_path="source-captures/cnbc-dollar-cpi-browser.png",
            accessed_at=accessed,
            published_at=published,
            status="verified",
            visible_excerpt="Dollar gains ... as U.S. CPI meets expectations",
            license="Editorial source pixels used for commentary",
        ),
    ]


def build_cpi_schedule() -> list[dict[str, Any]]:
    shots = [
        {
            "id": f"shot-{index:02d}",
            "start_ms": start,
            "end_ms": end,
            "source_role": source_role,
            "editorial_role": editorial_role,
            "reference_role": "primary-human",
        }
        for index, (
            start,
            end,
            source_role,
            editorial_role,
        ) in enumerate(_SHOT_SPECS, start=1)
    ]
    durations = [shot["end_ms"] - shot["start_ms"] for shot in shots]
    if not 2_300 <= median(durations) <= 3_000:
        raise ValueError("CPI schedule drifted from social-kinetic pacing")
    return shots


def _stock_assets(output_dir: Path) -> list[AssetRef]:
    manifest_path = output_dir / "analysis" / "selected-stock-assets.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    return [
        AssetRef(
            id=item["id"],
            kind="video",
            path=item["path"],
            keywords=[item["query"], "licensed moving context"],
            provenance="internet:licensed-stock-video",
            license=item["license"],
            provider=item["provider"],
            remote_id=item["remote_id"],
            creator=item["creator"],
            source_url=item["source_url"],
            license_url=item["license_url"],
            search_query=item["query"],
        )
        for item in payload
    ]


def build_cpi_blueprint(
    *,
    source: Path,
    output_dir: Path,
    style_reference: Path | None = None,
    flow_operation_budget: int = 0,
) -> dict[str, str]:
    source = source.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    style_reference = (
        style_reference.expanduser().resolve()
        if style_reference is not None
        else _DEFAULT_STYLE_REFERENCE
    )
    if not source.is_file():
        raise FileNotFoundError(source)
    if not style_reference.is_file():
        raise FileNotFoundError(style_reference)
    if flow_operation_budget != 0:
        raise ValueError("The CPI profile intentionally disables Flow")
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = probe_video(source)
    source_duration_ms = round(metadata.duration_seconds * 1000)
    silence_intervals = _detect_silence_intervals(source)
    edl = build_dialogue_edl_from_silences(
        source_duration_ms=source_duration_ms,
        target_duration_ms=OUTPUT_DURATION_MS,
        silence_intervals_ms=silence_intervals,
        minimum_retained_silence_ms=95,
    )

    presenter = output_dir / "assets" / "presenter" / "presenter-edl.mp4"
    dialogue_original = output_dir / "assets" / "audio" / "dialogue-original.wav"
    dialogue_processed = output_dir / "assets" / "audio" / "dialogue-processed.wav"
    _prepare_dialogue_media(
        source=source,
        edl=edl,
        presenter_output=presenter,
        original_audio_output=dialogue_original,
        processed_audio_output=dialogue_processed,
    )

    source_segments = _load_transcript(output_dir)
    remapped_segments = _remap_transcript(
        source_segments,
        edl,
        target_duration_ms=OUTPUT_DURATION_MS,
    )
    _write_json(
        output_dir / "transcript-aligned.json",
        [segment.model_dump(mode="json") for segment in remapped_segments],
    )

    graphics = _prepare_graphics(output_dir)
    logo = _copy_logo_without_background(
        _DEFAULT_LOGO,
        output_dir / "assets" / "brand" / "profit-bricks-logo.png",
    )
    evidence = _build_evidence()
    audio = _build_audio_plan(remapped_segments)
    layers = _build_layers()
    text_cues = _build_text_cues()
    motion_events = _build_motion_events()

    assets: list[AssetRef] = [
        AssetRef(
            id="presenter-edl",
            kind="video",
            path=_relative(output_dir, presenter),
            keywords=["presenter", "dialogue EDL", "source footage"],
            provenance="user-provided-edl-preserved",
            license="User-provided source footage",
        ),
        AssetRef(
            id="dialogue-original",
            kind="audio",
            path=_relative(output_dir, dialogue_original),
            keywords=["EDL dialogue baseline", "48 kHz"],
            provenance="source-dialogue-edl-master",
            license="User-provided source audio",
        ),
        AssetRef(
            id="dialogue-processed",
            kind="audio",
            path=_relative(output_dir, dialogue_processed),
            keywords=["processed dialogue", "48 kHz"],
            provenance="source-dialogue-edl-processed",
            license="User-provided source audio",
        ),
        AssetRef(
            id="brand-logo-original",
            kind="image",
            path=_relative(output_dir, logo),
            keywords=["Profit Bricks", "brand"],
            provenance="user-provided-brand-asset",
            license="User-provided",
        ),
    ]
    graphic_specs = {
        "graphic-lower-vignette": ("lower_vignette", "deterministic-original-graphic"),
        "graphic-bls-identity": ("bls_identity", "generated-from-verified-facts"),
        "graphic-basket-overlay": ("basket_overlay", "deterministic-original-graphic"),
        "graphic-actual-forecast": ("actual_forecast", "generated-from-verified-facts"),
        "graphic-bls-energy": ("energy", "generated-from-verified-facts"),
        "graphic-shelter-ring": ("shelter", "generated-from-verified-facts"),
        "evidence-cnbc-dollar": ("cnbc", "editorial-source-capture-derived-card"),
        "graphic-question-plate": ("question", "deterministic-original-graphic"),
        "graphic-factor-positioning": ("positioning", "deterministic-original-graphic"),
        "graphic-factor-rates": ("rates", "deterministic-original-graphic"),
        "graphic-factor-risks": ("risks", "deterministic-original-graphic"),
        "graphic-safeguards": ("safeguards", "deterministic-original-graphic"),
        "graphic-full-bill": ("full_bill", "deterministic-original-graphic"),
    }
    for asset_id, (key, provenance) in graphic_specs.items():
        assets.append(
            AssetRef(
                id=asset_id,
                kind="image",
                path=_relative(output_dir, graphics[key]),
                keywords=[asset_id.replace("-", " ")],
                provenance=provenance,
                license=(
                    "Editorial source pixels used for commentary"
                    if asset_id == "evidence-cnbc-dollar"
                    else "Original editorial graphic"
                ),
            )
        )
    assets.extend(_stock_assets(output_dir))
    assets.extend(_prepare_audio_assets(output_dir))

    blueprint = ProductionBlueprint(
        source_filename=source.name,
        source_metadata=metadata,
        output=OutputSpec(),
        duration_ms=OUTPUT_DURATION_MS,
        assets=assets,
        layers=layers,
        caption_pages=[],
        audio=audio,
        flow_shots=[],
        evidence=evidence,
        reference_profile="social-kinetic",
        story_profile="cpi-inflation",
        style_reference_path=str(style_reference),
        voice_policy="reference-compressed",
        dialogue_edl=edl,
        kinetic_text_cues=text_cues,
        motion_events=motion_events,
    )

    artifacts = {
        "blueprint": "blueprint.json",
        "storyboard": "storyboard.json",
        "evidence": "evidence.json",
        "reference_profile": "reference-profile.json",
        "dialogue_edl": "dialogue-edl.json",
        "kinetic_text_plan": "kinetic-text-plan.json",
        "motion_events": "motion-events.json",
        "sound_cue_sheet": "sound-cue-sheet.json",
        "flow_shot_plan": "flow-shot-plan.json",
        "flow_instructions": "flow-instructions.json",
        "asset_manifest": "asset-manifest.json",
        "capture_manifest": "capture-manifest.json",
        "caption_plan": "caption-plan.json",
        "production_settings": "production-settings.json",
        "transcript_aligned": "transcript-aligned.json",
    }
    _write_json(output_dir / "blueprint.json", blueprint.model_dump(mode="json"))
    _write_json(output_dir / "evidence.json", [item.model_dump(mode="json") for item in evidence])
    _write_json(
        output_dir / "dialogue-edl.json",
        {
            "source_duration_ms": source_duration_ms,
            "output_duration_ms": OUTPUT_DURATION_MS,
            "removed_ms": source_duration_ms - OUTPUT_DURATION_MS,
            "playback_rate_max": max(segment.playback_rate for segment in edl),
            "segments": [segment.model_dump(mode="json") for segment in edl],
        },
    )
    _write_json(
        output_dir / "kinetic-text-plan.json",
        {
            "profile": "social-kinetic",
            "continuous_captions": False,
            "semantic_text_visible_ms": measure_visible_interval_duration(text_cues),
            "semantic_text_ratio": round(
                measure_visible_interval_duration(text_cues) / OUTPUT_DURATION_MS,
                6,
            ),
            "cues": [cue.model_dump(mode="json") for cue in text_cues],
        },
    )
    _write_json(
        output_dir / "motion-events.json",
        [event.model_dump(mode="json") for event in motion_events],
    )
    _write_json(
        output_dir / "sound-cue-sheet.json",
        {
            "profile": "social-kinetic",
            "music_bpm": audio.music_bpm,
            "target_lufs": audio.integrated_lufs,
            "target_true_peak_dbtp": audio.true_peak_dbtp,
            "target_lra_lu": audio.target_lra_lu,
            "cues": [cue.model_dump(mode="json") for cue in audio.sfx_cues],
            "speech_protection_windows": [
                window.model_dump(mode="json")
                for window in audio.speech_protection_windows
            ],
        },
    )
    layer_ids_by_shot: dict[str, list[str]] = {}
    for layer in layers:
        layer_ids_by_shot.setdefault(layer.shot_id, []).append(layer.id)
    evidence_by_role = {
        "cpi-date-reveal": ["bls-cpi-monthly", "bls-cpi-yearly"],
        "monthly-number": ["bls-cpi-monthly"],
        "yearly-number": ["bls-cpi-yearly"],
        "energy-down-action": ["bls-energy-gasoline"],
        "gasoline-proof": ["bls-energy-gasoline"],
        "shelter-share": ["reuters-shelter-share"],
        "dollar-reaction": ["cnbc-dollar-gained"],
    }
    schedule = build_cpi_schedule()
    _write_json(
        output_dir / "storyboard.json",
        [
            {
                **shot,
                "layer_ids": layer_ids_by_shot.get(shot["id"], []),
                "kinetic_text_ids": [
                    cue.id
                    for cue in text_cues
                    if cue.start_ms < shot["end_ms"]
                    and cue.end_ms > shot["start_ms"]
                ],
                "evidence_ids": evidence_by_role.get(shot["editorial_role"], []),
            }
            for shot in schedule
        ],
    )
    _write_json(
        output_dir / "reference-profile.json",
        {
            "name": "social-kinetic",
            "story_profile": "cpi-inflation",
            "primary_reference": {
                "path": str(style_reference),
                "checksum_sha256": _sha256(style_reference),
                "role": "typography, pacing, color, motion and sound grammar",
            },
            "approved_golden": {
                "path": str(_DEFAULT_GOLDEN_DIR / "edited.mp4"),
                "checksum_sha256": _sha256(_DEFAULT_GOLDEN_DIR / "edited.mp4"),
            },
            "secondary_reference": {
                "training_reference": 10,
                "role": "factual evidence restraint only",
            },
            "targets": {
                "duration_seconds": [45.4, 45.7],
                "hard_cuts": [13, 16],
                "median_shot_seconds": [2.3, 3.0],
                "presenter_ratio": [0.58, 0.68],
                "flow_ratio_max": 0,
                "dark_frame_ratio_max": 0.06,
                "mean_luminance": [95, 108],
                "mean_saturation": [65, 85],
            },
        },
    )
    _write_json(output_dir / "flow-shot-plan.json", [])
    _write_json(
        output_dir / "flow-instructions.json",
        {"disabled": True, "reason": "Real and verified visuals cover every story beat."},
    )
    _write_json(
        output_dir / "caption-plan.json",
        {
            "profile": "social-kinetic",
            "pages": [],
            "reason": "Sparse semantic typography replaces continuous subtitles.",
        },
    )
    _write_json(
        output_dir / "capture-manifest.json",
        {
            "source": {
                "path": str(source),
                "checksum_sha256": _sha256(source),
                "read_only": True,
            },
            "presenter_edl": {
                "path": _relative(output_dir, presenter),
                "checksum_sha256": _sha256(presenter),
                "privacy_reviewed": True,
            },
            "editorial_capture": {
                "path": "source-captures/cnbc-dollar-cpi-browser.png",
                "checksum_sha256": _sha256(
                    output_dir
                    / "source-captures"
                    / "cnbc-dollar-cpi-browser.png"
                ),
            },
        },
    )
    _write_json(
        output_dir / "asset-manifest.json",
        {
            "assets": [
                {
                    **asset.model_dump(mode="json"),
                    "checksum_sha256": _sha256(output_dir / asset.path),
                }
                for asset in assets
            ]
        },
    )
    _write_json(
        output_dir / "production-settings.json",
        {
            "style_reference": str(style_reference),
            "reference_profile": "social-kinetic",
            "story_profile": "cpi-inflation",
            "voice_policy": "reference-compressed",
            "flow_operation_budget": 0,
            "human_final_approval_required": True,
        },
    )
    return artifacts

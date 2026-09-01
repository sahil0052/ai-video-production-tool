from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any
from urllib.request import Request, urlopen

from imageio_ffmpeg import get_ffmpeg_exe
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps


SERVER_DIR = Path(__file__).resolve().parent
WORKSPACE = SERVER_DIR.parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from app.production_models import ProductionBlueprint  # noqa: E402


SOURCE = Path(r"D:\Downloads\0813.mp4")
V1 = WORKSPACE / "storage" / "deliverables" / "0813-production-v1"
OUTPUT = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0813-production-v2-training-parity"
)
TRAINING_DIR = WORKSPACE / "training videos data"
PRIMARY_REFERENCE = next(
    TRAINING_DIR.glob("Xbox Cloud Gaming*.mp4")
)
SECONDARY_REFERENCE = next(
    TRAINING_DIR.glob("This engineer just discovered*.mp4")
)
FFMPEG = Path(get_ffmpeg_exe())
DURATION_MS = 45_550
BLS_OVERVIEW_END_MS = 5_570
MUSIC_ATEMPO = 1.04
SELECTED_FUEL_WIDE_ID = "25397939"
SELECTED_FUEL_ACTION_ID = "16567388"


def music_filter_chain() -> str:
    return (
        "highpass=f=35,lowpass=f=7000,"
        "equalizer=f=2800:t=q:w=0.9:g=-2,"
        f"atempo={MUSIC_ATEMPO:.2f},"
        "afade=t=in:st=0:d=0.35,"
        "afade=t=out:st=45.15:d=0.4,"
        "atrim=duration=45.55,aresample=48000"
    )


BOUNDARIES = [
    0,
    1_400,
    3_120,
    4_820,
    BLS_OVERVIEW_END_MS,
    6_960,
    7_947,
    9_338,
    10_310,
    11_220,
    12_274,
    13_020,
    13_714,
    14_880,
    16_427,
    17_467,
    18_660,
    19_430,
    20_839,
    21_990,
    22_599,
    24_439,
    25_834,
    27_530,
    28_900,
    30_195,
    31_400,
    32_963,
    34_180,
    35_242,
    37_061,
    38_566,
    40_058,
    40_786,
    41_666,
    42_262,
    43_220,
    44_093,
    45_550,
]

SHOT_ROLES = [
    ("licensed-context", "split-fuel-hook"),
    ("licensed-context", "rent-pressure"),
    ("presenter", "date-reset"),
    ("direct-evidence", "bls-overview"),
    ("direct-evidence", "bls-cpi-identity"),
    ("licensed-context", "basket-wide"),
    ("licensed-context", "basket-close"),
    ("licensed-context", "food-action"),
    ("licensed-context", "basket-components-grid"),
    ("direct-evidence", "monthly-proof-excerpt"),
    ("direct-evidence", "monthly-proof-number"),
    ("direct-evidence", "yearly-proof-excerpt"),
    ("direct-evidence", "yearly-proof-number"),
    ("presenter", "forecast-reset"),
    ("deterministic-graphic", "actual-forecast-match"),
    ("deterministic-graphic", "inside-story-diagram"),
    ("licensed-context", "fuel-station-night"),
    ("licensed-context", "fuel-action"),
    ("direct-evidence", "energy-table-proof"),
    ("direct-evidence", "gasoline-number-proof"),
    ("licensed-context", "shelter-night"),
    ("licensed-context", "shelter-facade"),
    ("direct-evidence", "shelter-source-proof"),
    ("direct-evidence", "cnbc-headline"),
    ("direct-evidence", "cnbc-paragraph"),
    ("deterministic-graphic", "surprise-question"),
    ("direct-evidence", "market-reaction-proof"),
    ("licensed-context", "positioning-context"),
    ("direct-evidence", "rate-expectations-proof"),
    ("presenter", "other-risks-reset"),
    ("presenter", "lesson-reset"),
    ("deterministic-graphic", "execution-rules"),
    ("deterministic-graphic", "spread-limit"),
    ("deterministic-graphic", "pause-control"),
    ("deterministic-graphic", "confirmation-control"),
    ("direct-evidence", "headline-proof"),
    ("direct-evidence", "full-release-proof"),
    ("presenter", "clean-cta"),
]

REMOTE_ASSETS = {
    "mixkit-fuel-nozzle-31961.mp4": (
        "https://assets.mixkit.co/videos/31961/31961-720.mp4"
    ),
    "pexels-apartment-facade-34641787.mp4": (
        "https://videos.pexels.com/video-files/34641787/"
        "14682617_1080_1920_60fps.mp4"
    ),
    "pexels-apartment-aerial-32107131.mp4": (
        "https://videos.pexels.com/video-files/32107131/"
        "13688486_1440_2560_60fps.mp4"
    ),
    "pexels-trader-monitor-8480284.mp4": (
        "https://videos.pexels.com/video-files/8480284/"
        "8480284-hd_1080_1920_25fps.mp4"
    ),
    "pexels-finance-workspace-37616121.mp4": (
        "https://videos.pexels.com/video-files/37616121/"
        "15942872_1080_1920_25fps.mp4"
    ),
    "pexels-grocery-produce-8027657.mp4": (
        "https://videos.pexels.com/video-files/8027657/"
        "8027657-hd_1080_1920_25fps.mp4"
    ),
    "pexels-gas-station-night-35823379.mp4": (
        "https://videos.pexels.com/video-files/35823379/"
        "15189665_1080_1920_100fps.mp4"
    ),
    "pexels-grocery-market-36108473.mp4": (
        "https://videos.pexels.com/video-files/36108473/"
        "15313484_1080_1920_24fps.mp4"
    ),
    "pexels-apartment-night-6016323.mp4": (
        "https://videos.pexels.com/video-files/6016323/"
        "6016323-hd_1080_1920_30fps.mp4"
    ),
    "pexels-market-tablet-35606106.mp4": (
        "https://videos.pexels.com/video-files/35606106/"
        "15089539_1080_1920_25fps.mp4"
    ),
    "pexels-gas-station-wide-25397939.mp4": (
        "https://videos.pexels.com/video-files/25397939/"
        "11900984_1080_1920_24fps.mp4"
    ),
    "pexels-gasoline-action-16567388.mp4": (
        "https://videos.pexels.com/video-files/16567388/"
        "16567388-hd_1080_1920_30fps.mp4"
    ),
}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(OUTPUT.resolve()).as_posix()


def copy_required(source: Path, destination: Path) -> Path:
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def download_if_missing(destination: Path, url: str) -> None:
    if destination.is_file() and destination.stat().st_size > 50_000:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/139.0.0.0 Safari/537.36"
            )
        },
    )
    temporary = destination.with_suffix(destination.suffix + ".part")
    with urlopen(request, timeout=300) as response, temporary.open("wb") as out:
        shutil.copyfileobj(response, out)
    temporary.replace(destination)


def run(command: list[str], timeout: int = 1800) -> None:
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


def font(size: int, *, mono: bool = False, serif: bool = False) -> ImageFont.FreeTypeFont:
    candidates: list[Path]
    if mono:
        candidates = [
            OUTPUT / "assets" / "fonts" / "ShareTechMono-Regular.ttf",
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
    stroke: int = 0,
) -> ImageFont.FreeTypeFont:
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    for size in range(start, minimum - 1, -2):
        candidate = font(size, mono=mono, serif=serif)
        box = probe.textbbox(
            (0, 0),
            text,
            font=candidate,
            stroke_width=stroke,
        )
        if box[2] - box[0] <= max_width:
            return candidate
    return font(minimum, mono=mono, serif=serif)


def paste_contained(
    canvas: Image.Image,
    source: Image.Image,
    box: tuple[int, int, int, int],
    *,
    background: tuple[int, int, int] | None = None,
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    if background is not None:
        ImageDraw.Draw(canvas).rounded_rectangle(
            box,
            radius=22,
            fill=background,
        )
    fitted = ImageOps.contain(
        source.convert("RGB"),
        (x2 - x1, y2 - y1),
        Image.Resampling.LANCZOS,
    )
    x = x1 + (x2 - x1 - fitted.width) // 2
    y = y1 + (y2 - y1 - fitted.height) // 2
    canvas.paste(fitted, (x, y))
    return (x, y, x + fitted.width, y + fitted.height)


def source_header(
    draw: ImageDraw.ImageDraw,
    *,
    title: str,
    source: str,
    dark: bool = False,
) -> None:
    fill = (248, 248, 244) if dark else (8, 30, 53)
    draw.rounded_rectangle(
        (42, 38, 1038, 154),
        radius=24,
        fill=fill,
    )
    draw.text(
        (72, 64),
        title,
        font=font(35, mono=True),
        fill=(10, 24, 38) if dark else "white",
    )
    draw.text(
        (72, 116),
        source,
        font=font(20, mono=True),
        fill=(90, 105, 115) if dark else (145, 202, 233),
    )


def build_evidence_graphics() -> dict[str, Path]:
    graphics = OUTPUT / "assets" / "evidence"
    graphics.mkdir(parents=True, exist_ok=True)
    bls_overview = Image.open(
        OUTPUT / "source-captures" / "bls-overview.png"
    ).convert("RGB")
    bls_pre = Image.open(
        OUTPUT / "source-captures" / "bls-release-pre-source.png"
    ).convert("RGB")
    bls_table = Image.open(
        OUTPUT / "source-captures" / "bls-table-a-source.png"
    ).convert("RGB")
    cnbc = Image.open(
        OUTPUT / "source-captures" / "cnbc-dollar-cpi-browser.png"
    ).convert("RGB")

    overview = Image.new("RGB", (1080, 1920), (244, 244, 240))
    overview_crop = bls_overview.crop((0, 0, 1020, 1920))
    paste_contained(overview, overview_crop, (0, 0, 1080, 1920))
    overview_path = graphics / "bls-overview-source.jpg"
    overview.save(overview_path, quality=95)

    def bright_source_proof(
        *,
        title: str,
        source: str,
        crops: list[Image.Image],
        label: str,
        value: str,
        accent: tuple[int, int, int],
    ) -> Image.Image:
        card = Image.new("RGB", (1080, 1920), (236, 236, 232))
        card_draw = ImageDraw.Draw(card)
        source_header(card_draw, title=title, source=source)
        for index, crop in enumerate(crops):
            y = 220 + index * 290
            panel = (50, y, 1030, y + 250)
            card_draw.rounded_rectangle(
                panel,
                radius=15,
                fill=(245, 245, 240),
            )
            fitted = ImageOps.contain(
                crop.convert("RGB"),
                (980, 250),
                Image.Resampling.LANCZOS,
            )
            x = 50 + (980 - fitted.width) // 2
            fitted_y = y + (250 - fitted.height) // 2
            card.paste(fitted, (x, fitted_y))
            card_draw.rounded_rectangle(
                (44, y - 6, 1036, y + 256),
                radius=15,
                outline=accent,
                width=5,
            )
        card_draw.text(
            (62, 1110),
            label,
            font=font(45, mono=True),
            fill=(38, 54, 66),
        )
        card_draw.text(
            (58, 1190),
            value,
            font=fit_font(
                value,
                start=205,
                minimum=120,
                max_width=940,
            ),
            fill=(8, 30, 53),
        )
        card_draw.line((62, 1480, 970, 1480), fill=accent, width=14)
        card_draw.text(
            (62, 1545),
            "OFFICIAL RELEASE - DIRECT SOURCE PIXELS",
            font=font(25, mono=True),
            fill=(50, 66, 76),
        )
        return card

    monthly = bright_source_proof(
        title="CONSUMER PRICE INDEX - JULY 2026",
        source="U.S. BLS - DIRECT SOURCE PIXELS - 12 AUG 2026",
        crops=[
            bls_pre.crop((0, 170, 1940, 360)),
            bls_pre.crop((0, 230, 1940, 360)),
            bls_pre.crop((0, 0, 1940, 165)),
        ],
        label="MONTHLY CHANGE",
        value="0.1%",
        accent=(33, 156, 194),
    )
    monthly_path = graphics / "bls-monthly-proof.jpg"
    monthly.save(monthly_path, quality=96)

    yearly = Image.new("RGB", (1080, 1920), (8, 11, 16))
    draw = ImageDraw.Draw(yearly)
    source_header(
        draw,
        title="CONSUMER PRICE INDEX - JULY 2026",
        source="U.S. BLS - DIRECT SOURCE PIXELS - 12 AUG 2026",
        dark=True,
    )
    title_crop = bls_pre.crop((0, 190, 940, 258))
    claim_crop = bls_pre.crop((0, 560, 1940, 720))
    detail_crop = bls_pre.crop((0, 575, 1120, 670))
    title_box = paste_contained(
        yearly,
        title_crop,
        (54, 230, 1026, 430),
        background=None,
    )
    draw.rounded_rectangle(
        (
            title_box[0] - 10,
            title_box[1] - 10,
            title_box[2] + 10,
            title_box[3] + 10,
        ),
        radius=16,
        outline=(128, 145, 155),
        width=4,
    )
    claim_box = paste_contained(
        yearly,
        claim_crop,
        (54, 500, 1026, 820),
        background=None,
    )
    draw.rounded_rectangle(
        (
            claim_box[0] - 12,
            claim_box[1] - 12,
            claim_box[2] + 12,
            claim_box[3] + 12,
        ),
        radius=20,
        outline=(160, 194, 44),
        width=7,
    )
    detail_box = paste_contained(
        yearly,
        detail_crop,
        (54, 900, 1026, 1160),
        background=None,
    )
    draw.rounded_rectangle(
        (
            detail_box[0] - 10,
            detail_box[1] - 10,
            detail_box[2] + 10,
            detail_box[3] + 10,
        ),
        radius=16,
        outline=(160, 194, 44),
        width=5,
    )
    draw.text(
        (70, 1300),
        "12-MONTH CHANGE",
        font=font(48, mono=True),
        fill=(189, 208, 135),
    )
    draw.text((66, 1370), "3.4%", font=font(205), fill=(255, 255, 255))
    draw.line((70, 1615, 690, 1615), fill=(160, 194, 44), width=13)
    draw.text(
        (70, 1680),
        "OFFICIAL RELEASE - SOURCE PIXELS",
        font=font(25, mono=True),
        fill=(128, 151, 164),
    )
    yearly_path = graphics / "bls-yearly-proof.jpg"
    yearly.save(yearly_path, quality=96)

    energy = Image.new("RGB", (1080, 1920), (246, 245, 239))
    draw = ImageDraw.Draw(energy)
    source_header(
        draw,
        title="ENERGY AND GASOLINE • JULY 2026",
        source="U.S. BLS TABLE A • OFFICIAL SOURCE PIXELS",
    )
    table_title = bls_table.crop((0, 0, 1650, 90))
    labels = bls_table.crop((0, 535, 1030, 725))
    values = bls_table.crop((1880, 535, 2254, 725))
    paste_contained(energy, table_title, (48, 220, 1032, 360))
    label_box = paste_contained(
        energy,
        labels,
        (48, 440, 748, 810),
        background=(255, 255, 255),
    )
    value_box = paste_contained(
        energy,
        values,
        (750, 440, 1032, 810),
        background=(255, 255, 255),
    )
    draw.rounded_rectangle(
        (
            label_box[0] - 10,
            label_box[1] - 10,
            value_box[2] + 10,
            value_box[3] + 10,
        ),
        radius=18,
        outline=(23, 117, 150),
        width=6,
    )
    draw.text((70, 965), "ENERGY", font=font(45, mono=True), fill=(54, 70, 82))
    draw.text((62, 1015), "−1.5%", font=font(170), fill=(23, 117, 150))
    draw.text((70, 1315), "GASOLINE", font=font(45, mono=True), fill=(54, 70, 82))
    draw.text((62, 1365), "−2.9%", font=font(170), fill=(190, 58, 45))
    energy_path = graphics / "bls-energy-proof.jpg"
    energy.save(energy_path, quality=96)

    shelter = bright_source_proof(
        title="SHELTER - MONTHLY CPI CONTRIBUTION",
        source="U.S. BLS OFFICIAL RELEASE - 12 AUG 2026",
        crops=[
            bls_pre.crop((0, 350, 1940, 475)),
            bls_pre.crop((0, 390, 1940, 520)),
            bls_pre.crop((0, 0, 1940, 165)),
        ],
        label="SHELTER CONTRIBUTION",
        value="TWO-THIRDS",
        accent=(209, 142, 30),
    )
    shelter_path = graphics / "bls-shelter-proof.jpg"
    shelter.save(shelter_path, quality=96)

    cnbc_clean = ImageEnhance.Contrast(cnbc).enhance(1.18)
    cnbc_clean = ImageEnhance.Brightness(cnbc_clean).enhance(1.14)
    headline = Image.new("RGB", (1080, 1920), (9, 10, 12))
    draw = ImageDraw.Draw(headline)
    source_header(
        draw,
        title="CNBC • MARKETS",
        source="12 AUG 2026 • GENUINE EDITORIAL CAPTURE",
        dark=True,
    )
    logo = cnbc_clean.crop((40, 0, 1180, 110))
    headline_crop = cnbc_clean.crop((150, 240, 1085, 470))
    paste_contained(headline, logo, (70, 210, 1010, 360))
    box = paste_contained(
        headline,
        headline_crop,
        (58, 430, 1022, 760),
        background=None,
    )
    draw.rounded_rectangle(
        (box[0] - 8, box[1] - 8, box[2] + 8, box[3] + 8),
        radius=18,
        outline=(71, 171, 223),
        width=6,
    )
    draw.text((70, 1010), "DOLLAR", font=font(42, mono=True), fill=(143, 211, 255))
    draw.text((64, 1065), "GAINED", font=font(150), fill="white")
    headline_path = graphics / "cnbc-headline-proof.jpg"
    headline.save(headline_path, quality=96)

    paragraph = Image.new("RGB", (1080, 1920), (9, 10, 12))
    draw = ImageDraw.Draw(paragraph)
    source_header(
        draw,
        title="CNBC • MARKET REACTION",
        source="GENUINE EDITORIAL CAPTURE • 12 AUG 2026",
        dark=True,
    )
    paragraph_crop = cnbc_clean.crop((260, 1020, 1035, 1288))
    box = paste_contained(
        paragraph,
        paragraph_crop,
        (58, 300, 1022, 690),
        background=None,
    )
    draw.rounded_rectangle(
        (box[0] - 8, box[1] - 8, box[2] + 8, box[3] + 8),
        radius=18,
        outline=(71, 171, 223),
        width=6,
    )
    draw.text(
        (70, 930),
        "EXPECTED DATA.",
        font=font(78),
        fill="white",
    )
    draw.text(
        (70, 1040),
        "REAL MARKET MOVE.",
        font=font(78),
        fill=(143, 211, 255),
    )
    paragraph_path = graphics / "cnbc-paragraph-proof.jpg"
    paragraph.save(paragraph_path, quality=96)

    rates = Image.new("RGB", (1080, 1920), (9, 10, 12))
    draw = ImageDraw.Draw(rates)
    source_header(
        draw,
        title="CNBC - RATE EXPECTATIONS",
        source="GENUINE EDITORIAL CAPTURE - 12 AUG 2026",
        dark=True,
    )
    rates_crop = cnbc_clean.crop((250, 1240, 1045, 1490))
    rates_box = paste_contained(
        rates,
        rates_crop,
        (58, 320, 1022, 650),
        background=None,
    )
    draw.rounded_rectangle(
        (
            rates_box[0] - 8,
            rates_box[1] - 8,
            rates_box[2] + 8,
            rates_box[3] + 8,
        ),
        radius=18,
        outline=(255, 194, 72),
        width=6,
    )
    draw.text(
        (70, 900),
        "RATE",
        font=font(58, mono=True),
        fill=(255, 194, 72),
    )
    draw.text(
        (64, 965),
        "EXPECTATIONS",
        font=fit_font(
            "EXPECTATIONS",
            start=100,
            minimum=72,
            max_width=930,
        ),
        fill=(255, 255, 255),
    )
    rates_path = graphics / "cnbc-rate-expectations-proof.jpg"
    rates.save(rates_path, quality=96)

    split = Image.new("RGB", (1080, 1920), (8, 12, 18))
    draw = ImageDraw.Draw(split)
    draw.text((56, 42), "HEADLINE", font=font(31, mono=True), fill=(255, 220, 80))
    head_crop = cnbc_clean.crop((150, 240, 1085, 470))
    paste_contained(split, head_crop, (38, 105, 1042, 745), background=(245, 245, 242))
    draw.line((54, 814, 1026, 814), fill=(255, 255, 255), width=3)
    draw.text((56, 850), "FULL RELEASE", font=font(31, mono=True), fill=(89, 220, 255))
    source_crop = bls_pre.crop((0, 190, 1940, 520))
    paste_contained(split, source_crop, (38, 920, 1042, 1610), background=(255, 255, 255))
    draw.text(
        (540, 1745),
        "MARKET READS THE FULL BILL",
        font=fit_font(
            "MARKET READS THE FULL BILL",
            start=50,
            minimum=36,
            max_width=930,
            mono=True,
        ),
        fill="white",
        anchor="mm",
    )
    split_path = graphics / "headline-vs-full-release.jpg"
    split.save(split_path, quality=96)

    identity = Image.new("RGB", (1080, 1920), (9, 10, 12))
    draw = ImageDraw.Draw(identity)
    source_header(
        draw,
        title="U.S. BLS - OFFICIAL CPI RELEASE",
        source="DIRECT SOURCE PIXELS - 12 AUG 2026",
        dark=True,
    )
    identity_crop = bls_pre.crop((600, 255, 1620, 335))
    identity_box = paste_contained(
        identity,
        identity_crop,
        (54, 270, 1026, 520),
        background=None,
    )
    draw.rounded_rectangle(
        (
            identity_box[0] - 10,
            identity_box[1] - 10,
            identity_box[2] + 10,
            identity_box[3] + 10,
        ),
        radius=18,
        outline=(77, 207, 232),
        width=6,
    )
    draw.text((64, 720), "CPI-U", font=font(185), fill=(255, 255, 255))
    draw.line((70, 955, 790, 955), fill=(77, 207, 232), width=12)
    draw.text(
        (70, 1040),
        "MONTHLY SHOPPING",
        font=font(60, mono=True),
        fill=(177, 221, 234),
    )
    draw.text(
        (70, 1130),
        "BASKET",
        font=font(112),
        fill=(255, 255, 255),
    )
    draw.text(
        (70, 1345),
        "FOOD / PETROL / RENT / SERVICES",
        font=font(31, mono=True),
        fill=(156, 173, 184),
    )
    identity_path = graphics / "bls-cpi-identity-dark.jpg"
    identity.save(identity_path, quality=96)

    def dark_number_proof(
        *,
        filename: str,
        title: str,
        label: str,
        value: str,
        accent: tuple[int, int, int],
        source_crop: Image.Image,
    ) -> Path:
        card = Image.new("RGB", (1080, 1920), (9, 10, 12))
        card_draw = ImageDraw.Draw(card)
        source_header(
            card_draw,
            title=title,
            source="U.S. BLS - DIRECT SOURCE PIXELS",
            dark=True,
        )
        source_box = paste_contained(
            card,
            source_crop,
            (54, 270, 1026, 540),
            background=None,
        )
        card_draw.rounded_rectangle(
            (
                source_box[0] - 10,
                source_box[1] - 10,
                source_box[2] + 10,
                source_box[3] + 10,
            ),
            radius=18,
            outline=accent,
            width=6,
        )
        card_draw.text(
            (70, 770),
            label,
            font=font(48, mono=True),
            fill=(173, 190, 201),
        )
        card_draw.text(
            (62, 850),
            value,
            font=fit_font(
                value,
                start=230,
                minimum=150,
                max_width=930,
            ),
            fill=(255, 255, 255),
        )
        card_draw.line((70, 1170, 900, 1170), fill=accent, width=14)
        card_draw.text(
            (70, 1240),
            "OFFICIAL RELEASE",
            font=font(32, mono=True),
            fill=accent,
        )
        path = graphics / filename
        card.save(path, quality=96)
        return path

    monthly_number_path = dark_number_proof(
        filename="bls-monthly-number-dark.jpg",
        title="CONSUMER PRICE INDEX - JULY 2026",
        label="MONTHLY CHANGE",
        value="0.1%",
        accent=(77, 207, 232),
        source_crop=bls_pre.crop((650, 255, 1600, 335)),
    )
    yearly_number_path = dark_number_proof(
        filename="bls-yearly-number-dark.jpg",
        title="CONSUMER PRICE INDEX - JULY 2026",
        label="12-MONTH CHANGE",
        value="3.4%",
        accent=(164, 205, 63),
        source_crop=bls_pre.crop((300, 320, 1200, 392)),
    )
    gasoline_number_path = dark_number_proof(
        filename="bls-energy-number-dark.jpg",
        title="ENERGY AND GASOLINE - JULY 2026",
        label="ENERGY -1.5 / GASOLINE",
        value="-2.9%",
        accent=(226, 79, 67),
        source_crop=bls_table.crop((0, 520, 2254, 735)),
    )

    full_release = Image.new("RGB", (1080, 1920), (5, 10, 17))
    draw = ImageDraw.Draw(full_release)
    draw.text(
        (56, 60),
        "FULL RELEASE",
        font=font(34, mono=True),
        fill=(77, 207, 232),
    )
    release_intro_crop = bls_pre.crop((0, 250, 1250, 390))
    release_intro_box = paste_contained(
        full_release,
        release_intro_crop,
        (42, 180, 1038, 760),
        background=(255, 255, 255),
    )
    draw.rounded_rectangle(
        (
            release_intro_box[0] - 8,
            release_intro_box[1] - 8,
            release_intro_box[2] + 8,
            release_intro_box[3] + 8,
        ),
        radius=14,
        outline=(77, 207, 232),
        width=5,
    )
    release_shelter_crop = bls_pre.crop((0, 390, 1250, 520))
    release_shelter_box = paste_contained(
        full_release,
        release_shelter_crop,
        (42, 800, 1038, 1360),
        background=(255, 255, 255),
    )
    draw.rounded_rectangle(
        (
            release_shelter_box[0] - 8,
            release_shelter_box[1] - 8,
            release_shelter_box[2] + 8,
            release_shelter_box[3] + 8,
        ),
        radius=14,
        outline=(255, 194, 72),
        width=5,
    )
    draw.text(
        (540, 1555),
        "MARKET READS THE FULL BILL",
        font=fit_font(
            "MARKET READS THE FULL BILL",
            start=54,
            minimum=40,
            max_width=950,
            mono=True,
        ),
        fill=(255, 255, 255),
        anchor="mm",
    )
    full_release_path = graphics / "bls-full-release-dark.jpg"
    full_release.save(full_release_path, quality=96)

    return {
        "bls-overview": overview_path,
        "bls-identity": identity_path,
        "bls-monthly": monthly_path,
        "bls-monthly-number": monthly_number_path,
        "bls-yearly": yearly_path,
        "bls-yearly-number": yearly_number_path,
        "bls-energy": energy_path,
        "bls-gasoline-number": gasoline_number_path,
        "bls-shelter": shelter_path,
        "cnbc-headline": headline_path,
        "cnbc-paragraph": paragraph_path,
        "cnbc-rates": rates_path,
        "headline-proof": headline_path,
        "full-release-proof": full_release_path,
        "headline-vs-full": split_path,
    }


def build_deterministic_graphics() -> dict[str, Path]:
    graphics = OUTPUT / "assets" / "graphics"
    graphics.mkdir(parents=True, exist_ok=True)

    contrast = Image.new("RGB", (1080, 1920), (5, 10, 16))
    draw = ImageDraw.Draw(contrast)
    draw.text((70, 120), "HEADLINE", font=font(31, mono=True), fill=(87, 218, 255))
    draw.rounded_rectangle(
        (70, 270, 1010, 780),
        radius=36,
        fill=(12, 22, 31),
        outline=(61, 96, 116),
        width=4,
    )
    draw.text((190, 375), "ACTUAL", font=font(44, mono=True), fill=(185, 197, 204))
    draw.text((170, 470), "0.1%", font=font(115), fill="white")
    draw.text((660, 375), "FORECAST", font=font(44, mono=True), fill=(185, 197, 204))
    draw.text((670, 470), "0.1%", font=font(115), fill="white")
    draw.text((540, 635), "=", font=font(105), fill=(163, 232, 82), anchor="mm")
    draw.text((70, 965), "INSIDE THE DATA", font=font(31, mono=True), fill=(255, 210, 75))
    draw.line((120, 1110, 960, 1110), fill=(255, 255, 255), width=5)
    draw.ellipse((120, 1230, 350, 1460), outline=(89, 220, 255), width=8)
    draw.ellipse((425, 1230, 655, 1460), outline=(255, 190, 65), width=8)
    draw.ellipse((730, 1230, 960, 1460), outline=(235, 75, 67), width=8)
    for x, label in ((235, "ENERGY"), (540, "SHELTER"), (845, "RATES")):
        draw.text((x, 1505), label, font=font(27, mono=True), fill=(210, 218, 223), anchor="mm")
    draw.text(
        (540, 1680),
        "SAME HEADLINE ≠ SAME STORY",
        font=fit_font(
            "SAME HEADLINE ≠ SAME STORY",
            start=55,
            minimum=40,
            max_width=930,
            mono=True,
        ),
        fill="white",
        anchor="mm",
    )
    contrast_path = graphics / "actual-forecast-inside-story.jpg"
    contrast.save(contrast_path, quality=95)

    question = Image.new("RGB", (1080, 1920), (12, 6, 11))
    glow = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((120, 380, 960, 1220), fill=(160, 16, 38, 110))
    glow = glow.filter(ImageFilter.GaussianBlur(110))
    question.paste(glow.convert("RGB"), (0, 0), glow)
    draw = ImageDraw.Draw(question)
    draw.text((540, 610), "0", font=font(330), fill=(255, 245, 240), anchor="mm")
    draw.text((540, 1010), "?", font=font(420, serif=True), fill=(236, 54, 74), anchor="mm")
    draw.text(
        (540, 1420),
        "SURPRISE ZERO.",
        font=font(64, mono=True),
        fill="white",
        anchor="mm",
    )
    draw.text(
        (540, 1510),
        "MARKET MOVED.",
        font=font(64, mono=True),
        fill=(236, 54, 74),
        anchor="mm",
    )
    question_path = graphics / "surprise-question.jpg"
    question.save(question_path, quality=95)

    safeguards = Image.new("RGB", (1080, 1920), (4, 12, 18))
    draw = ImageDraw.Draw(safeguards)
    draw.text((70, 115), "AUTOMATION NEEDS GUARDRAILS", font=font(40, mono=True), fill=(90, 221, 255))
    rows = [
        ("01", "SPREAD LIMIT", (90, 221, 255)),
        ("02", "PAUSE", (255, 194, 72)),
        ("03", "CONFIRMATION", (162, 232, 82)),
    ]
    for index, (number, label, accent) in enumerate(rows):
        y = 420 + index * 370
        draw.rounded_rectangle(
            (70, y, 1010, y + 260),
            radius=34,
            fill=(13, 26, 35),
            outline=accent,
            width=5,
        )
        draw.text((118, y + 74), number, font=font(42, mono=True), fill=accent)
        draw.text(
            (230, y + 72),
            label,
            font=fit_font(
                label,
                start=64,
                minimum=48,
                max_width=700,
                mono=True,
            ),
            fill="white",
        )
    draw.text(
        (540, 1655),
        "COMPARE LESS. CONTROL MORE.",
        font=fit_font(
            "COMPARE LESS. CONTROL MORE.",
            start=48,
            minimum=36,
            max_width=940,
            mono=True,
        ),
        fill=(190, 200, 207),
        anchor="mm",
    )
    safeguards_path = graphics / "risk-controls.jpg"
    safeguards.save(safeguards_path, quality=95)

    grid_overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(grid_overlay)
    for x, y, label, accent in (
        (30, 40, "FOOD", (255, 220, 76)),
        (560, 40, "PETROL", (89, 220, 255)),
        (30, 1000, "RENT", (255, 112, 85)),
        (560, 1000, "SERVICES", (167, 232, 83)),
    ):
        draw.rounded_rectangle(
            (x + 20, y + 20, x + 490, y + 118),
            radius=18,
            fill=(4, 8, 12, 220),
            outline=accent,
            width=3,
        )
        draw.text((x + 255, y + 68), label, font=font(33, mono=True), fill=accent, anchor="mm")
    grid_overlay_path = graphics / "basket-grid-overlay.png"
    grid_overlay.save(grid_overlay_path)

    split_mask = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(split_mask)
    draw.rectangle((0, 1080, 1080, 1094), fill=(255, 255, 255, 255))
    split_mask_path = graphics / "split-divider.png"
    split_mask.save(split_mask_path)

    actual_match = Image.new("RGB", (1080, 1920), (8, 9, 10))
    draw = ImageDraw.Draw(actual_match)
    draw.text(
        (70, 120),
        "HEADLINE INPUT",
        font=font(34, mono=True),
        fill=(91, 218, 246),
    )
    draw.rounded_rectangle(
        (65, 330, 1015, 1110),
        radius=42,
        fill=(18, 20, 22),
        outline=(64, 103, 126),
        width=5,
    )
    draw.text(
        (255, 475),
        "ACTUAL",
        font=font(44, mono=True),
        fill=(172, 188, 198),
        anchor="mm",
    )
    draw.text(
        (825, 475),
        "FORECAST",
        font=font(44, mono=True),
        fill=(172, 188, 198),
        anchor="mm",
    )
    draw.text((255, 695), "0.1%", font=font(150), fill="white", anchor="mm")
    draw.text((825, 695), "0.1%", font=font(150), fill="white", anchor="mm")
    draw.text(
        (540, 700),
        "=",
        font=font(120),
        fill=(164, 232, 82),
        anchor="mm",
    )
    draw.line((160, 900, 920, 900), fill=(164, 232, 82), width=12)
    draw.text(
        (540, 995),
        "ZERO HEADLINE SURPRISE",
        font=font(48, mono=True),
        fill=(215, 230, 235),
        anchor="mm",
    )
    draw.text(
        (540, 1440),
        "BUT PRICE STILL MOVED",
        font=fit_font(
            "BUT PRICE STILL MOVED",
            start=74,
            minimum=52,
            max_width=930,
            mono=True,
        ),
        fill=(255, 194, 72),
        anchor="mm",
    )
    actual_match_path = graphics / "actual-forecast-match.jpg"
    actual_match.save(actual_match_path, quality=96)

    inside_story = Image.new("RGB", (1080, 1920), (8, 9, 10))
    draw = ImageDraw.Draw(inside_story)
    draw.text(
        (70, 120),
        "INSIDE THE DATA",
        font=font(34, mono=True),
        fill=(255, 194, 72),
    )
    factors = [
        ("ENERGY", "DOWN", (91, 218, 246)),
        ("SHELTER", "UP", (255, 194, 72)),
        ("RATE EXPECTATIONS", "SHIFT", (233, 77, 84)),
    ]
    for index, (label, value, accent) in enumerate(factors):
        y = 360 + index * 390
        draw.rounded_rectangle(
            (70, y, 1010, y + 270),
            radius=34,
            fill=(18, 20, 22),
            outline=accent,
            width=5,
        )
        draw.text(
            (120, y + 58),
            f"0{index + 1}",
            font=font(34, mono=True),
            fill=accent,
        )
        draw.text(
            (210, y + 54),
            label,
            font=fit_font(
                label,
                start=55,
                minimum=38,
                max_width=720,
                mono=True,
            ),
            fill=(244, 248, 250),
        )
        draw.text(
            (890, y + 175),
            value,
            font=font(42, mono=True),
            fill=accent,
            anchor="mm",
        )
    draw.text(
        (540, 1650),
        "SAME HEADLINE. DIFFERENT PRESSURES.",
        font=fit_font(
            "SAME HEADLINE. DIFFERENT PRESSURES.",
            start=48,
            minimum=34,
            max_width=940,
            mono=True,
        ),
        fill=(191, 204, 212),
        anchor="mm",
    )
    inside_story_path = graphics / "inside-story-factors.jpg"
    inside_story.save(inside_story_path, quality=96)

    question_overlay = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
    draw = ImageDraw.Draw(question_overlay)
    draw.rounded_rectangle(
        (70, 280, 1010, 1000),
        radius=42,
        fill=(8, 9, 10, 220),
        outline=(228, 66, 80, 240),
        width=6,
    )
    draw.text(
        (540, 430),
        "SURPRISE",
        font=font(55, mono=True),
        fill=(190, 204, 213, 255),
        anchor="mm",
    )
    draw.text(
        (540, 625),
        "0",
        font=font(240),
        fill=(255, 255, 255, 255),
        anchor="mm",
    )
    draw.text(
        (540, 860),
        "WHY DID USD MOVE?",
        font=fit_font(
            "WHY DID USD MOVE?",
            start=68,
            minimum=48,
            max_width=850,
            mono=True,
        ),
        fill=(239, 77, 91, 255),
        anchor="mm",
    )
    question_overlay_path = graphics / "surprise-question-overlay.png"
    question_overlay.save(question_overlay_path)

    execution = Image.new("RGB", (1080, 1920), (8, 9, 10))
    draw = ImageDraw.Draw(execution)
    draw.text(
        (70, 120),
        "ROBOT DECISION",
        font=font(34, mono=True),
        fill=(91, 218, 246),
    )
    draw.rounded_rectangle(
        (70, 300, 1010, 720),
        radius=38,
        fill=(18, 20, 22),
        outline=(91, 218, 246),
        width=5,
    )
    draw.text(
        (540, 430),
        "ACTUAL = FORECAST",
        font=font(62, mono=True),
        fill=(255, 255, 255),
        anchor="mm",
    )
    draw.text(
        (540, 570),
        "NOT ENOUGH",
        font=font(72, mono=True),
        fill=(239, 77, 91),
        anchor="mm",
    )
    for index, (label, accent) in enumerate(
        (
            ("SPREAD", (91, 218, 246)),
            ("PAUSE", (255, 194, 72)),
            ("CONFIRMATION", (164, 232, 82)),
        )
    ):
        y = 920 + index * 210
        draw.line((120, y, 260, y), fill=accent, width=10)
        draw.text(
            (300, y - 36),
            label,
            font=font(56, mono=True),
            fill=(245, 248, 250),
        )
    execution_path = graphics / "execution-rules.jpg"
    execution.save(execution_path, quality=96)

    def control_card(
        *,
        filename: str,
        number: str,
        label: str,
        detail: str,
        accent: tuple[int, int, int],
    ) -> Path:
        card = Image.new("RGB", (1080, 1920), (8, 9, 10))
        card_draw = ImageDraw.Draw(card)
        card_draw.text(
            (70, 120),
            "AUTOMATION GUARDRAIL",
            font=font(34, mono=True),
            fill=accent,
        )
        card_draw.text(
            (80, 400),
            number,
            font=font(220),
            fill=(38, 55, 66),
        )
        card_draw.line((80, 760, 1000, 760), fill=accent, width=12)
        card_draw.text(
            (80, 840),
            label,
            font=fit_font(
                label,
                start=112,
                minimum=72,
                max_width=920,
                mono=True,
            ),
            fill=(255, 255, 255),
        )
        card_draw.text(
            (84, 1090),
            detail,
            font=fit_font(
                detail,
                start=48,
                minimum=34,
                max_width=900,
                mono=True,
            ),
            fill=(177, 192, 201),
        )
        card_draw.rounded_rectangle(
            (80, 1430, 1000, 1540),
            radius=24,
            fill=(18, 20, 22),
            outline=accent,
            width=4,
        )
        card_draw.text(
            (540, 1485),
            "CONTROL LOCKED",
            font=font(40, mono=True),
            fill=accent,
            anchor="mm",
        )
        path = graphics / filename
        card.save(path, quality=96)
        return path

    spread_path = control_card(
        filename="control-spread-limit.jpg",
        number="01",
        label="SPREAD LIMIT",
        detail="SKIP WIDE MARKET CONDITIONS",
        accent=(91, 218, 246),
    )
    pause_path = control_card(
        filename="control-pause.jpg",
        number="02",
        label="PAUSE",
        detail="WAIT AFTER THE DATA RELEASE",
        accent=(255, 194, 72),
    )
    confirmation_path = control_card(
        filename="control-confirmation.jpg",
        number="03",
        label="CONFIRMATION",
        detail="REQUIRE A SECOND SIGNAL",
        accent=(164, 232, 82),
    )

    return {
        "contrast": contrast_path,
        "question": question_path,
        "safeguards": safeguards_path,
        "grid-overlay": grid_overlay_path,
        "split-divider": split_mask_path,
        "actual-match": actual_match_path,
        "inside-story": inside_story_path,
        "question-overlay": question_overlay_path,
        "execution-rules": execution_path,
        "spread-limit": spread_path,
        "pause-control": pause_path,
        "confirmation-control": confirmation_path,
    }


def flat_words(transcript: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        word
        for segment in transcript
        for word in segment.get("words", [])
    ]


CAPTION_GROUPS = [
    (0, 0, "Sochiye"),
    (1, 4, "Petrol kharcha kam"),
    (5, 8, "But rent abhi"),
    (9, 12, "Pocket kha raha"),
    (13, 14, "12 August"),
    (15, 18, "2026 ko"),
    (19, 21, "America ka CPI"),
    (22, 25, "Yehi twist tha"),
    (48, 49, "Forecast bhi"),
    (50, 52, "Exactly same tha"),
    (54, 56, "Headline ke andar"),
    (57, 60, "Real story alag"),
    (70, 72, "Phir bhi monthly"),
    (73, 74, "Inflation increase"),
    (75, 78, "Lagbhag do tihai"),
    (79, 79, "Shelter"),
    (80, 82, "Yaani rent aur"),
    (83, 84, "Housing cost"),
    (85, 87, "Se aaya"),
    (96, 99, "Lekin sawal hai"),
    (100, 103, "Surprise zero tha"),
    (104, 106, "Market kyun hila?"),
    (107, 108, "Kyunki positioning"),
    (109, 111, "Rate expectations"),
    (112, 115, "Aur dusre risks"),
    (116, 120, "Dollar ko move karte"),
    (121, 123, "Lesson clear hai"),
    (124, 127, "Sirf actual forecast"),
    (128, 131, "Compare enough nahi"),
    (132, 133, "Spread limit"),
    (134, 136, "Pause aur confirmation"),
    (137, 138, "Zaroori hai"),
    (139, 142, "Robot headline padhta"),
    (143, 145, "Market poora bill"),
    (146, 149, "Forex videos ke liye"),
    (150, 151, "Follow kijiye"),
]


def source_aligned_tokens(
    *,
    source_words: list[dict[str, Any]],
    display_words: list[str],
) -> list[dict[str, Any]]:
    if not source_words or not display_words:
        return []
    source_count = len(source_words)
    display_count = len(display_words)
    boundaries = [
        round(index * source_count / display_count)
        for index in range(display_count + 1)
    ]
    boundaries[0] = 0
    boundaries[-1] = source_count
    tokens: list[dict[str, Any]] = []
    for index, text in enumerate(display_words):
        start_index = min(source_count - 1, boundaries[index])
        end_index = max(start_index, boundaries[index + 1] - 1)
        tokens.append(
            {
                "text": text,
                "start_ms": round(
                    float(source_words[start_index]["start"]) * 1000
                ),
                "end_ms": round(
                    float(source_words[end_index]["end"]) * 1000
                ),
                "highlighted": False,
                "confidence": None,
            }
        )
    return tokens


def caption_family(start_ms: int) -> tuple[str, str, int]:
    if 16_427 <= start_ms < 18_630 or 38_566 <= start_ms < 42_262:
        return ("technical-mono", "center-74", 500)
    return ("compact-pill", "center-76", 620)


def build_caption_pages(transcript: list[dict[str, Any]]) -> list[dict[str, Any]]:
    words = flat_words(transcript)
    pages: list[dict[str, Any]] = []
    for start_index, end_index, display in CAPTION_GROUPS:
        start_ms = round(float(words[start_index]["start"]) * 1000)
        end_ms = round(float(words[end_index]["end"]) * 1000)
        duration = end_ms - start_ms
        if duration < 350:
            end_ms = start_ms + 350
            duration = 350
        if duration > 1300:
            raise ValueError(
                f"Caption group exceeds 1300 ms: {display} ({duration})"
            )
        display_words = display.split()
        tokens = source_aligned_tokens(
            source_words=words[start_index : end_index + 1],
            display_words=display_words,
        )
        family, anchor, max_width = caption_family(start_ms)
        pages.append(
            {
                "start_ms": start_ms,
                "end_ms": end_ms,
                "tokens": tokens,
                "family": family,
                "anchor": anchor,
                "transition": "hard-cut",
                "max_width": max_width,
            }
        )
    for left, right in zip(pages, pages[1:]):
        if left["end_ms"] > right["start_ms"]:
            left["end_ms"] = right["start_ms"]
            left["tokens"][-1]["end_ms"] = right["start_ms"]
    return pages


def asset(
    *,
    identifier: str,
    kind: str,
    path: Path,
    keywords: list[str],
    provenance: str,
    license_name: str,
    provider: str | None = None,
    remote_id: str | None = None,
    creator: str | None = None,
    source_url: str | None = None,
    license_url: str | None = None,
    search_query: str | None = None,
) -> dict[str, Any]:
    return {
        "id": identifier,
        "kind": kind,
        "path": relative(path),
        "keywords": keywords,
        "provenance": provenance,
        "license": license_name,
        "provider": provider,
        "remote_id": remote_id,
        "creator": creator,
        "source_url": source_url,
        "license_url": license_url,
        "search_query": search_query,
        "start_ms": None,
        "end_ms": None,
    }


def layer(
    *,
    identifier: str,
    shot_id: str,
    start_ms: int,
    end_ms: int,
    source_role: str,
    kind: str,
    asset_id: str,
    bounds: tuple[int, int, int, int] = (0, 0, 1080, 1920),
    source_start_ms: int | None = None,
    source_end_ms: int | None = None,
    z_index: int = 10,
    border_radius: int = 0,
    start_scale: float = 1.0,
    end_scale: float = 1.04,
    reference_role: str = "primary-13",
) -> dict[str, Any]:
    x, y, width, height = bounds
    return {
        "id": identifier,
        "shot_id": shot_id,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "source_role": source_role,
        "kind": kind,
        "asset_id": asset_id,
        "flow_shot_id": None,
        "source_start_ms": source_start_ms,
        "source_end_ms": source_end_ms,
        "bounds": {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        },
        "crop": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
        "fit": "cover" if kind == "video" else "fill",
        "transform_keyframes": [
            {
                "at_ms": 0,
                "x": 0.0,
                "y": 0.0,
                "scale": start_scale,
                "rotate_deg": 0.0,
            },
            {
                "at_ms": end_ms - start_ms,
                "x": 0.0,
                "y": 0.0,
                "scale": end_scale,
                "rotate_deg": 0.0,
            },
        ],
        "opacity_keyframes": [{"at_ms": 0, "value": 1.0}],
        "effect_keyframes": [
            {
                "at_ms": 0,
                "brightness": 1.0,
                "contrast": 1.0,
                "saturation": 1.0,
                "blur_px": 0.0,
            }
        ],
        "blend_mode": "normal",
        "z_index": z_index,
        "muted": True,
        "playback_rate": 1.0,
        "illustrative_label": False,
        "border_radius": border_radius,
        "color_filter": None,
        "reference_role": reference_role,
    }


def build_layers() -> list[dict[str, Any]]:
    layers: list[dict[str, Any]] = []
    for index, ((role, editorial), start_ms, end_ms) in enumerate(
        zip(SHOT_ROLES, BOUNDARIES[:-1], BOUNDARIES[1:]),
        start=1,
    ):
        shot_id = f"shot-{index:02d}"
        if editorial == "split-fuel-hook":
            layers.extend(
                [
                    layer(
                        identifier="hook-presenter",
                        shot_id=shot_id,
                        start_ms=start_ms,
                        end_ms=end_ms,
                        source_role="presenter",
                        kind="video",
                        asset_id="presenter-edl",
                        bounds=(0, 1094, 1080, 826),
                        source_start_ms=start_ms,
                        source_end_ms=end_ms,
                        z_index=10,
                        start_scale=1.02,
                        end_scale=1.06,
                    ),
                    layer(
                        identifier="hook-fuel",
                        shot_id=shot_id,
                        start_ms=start_ms,
                        end_ms=end_ms,
                        source_role="licensed-context",
                        kind="video",
                        asset_id="licensed-fuel-nozzle",
                        bounds=(0, 0, 1080, 1080),
                        source_start_ms=2_000,
                        source_end_ms=3_400,
                        z_index=20,
                        start_scale=1.02,
                        end_scale=1.07,
                    ),
                    layer(
                        identifier="hook-divider",
                        shot_id=shot_id,
                        start_ms=start_ms,
                        end_ms=end_ms,
                        source_role="deterministic-graphic",
                        kind="image",
                        asset_id="graphic-split-divider",
                        z_index=30,
                        start_scale=1,
                        end_scale=1,
                    ),
                ]
            )
            continue
        definitions: dict[str, tuple[str, str, int | None]] = {
            "rent-pressure": ("licensed-rent-keys", "video", 450),
            "date-reset": ("presenter-edl", "video", start_ms),
            "bls-overview": ("evidence-bls-overview", "image", None),
            "bls-cpi-identity": ("evidence-bls-identity", "image", None),
            "basket-wide": ("licensed-grocery-market", "video", 2_000),
            "basket-close": ("licensed-shopping-cart", "video", 700),
            "food-action": ("licensed-grocery-produce", "video", 700),
            "monthly-proof-excerpt": (
                "evidence-bls-monthly-excerpt",
                "image",
                None,
            ),
            "monthly-proof-number": (
                "evidence-bls-monthly-number",
                "image",
                None,
            ),
            "yearly-proof-excerpt": (
                "evidence-bls-yearly-excerpt",
                "image",
                None,
            ),
            "yearly-proof-number": (
                "evidence-bls-yearly-number",
                "image",
                None,
            ),
            "forecast-reset": ("presenter-edl", "video", start_ms),
            "actual-forecast-match": ("graphic-actual-match", "image", None),
            "inside-story-diagram": ("graphic-inside-story", "image", None),
            "fuel-station-night": (
                "licensed-gas-station-wide",
                "video",
                350,
            ),
            "fuel-action": ("licensed-gasoline-action", "video", 150),
            "energy-table-proof": (
                "evidence-bls-energy-table",
                "image",
                None,
            ),
            "gasoline-number-proof": (
                "evidence-bls-gasoline-number",
                "image",
                None,
            ),
            "shelter-night": (
                "licensed-apartment-night",
                "video",
                350,
            ),
            "shelter-facade": ("licensed-apartment-facade", "video", 1_100),
            "shelter-source-proof": ("evidence-bls-shelter", "image", None),
            "cnbc-headline": ("evidence-cnbc-headline", "image", None),
            "cnbc-paragraph": ("evidence-cnbc-paragraph", "image", None),
            "market-reaction-proof": (
                "evidence-cnbc-paragraph",
                "image",
                None,
            ),
            "positioning-context": ("licensed-trader-monitor", "video", 2_300),
            "rate-expectations-proof": (
                "evidence-cnbc-rates",
                "image",
                None,
            ),
            "other-risks-reset": ("presenter-edl", "video", start_ms),
            "lesson-reset": ("presenter-edl", "video", start_ms),
            "execution-rules": ("graphic-execution-rules", "image", None),
            "spread-limit": ("graphic-spread-limit", "image", None),
            "pause-control": ("graphic-pause-control", "image", None),
            "confirmation-control": (
                "graphic-confirmation-control",
                "image",
                None,
            ),
            "headline-proof": ("evidence-headline-proof", "image", None),
            "full-release-proof": (
                "evidence-bls-overview",
                "image",
                None,
            ),
            "clean-cta": ("presenter-edl", "video", start_ms),
        }
        if editorial == "basket-components-grid":
            evidence_end_ms = min(end_ms, start_ms + 440)
            layers.append(
                layer(
                    identifier="grid-source-overview",
                    shot_id=shot_id,
                    start_ms=start_ms,
                    end_ms=evidence_end_ms,
                    source_role="direct-evidence",
                    kind="image",
                    asset_id="evidence-bls-overview",
                    z_index=40,
                    start_scale=1,
                    end_scale=1.02,
                )
            )
            for identifier, asset_id, bounds, source_start in (
                ("grid-food", "licensed-grocery-produce", (0, 0, 540, 960), 2_600),
                ("grid-petrol", "licensed-gas-station-wide", (540, 0, 540, 960), 350),
                ("grid-rent", "licensed-apartment-night", (0, 960, 540, 960), 350),
                ("grid-services", "licensed-finance-workspace", (540, 960, 540, 960), 1_600),
            ):
                layers.append(
                    layer(
                        identifier=identifier,
                        shot_id=shot_id,
                        start_ms=evidence_end_ms,
                        end_ms=end_ms,
                        source_role="licensed-context",
                        kind="video",
                        asset_id=asset_id,
                        bounds=bounds,
                        source_start_ms=source_start,
                        source_end_ms=(
                            source_start + end_ms - evidence_end_ms
                        ),
                        z_index=10,
                        start_scale=1.02,
                        end_scale=1.06,
                    )
                )
            layers.append(
                layer(
                    identifier="grid-labels",
                    shot_id=shot_id,
                    start_ms=evidence_end_ms,
                    end_ms=end_ms,
                    source_role="deterministic-graphic",
                    kind="image",
                    asset_id="graphic-grid-overlay",
                    z_index=30,
                    start_scale=1,
                    end_scale=1,
                )
            )
            continue
        if editorial == "surprise-question":
            layers.extend(
                [
                    layer(
                        identifier="question-market",
                        shot_id=shot_id,
                        start_ms=start_ms,
                        end_ms=end_ms,
                        source_role="licensed-context",
                        kind="video",
                        asset_id="licensed-market-tablet",
                        source_start_ms=500,
                        source_end_ms=500 + end_ms - start_ms,
                        z_index=10,
                        start_scale=1.02,
                        end_scale=1.08,
                    ),
                    layer(
                        identifier="question-overlay",
                        shot_id=shot_id,
                        start_ms=start_ms,
                        end_ms=end_ms,
                        source_role="deterministic-graphic",
                        kind="image",
                        asset_id="graphic-question-overlay",
                        z_index=20,
                        start_scale=1,
                        end_scale=1,
                    ),
                ]
            )
            continue
        asset_id, kind, source_start = definitions[editorial]
        layers.append(
            layer(
                identifier=f"base-{shot_id}",
                shot_id=shot_id,
                start_ms=start_ms,
                end_ms=end_ms,
                source_role=role,
                kind=kind,
                asset_id=asset_id,
                source_start_ms=source_start,
                source_end_ms=(
                    source_start + end_ms - start_ms
                    if source_start is not None
                    else None
                ),
                z_index=10,
                start_scale=1.01,
                end_scale=1.055,
                reference_role=(
                    "secondary-10"
                    if role in {"direct-evidence", "deterministic-graphic"}
                    else "primary-13"
                ),
            )
        )
    return layers


def evidence_items() -> list[dict[str, Any]]:
    accessed = "2026-08-13T00:00:00Z"
    bls_url = "https://www.bls.gov/news.release/archives/cpi_08122026.htm"
    return [
        {
            "id": "bls-cpi-monthly",
            "claim": "The U.S. all-items CPI rose 0.1% in July 2026.",
            "source_title": "Consumer Price Index - July 2026",
            "source_url": bls_url,
            "source_type": "official",
            "capture_path": "source-captures/bls-release-pre-source.png",
            "accessed_at": accessed,
            "status": "verified",
            "published_at": "2026-08-12T00:00:00Z",
            "visible_excerpt": "increased 0.1 percent on a seasonally adjusted basis in July",
            "license": "Official public data used as editorial evidence",
            "notes": "Rendered from direct official source pixels.",
        },
        {
            "id": "bls-cpi-yearly",
            "claim": "The U.S. all-items CPI rose 3.4% over the 12 months ending July 2026.",
            "source_title": "Consumer Price Index - July 2026",
            "source_url": bls_url,
            "source_type": "official",
            "capture_path": "source-captures/bls-release-pre-source.png",
            "accessed_at": accessed,
            "status": "verified",
            "published_at": "2026-08-12T00:00:00Z",
            "visible_excerpt": "all items index increased 3.4 percent",
            "license": "Official public data used as editorial evidence",
            "notes": "Rendered from direct official source pixels.",
        },
        {
            "id": "bls-energy-gasoline",
            "claim": "Energy fell 1.5% and gasoline fell 2.9% in July 2026.",
            "source_title": "Consumer Price Index - July 2026, Table A",
            "source_url": bls_url,
            "source_type": "official",
            "capture_path": "source-captures/bls-table-a-source.png",
            "accessed_at": accessed,
            "status": "verified",
            "published_at": "2026-08-12T00:00:00Z",
            "visible_excerpt": "Energy -1.5; Gasoline (all types) -2.9",
            "license": "Official public data used as editorial evidence",
            "notes": "Direct table pixels are cropped and highlighted.",
        },
        {
            "id": "bls-shelter-share",
            "claim": "Shelter accounted for roughly two-thirds of the monthly all-items increase.",
            "source_title": "Consumer Price Index - July 2026",
            "source_url": bls_url,
            "source_type": "official",
            "capture_path": "source-captures/bls-release-pre-source.png",
            "accessed_at": accessed,
            "status": "verified",
            "published_at": "2026-08-12T00:00:00Z",
            "visible_excerpt": "accounting for roughly two-thirds of the monthly all items increase",
            "license": "Official public data used as editorial evidence",
            "notes": "The official source removes the need for a secondary Reuters claim.",
        },
        {
            "id": "cnbc-dollar-gained",
            "claim": "The dollar gained as U.S. CPI met expectations on August 12, 2026.",
            "source_title": "Dollar gains, yen slips as U.S. CPI meets expectations",
            "source_url": (
                "https://www.cnbc.com/2026/08/12/"
                "dollar-ticks-up-on-iran-tensions-with-us-data-in-focus.html"
            ),
            "source_type": "editorial",
            "capture_path": "source-captures/cnbc-dollar-cpi-browser.png",
            "accessed_at": accessed,
            "status": "verified",
            "published_at": "2026-08-12T00:00:00Z",
            "visible_excerpt": "Dollar gains ... as U.S. CPI meets expectations",
            "license": "Editorial source pixels used for commentary",
            "notes": "Headline and first paragraph are shown as direct source crops.",
        },
    ]


def prepare_assets() -> tuple[list[dict[str, Any]], dict[str, Path]]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    licensed = OUTPUT / "assets" / "licensed"
    for filename, url in REMOTE_ASSETS.items():
        download_if_missing(licensed / filename, url)

    font_dir = OUTPUT / "assets" / "fonts"
    download_if_missing(
        font_dir / "ShareTechMono-Regular.ttf",
        (
            "https://raw.githubusercontent.com/google/fonts/main/"
            "ofl/sharetechmono/ShareTechMono-Regular.ttf"
        ),
    )
    download_if_missing(
        font_dir / "OFL.txt",
        "https://raw.githubusercontent.com/google/fonts/main/ofl/sharetechmono/OFL.txt",
    )
    download_if_missing(
        font_dir / "Anton-Regular.ttf",
        (
            "https://raw.githubusercontent.com/google/fonts/main/"
            "ofl/anton/Anton-Regular.ttf"
        ),
    )

    presenter = copy_required(
        V1 / "assets" / "presenter" / "presenter-edl.mp4",
        OUTPUT / "assets" / "presenter" / "presenter-edl.mp4",
    )
    dialogue_original = copy_required(
        V1 / "assets" / "audio" / "dialogue-original.wav",
        OUTPUT / "assets" / "audio" / "dialogue-original.wav",
    )
    dialogue_processed = copy_required(
        V1 / "assets" / "audio" / "dialogue-processed.wav",
        OUTPUT / "assets" / "audio" / "dialogue-processed.wav",
    )
    logo = copy_required(
        V1 / "assets" / "brand" / "profit-bricks-logo.png",
        OUTPUT / "assets" / "brand" / "profit-bricks-logo.png",
    )
    shopping = copy_required(
        V1
        / "assets"
        / "licensed"
        / "pexels"
        / "licensed-shopping-cart-4251604.mp4",
        licensed / "pexels-shopping-cart-4251604.mp4",
    )
    rent_keys = copy_required(
        V1
        / "assets"
        / "licensed"
        / "pexels"
        / "licensed-rent-keys-7986204.mp4",
        licensed / "pexels-rent-keys-7986204.mp4",
    )

    capture_dir = OUTPUT / "source-captures"
    capture_dir.mkdir(parents=True, exist_ok=True)
    copy_required(
        V1 / "source-captures" / "cnbc-dollar-cpi-browser.png",
        capture_dir / "cnbc-dollar-cpi-browser.png",
    )
    required_bls = [
        "bls-overview.png",
        "bls-release-pre-source.png",
        "bls-table-a-source.png",
        "bls-cpi-08122026.html",
    ]
    for filename in required_bls:
        path = capture_dir / filename
        if not path.is_file():
            raise FileNotFoundError(
                f"Official BLS capture is missing: {path}"
            )

    evidence = build_evidence_graphics()
    graphics = build_deterministic_graphics()

    music_source = (
        WORKSPACE
        / "storage"
        / "assets"
        / "audio"
        / "technical-reference"
        / "candidates"
        / "feedback-dreams-588.mp3"
    )
    music = OUTPUT / "assets" / "audio" / "music-technical-documentary.wav"
    music.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            "50",
            "-i",
            str(music_source),
            "-af",
            music_filter_chain(),
            "-c:a",
            "pcm_s24le",
            str(music),
        ]
    )

    v8_audio = (
        WORKSPACE
        / "storage"
        / "deliverables"
        / "0806-production-v8-training-parity"
        / "assets"
        / "audio"
    )
    sfx = {}
    for filename in (
        "sfx-click.mp3",
        "sfx-impact.mp3",
        "sfx-paper.mp3",
        "sfx-proof.mp3",
        "sfx-reversal.mp3",
        "sfx-riser.mp3",
        "sfx-snap.mp3",
    ):
        sfx[filename] = copy_required(
            v8_audio / filename,
            OUTPUT / "assets" / "audio" / filename,
        )

    assets = [
        asset(
            identifier="presenter-edl",
            kind="video",
            path=presenter,
            keywords=["presenter", "source footage", "dialogue EDL"],
            provenance="user-provided-edl-preserved",
            license_name="User-provided source footage",
        ),
        asset(
            identifier="dialogue-original",
            kind="audio",
            path=dialogue_original,
            keywords=["untouched narration", "48 kHz"],
            provenance="source-dialogue-edl-master",
            license_name="User-provided source audio",
        ),
        asset(
            identifier="dialogue-processed",
            kind="audio",
            path=dialogue_processed,
            keywords=["processed narration", "48 kHz"],
            provenance="source-dialogue-edl-processed",
            license_name="User-provided source audio",
        ),
        asset(
            identifier="brand-logo-original",
            kind="image",
            path=logo,
            keywords=["Profit Bricks", "brand"],
            provenance="user-provided-brand-asset",
            license_name="User-provided",
        ),
        asset(
            identifier="licensed-fuel-nozzle",
            kind="video",
            path=licensed / "mixkit-fuel-nozzle-31961.mp4",
            keywords=["gasoline nozzle", "petrol pump action"],
            provenance="internet:licensed-stock-video",
            license_name="Mixkit Free License",
            provider="Mixkit",
            remote_id="31961",
            creator="Mixkit contributor",
            source_url=(
                "https://mixkit.co/free-stock-video/"
                "mans-hand-taking-the-fuel-nozzle-at-the-gas-station-31961/"
            ),
            license_url="https://mixkit.co/license/",
            search_query="gasoline nozzle fueling car",
        ),
        asset(
            identifier="licensed-rent-keys",
            kind="video",
            path=rent_keys,
            keywords=["rent", "house keys"],
            provenance="internet:licensed-stock-video",
            license_name="Pexels License",
            provider="Pexels",
            remote_id="7986204",
            creator="SHVETS production",
            source_url="https://www.pexels.com/video/person-holding-keys-7986204/",
            license_url="https://www.pexels.com/license/",
            search_query="apartment keys rent housing",
        ),
        asset(
            identifier="licensed-shopping-cart",
            kind="video",
            path=shopping,
            keywords=["grocery cart", "shopping basket"],
            provenance="internet:licensed-stock-video",
            license_name="Pexels License",
            provider="Pexels",
            remote_id="4251604",
            creator="Peggy Anke",
            source_url=(
                "https://www.pexels.com/video/"
                "food-market-supermarket-foodstuff-4251604/"
            ),
            license_url="https://www.pexels.com/license/",
            search_query="grocery shopping cart basket",
        ),
        asset(
            identifier="licensed-grocery-produce",
            kind="video",
            path=licensed / "pexels-grocery-produce-8027657.mp4",
            keywords=["food prices", "grocery basket"],
            provenance="internet:licensed-stock-video",
            license_name="Pexels License",
            provider="Pexels",
            remote_id="8027657",
            creator="Pexels contributor",
            source_url="https://www.pexels.com/video/food-healthy-man-people-8027657/",
            license_url="https://www.pexels.com/license/",
            search_query="grocery shopping basket supermarket",
        ),
        asset(
            identifier="licensed-apartment-facade",
            kind="video",
            path=licensed / "pexels-apartment-facade-34641787.mp4",
            keywords=["apartments", "shelter", "housing"],
            provenance="internet:licensed-stock-video",
            license_name="Pexels License",
            provider="Pexels",
            remote_id="34641787",
            creator="Nothing Ahead",
            source_url=(
                "https://www.pexels.com/video/"
                "modern-urban-apartment-building-facade-34641787/"
            ),
            license_url="https://www.pexels.com/license/",
            search_query="apartment rent housing building",
        ),
        asset(
            identifier="licensed-apartment-aerial",
            kind="video",
            path=licensed / "pexels-apartment-aerial-32107131.mp4",
            keywords=["residential towers", "housing costs"],
            provenance="internet:licensed-stock-video",
            license_name="Pexels License",
            provider="Pexels",
            remote_id="32107131",
            creator="Toàn BDS",
            source_url=(
                "https://www.pexels.com/video/"
                "aerial-view-of-modern-residential-towers-32107131/"
            ),
            license_url="https://www.pexels.com/license/",
            search_query="apartment rent housing building",
        ),
        asset(
            identifier="licensed-trader-monitor",
            kind="video",
            path=licensed / "pexels-trader-monitor-8480284.mp4",
            keywords=["market positioning", "trading screen"],
            provenance="internet:licensed-stock-video",
            license_name="Pexels License",
            provider="Pexels",
            remote_id="8480284",
            creator="ArtHouse Studio",
            source_url=(
                "https://www.pexels.com/video/"
                "person-looking-a-stock-market-8480284/"
            ),
            license_url="https://www.pexels.com/license/",
            search_query="stock market trader screens dollar reaction",
        ),
        asset(
            identifier="licensed-finance-workspace",
            kind="video",
            path=licensed / "pexels-finance-workspace-37616121.mp4",
            keywords=["rate expectations", "financial analysis"],
            provenance="internet:licensed-stock-video",
            license_name="Pexels License",
            provider="Pexels",
            remote_id="37616121",
            creator="Pexels contributor",
            source_url=(
                "https://www.pexels.com/video/"
                "professional-financial-analysis-workspace-37616121/"
            ),
            license_url="https://www.pexels.com/license/",
            search_query="stock market trader screens dollar reaction",
        ),
        asset(
            identifier="licensed-gas-station-night",
            kind="video",
            path=licensed / "pexels-gas-station-night-35823379.mp4",
            keywords=["gas station", "petrol", "night", "rain"],
            provenance="internet:licensed-stock-video",
            license_name="Pexels License",
            provider="Pexels",
            remote_id="35823379",
            creator="Orhan Pergel",
            source_url=(
                "https://www.pexels.com/video/"
                "moody-night-gas-station-scene-with-rain-35823379/"
            ),
            license_url="https://www.pexels.com/license/",
            search_query="gas station night pump",
        ),
        asset(
            identifier="licensed-gas-station-wide",
            kind="video",
            path=licensed / "pexels-gas-station-wide-25397939.mp4",
            keywords=["gas station", "petrol", "moving cars", "wide shot"],
            provenance="internet:licensed-stock-video",
            license_name="Pexels License",
            provider="Pexels",
            remote_id=SELECTED_FUEL_WIDE_ID,
            creator="Matheus Bertelli",
            source_url=(
                "https://www.pexels.com/video/"
                "a-gas-station-at-night-with-cars-parked-in-front-25397939/"
            ),
            license_url="https://www.pexels.com/license/",
            search_query="gasoline pump fueling car close up",
        ),
        asset(
            identifier="licensed-gasoline-action",
            kind="video",
            path=licensed / "pexels-gasoline-action-16567388.mp4",
            keywords=["gas station", "motorcycle", "petrol pump", "action"],
            provenance="internet:licensed-stock-video",
            license_name="Pexels License",
            provider="Pexels",
            remote_id=SELECTED_FUEL_ACTION_ID,
            creator="paashuu",
            source_url=(
                "https://www.pexels.com/video/"
                "a-motorcycle-is-parked-at-a-gas-station-16567388/"
            ),
            license_url="https://www.pexels.com/license/",
            search_query="gasoline pump fueling car close up",
        ),
        asset(
            identifier="licensed-grocery-market",
            kind="video",
            path=licensed / "pexels-grocery-market-36108473.mp4",
            keywords=["grocery market", "shopping", "food prices"],
            provenance="internet:licensed-stock-video",
            license_name="Pexels License",
            provider="Pexels",
            remote_id="36108473",
            creator="Airam Dato-on",
            source_url=(
                "https://www.pexels.com/video/"
                "busy-urban-market-shopping-in-grocery-aisle-36108473/"
            ),
            license_url="https://www.pexels.com/license/",
            search_query="grocery store dark cinematic",
        ),
        asset(
            identifier="licensed-apartment-night",
            kind="video",
            path=licensed / "pexels-apartment-night-6016323.mp4",
            keywords=["apartment windows", "rent", "housing", "night"],
            provenance="internet:licensed-stock-video",
            license_name="Pexels License",
            provider="Pexels",
            remote_id="6016323",
            creator="Miqayel Harutyunyan",
            source_url=(
                "https://www.pexels.com/video/"
                "apartment-building-lights-6016323/"
            ),
            license_url="https://www.pexels.com/license/",
            search_query="apartment building night city",
        ),
        asset(
            identifier="licensed-market-tablet",
            kind="video",
            path=licensed / "pexels-market-tablet-35606106.mp4",
            keywords=["market analysis", "tablet", "dollar reaction"],
            provenance="internet:licensed-stock-video",
            license_name="Pexels License",
            provider="Pexels",
            remote_id="35606106",
            creator="Jakub Zerdzicki",
            source_url=(
                "https://www.pexels.com/video/"
                "professional-trading-analysis-on-tablet-and-desktop-35606106/"
            ),
            license_url="https://www.pexels.com/license/",
            search_query="stock market screen dark",
        ),
    ]

    evidence_asset_specs = {
        "evidence-bls-overview": evidence["bls-overview"],
        "evidence-bls-identity": evidence["bls-identity"],
        "evidence-bls-monthly-excerpt": evidence["bls-monthly"],
        "evidence-bls-monthly-number": evidence["bls-monthly-number"],
        "evidence-bls-yearly-excerpt": evidence["bls-yearly"],
        "evidence-bls-yearly-number": evidence["bls-yearly-number"],
        "evidence-bls-energy-table": evidence["bls-energy"],
        "evidence-bls-gasoline-number": evidence["bls-gasoline-number"],
        "evidence-bls-shelter": evidence["bls-shelter"],
        "evidence-cnbc-headline": evidence["cnbc-headline"],
        "evidence-cnbc-paragraph": evidence["cnbc-paragraph"],
        "evidence-cnbc-rates": evidence["cnbc-rates"],
        "evidence-headline-proof": evidence["headline-proof"],
        "evidence-full-release-proof": evidence["full-release-proof"],
        "evidence-headline-vs-full": evidence["headline-vs-full"],
    }
    for identifier, path in evidence_asset_specs.items():
        assets.append(
            asset(
                identifier=identifier,
                kind="image",
                path=path,
                keywords=["direct evidence", identifier],
                provenance="direct-source-pixel-editorial-crop",
                license_name="Official/editorial source pixels used for commentary",
            )
        )
    graphic_asset_specs = {
        "graphic-actual-forecast": graphics["contrast"],
        "graphic-question": graphics["question"],
        "graphic-safeguards": graphics["safeguards"],
        "graphic-grid-overlay": graphics["grid-overlay"],
        "graphic-split-divider": graphics["split-divider"],
        "graphic-actual-match": graphics["actual-match"],
        "graphic-inside-story": graphics["inside-story"],
        "graphic-question-overlay": graphics["question-overlay"],
        "graphic-execution-rules": graphics["execution-rules"],
        "graphic-spread-limit": graphics["spread-limit"],
        "graphic-pause-control": graphics["pause-control"],
        "graphic-confirmation-control": graphics[
            "confirmation-control"
        ],
    }
    for identifier, path in graphic_asset_specs.items():
        assets.append(
            asset(
                identifier=identifier,
                kind="image",
                path=path,
                keywords=["deterministic editorial graphic", identifier],
                provenance="deterministic-original-graphic",
                license_name="Original editorial graphic",
            )
        )
    assets.append(
        asset(
            identifier="music-technical-documentary",
            kind="audio",
            path=music,
            keywords=["95 BPM", "documentary", "technical", "vocal-free"],
            provenance="internet:licensed-stock-audio",
            license_name="Mixkit Free License",
            provider="Mixkit",
            remote_id="588",
            creator="Mixkit contributor",
            source_url="https://mixkit.co/free-stock-music/",
            license_url="https://mixkit.co/license/",
            search_query="restrained documentary technology music",
        )
    )
    for filename, path in sfx.items():
        identifier = filename.removesuffix(".mp3")
        assets.append(
            asset(
                identifier=identifier,
                kind="audio",
                path=path,
                keywords=["semantic sound effect", identifier],
                provenance="licensed-production-sfx",
                license_name="Production asset with retained provenance",
            )
        )
    paths = {
        "presenter": presenter,
        "dialogue-original": dialogue_original,
        "dialogue-processed": dialogue_processed,
        "logo": logo,
        "music": music,
    }
    return assets, paths


def build_audio_spec(base_audio: dict[str, Any]) -> dict[str, Any]:
    audio = dict(base_audio)
    audio["music_gain_automation"] = [
        dict(window)
        for window in base_audio.get("music_gain_automation", [])
    ]
    audio.update(
        {
            "integrated_lufs": -14.2,
            "true_peak_dbtp": -1.2,
            "target_lra_lu": 2.8,
            "music_bpm": 95,
            "dialogue_asset_id": "dialogue-original",
            "music_asset_id": "music-technical-documentary",
            "music_duck_db": 6.0,
            "music_base_gain_db": -20.0,
            "sfx_asset_ids": [
                "sfx-click",
                "sfx-impact",
                "sfx-paper",
                "sfx-proof",
                "sfx-reversal",
                "sfx-riser",
                "sfx-snap",
            ],
            "sfx_cues": [
                {
                    "id": "hook-settle",
                    "asset_id": "sfx-impact",
                    "start_ms": 220,
                    "source_start_ms": 220,
                    "duration_ms": 100,
                    "volume": 0.35,
                    "gain_db": -18.0,
                    "kind": "impact",
                    "reason": "fuel action settles after the opening word",
                },
                {
                    "id": "official-source",
                    "asset_id": "sfx-paper",
                    "start_ms": 4_560,
                    "source_start_ms": 460,
                    "duration_ms": 100,
                    "volume": 0.35,
                    "gain_db": -20.0,
                    "kind": "whoosh",
                    "reason": "official BLS source reveal",
                },
                {
                    "id": "basket-cut",
                    "asset_id": "sfx-snap",
                    "start_ms": 7_130,
                    "source_start_ms": 0,
                    "duration_ms": 100,
                    "volume": 0.35,
                    "gain_db": -20.0,
                    "kind": "click",
                    "reason": "shopping basket change",
                },
                {
                    "id": "basket-proof",
                    "asset_id": "sfx-snap",
                    "start_ms": 9_250,
                    "source_start_ms": 0,
                    "duration_ms": 80,
                    "volume": 0.35,
                    "gain_db": -8.0,
                    "kind": "click",
                    "reason": "basket-components proof cut",
                },
                {
                    "id": "basket-grid-accent",
                    "asset_id": "sfx-proof",
                    "start_ms": 10_220,
                    "source_start_ms": 260,
                    "duration_ms": 70,
                    "volume": 0.3,
                    "gain_db": -10.5,
                    "kind": "impact",
                    "reason": "basket grid resolves into the official proof",
                },
                {
                    "id": "monthly-proof",
                    "asset_id": "sfx-proof",
                    "start_ms": 11_090,
                    "source_start_ms": 340,
                    "duration_ms": 80,
                    "volume": 0.25,
                    "gain_db": -12.0,
                    "kind": "impact",
                    "reason": "official monthly CPI proof",
                },
                {
                    "id": "yearly-lead",
                    "asset_id": "sfx-proof",
                    "start_ms": 12_970,
                    "source_start_ms": 260,
                    "duration_ms": 70,
                    "volume": 0.3,
                    "gain_db": -10.5,
                    "kind": "impact",
                    "reason": "monthly proof changes to yearly evidence",
                },
                {
                    "id": "yearly-proof",
                    "asset_id": "sfx-proof",
                    "start_ms": 13_620,
                    "source_start_ms": 260,
                    "duration_ms": 80,
                    "volume": 0.3,
                    "gain_db": -10.5,
                    "kind": "impact",
                    "reason": "official yearly CPI proof",
                },
                {
                    "id": "energy-proof",
                    "asset_id": "sfx-click",
                    "start_ms": 21_060,
                    "source_start_ms": 40,
                    "duration_ms": 90,
                    "volume": 0.35,
                    "gain_db": -20.0,
                    "kind": "click",
                    "reason": "BLS energy table macro",
                },
                {
                    "id": "shelter-proof",
                    "asset_id": "sfx-snap",
                    "start_ms": 25_720,
                    "source_start_ms": 0,
                    "duration_ms": 80,
                    "volume": 0.35,
                    "gain_db": -8.0,
                    "kind": "click",
                    "reason": "shelter contribution proof cut",
                },
                {
                    "id": "cnbc-proof",
                    "asset_id": "sfx-paper",
                    "start_ms": 28_420,
                    "source_start_ms": 460,
                    "duration_ms": 100,
                    "volume": 0.35,
                    "gain_db": -20.0,
                    "kind": "whoosh",
                    "reason": "CNBC source reveal",
                },
                {
                    "id": "question-turn",
                    "asset_id": "sfx-reversal",
                    "start_ms": 30_040,
                    "source_start_ms": 220,
                    "duration_ms": 110,
                    "volume": 0.35,
                    "gain_db": -19.0,
                    "kind": "impact",
                    "reason": "question and market-reaction turn",
                },
                {
                    "id": "market-reaction-cut",
                    "asset_id": "sfx-proof",
                    "start_ms": 31_400,
                    "source_start_ms": 260,
                    "duration_ms": 70,
                    "volume": 0.3,
                    "gain_db": -10.5,
                    "kind": "impact",
                    "reason": "question plate cuts to direct market evidence",
                },
                {
                    "id": "spread-control",
                    "asset_id": "sfx-click",
                    "start_ms": 40_290,
                    "source_start_ms": 40,
                    "duration_ms": 70,
                    "volume": 0.35,
                    "gain_db": -21.0,
                    "kind": "click",
                    "reason": "spread limit control locks",
                },
                {
                    "id": "pause-control",
                    "asset_id": "sfx-snap",
                    "start_ms": 40_670,
                    "source_start_ms": 0,
                    "duration_ms": 70,
                    "volume": 0.35,
                    "gain_db": -21.0,
                    "kind": "click",
                    "reason": "pause control locks",
                },
                {
                    "id": "confirmation-control",
                    "asset_id": "sfx-click",
                    "start_ms": 41_495,
                    "source_start_ms": 40,
                    "duration_ms": 70,
                    "volume": 0.35,
                    "gain_db": -21.0,
                    "kind": "click",
                    "reason": "confirmation control locks",
                },
                {
                    "id": "cta-lift",
                    "asset_id": "sfx-riser",
                    "start_ms": 45_280,
                    "source_start_ms": 500,
                    "duration_ms": 180,
                    "volume": 0.35,
                    "gain_db": -21.0,
                    "kind": "riser",
                    "reason": "clean CTA lift after the final spoken onset",
                },
            ],
        }
    )
    semantic_cue_ids = {
        "hook-settle",
        "official-source",
        "basket-proof",
        "monthly-proof",
        "yearly-proof",
        "shelter-proof",
        "question-turn",
        "cta-lift",
    }
    audio["sfx_cues"] = [
        cue
        for cue in audio["sfx_cues"]
        if cue["id"] in semantic_cue_ids
    ]
    for automation in audio["music_gain_automation"]:
        automation["gain_db"] = -6.0
        automation["reason"] = (
            "Duck restrained documentary music beneath narration"
        )
    return audio


def main() -> int:
    assets, paths = prepare_assets()
    v1_blueprint = json.loads(
        (V1 / "blueprint.json").read_text(encoding="utf-8")
    )
    transcript = json.loads(
        (V1 / "transcript-aligned.json").read_text(encoding="utf-8")
    )
    dialogue_edl_payload = json.loads(
        (V1 / "dialogue-edl.json").read_text(encoding="utf-8")
    )
    caption_pages = build_caption_pages(transcript)
    layers = build_layers()
    evidence = evidence_items()

    audio = build_audio_spec(v1_blueprint["audio"])

    kinetic_text = [
        {
            "id": "hook-petrol",
            "start_ms": 220,
            "end_ms": 1_280,
            "text": "PETROL DOWN.",
            "family": "micro-source",
            "x": 540,
            "y": 210,
            "max_width": 920,
            "align": "center",
            "animation": "hard-cut",
            "accent": None,
            "secondary_text": None,
            "rotation_deg": 0.0,
            "z_index": 60,
        },
        {
            "id": "hook-rent",
            "start_ms": 1_520,
            "end_ms": 3_050,
            "text": "RENT STILL HURTS.",
            "family": "micro-source",
            "x": 540,
            "y": 930,
            "max_width": 920,
            "align": "center",
            "animation": "hard-cut",
            "accent": None,
            "secondary_text": None,
            "rotation_deg": 0.0,
            "z_index": 60,
        },
        {
            "id": "cta-follow",
            "start_ms": 44_800,
            "end_ms": 45_500,
            "text": "FOLLOW FOR FOREX",
            "family": "micro-source",
            "x": 540,
            "y": 1_710,
            "max_width": 860,
            "align": "center",
            "animation": "hard-cut",
            "accent": None,
            "secondary_text": None,
            "rotation_deg": 0.0,
            "z_index": 60,
        },
    ]
    motion_events = [
        {
            "id": f"motion-{index:02d}",
            "start_ms": start,
            "end_ms": min(end, start + 620),
            "kind": (
                "proof-punch"
                if role == "direct-evidence"
                else "punch-crop"
                if role in {"presenter", "licensed-context"}
                else "highlight-sweep"
            ),
            "target_id": (
                next(
                    item["id"]
                    for item in layers
                    if item["shot_id"] == f"shot-{index:02d}"
                )
            ),
            "intensity": 0.45,
            "direction": "none",
        }
        for index, ((role, _), start, end) in enumerate(
            zip(SHOT_ROLES, BOUNDARIES[:-1], BOUNDARIES[1:]),
            start=1,
        )
    ]

    blueprint_payload = {
        "version": v1_blueprint.get("version", 2),
        "profile": v1_blueprint.get("profile", "v2"),
        "source_filename": SOURCE.name,
        "source_metadata": v1_blueprint["source_metadata"],
        "output": v1_blueprint["output"],
        "duration_ms": DURATION_MS,
        "assets": assets,
        "layers": layers,
        "caption_pages": caption_pages,
        "audio": audio,
        "flow_shots": [],
        "evidence": evidence,
        "reference_profile": "technical-reference",
        "story_profile": "cpi-inflation-training",
        "style_reference_path": str(PRIMARY_REFERENCE),
        "voice_policy": "reference-compressed",
        "dialogue_edl": dialogue_edl_payload["segments"],
        "kinetic_text_cues": kinetic_text,
        "motion_events": motion_events,
    }
    blueprint = ProductionBlueprint.model_validate(blueprint_payload)
    write_json(OUTPUT / "blueprint.json", blueprint)
    write_json(OUTPUT / "transcript-aligned.json", transcript)
    copy_required(V1 / "dialogue-edl.json", OUTPUT / "dialogue-edl.json")
    write_json(OUTPUT / "evidence.json", evidence)
    write_json(
        OUTPUT / "caption-plan.json",
        {
            "profile": "technical-reference",
            "caption_coverage_target": [0.65, 0.75],
            "continuous_karaoke": False,
            "pages": caption_pages,
        },
    )
    write_json(
        OUTPUT / "kinetic-text-plan.json",
        {
            "profile": "training-news",
            "continuous_captions": True,
            "cues": kinetic_text,
        },
    )
    write_json(OUTPUT / "motion-events.json", motion_events)
    write_json(
        OUTPUT / "sound-cue-sheet.json",
        {
            "profile": "training-news",
            "music_bpm": 95,
            "target_lufs": -14.2,
            "target_true_peak_dbtp": -1.2,
            "target_lra_lu": 2.8,
            "music_base_gain_db": -18.0,
            "music_duck_db": 7.0,
            "cues": audio["sfx_cues"],
            "speech_protection_windows": audio[
                "speech_protection_windows"
            ],
        },
    )

    layer_ids: dict[str, list[str]] = {}
    for item in layers:
        layer_ids.setdefault(item["shot_id"], []).append(item["id"])
    evidence_by_role = {
        "bls-overview": ["bls-cpi-monthly", "bls-cpi-yearly"],
        "bls-cpi-identity": ["bls-cpi-monthly"],
        "monthly-proof": ["bls-cpi-monthly"],
        "yearly-proof": ["bls-cpi-yearly"],
        "energy-gasoline-proof": ["bls-energy-gasoline"],
        "shelter-source-proof": ["bls-shelter-share"],
        "cnbc-headline": ["cnbc-dollar-gained"],
        "cnbc-paragraph": ["cnbc-dollar-gained"],
        "headline-vs-full-release": [
            "cnbc-dollar-gained",
            "bls-cpi-monthly",
            "bls-shelter-share",
        ],
    }
    storyboard = []
    for index, ((role, editorial), start, end) in enumerate(
        zip(SHOT_ROLES, BOUNDARIES[:-1], BOUNDARIES[1:]),
        start=1,
    ):
        shot_id = f"shot-{index:02d}"
        storyboard.append(
            {
                "id": shot_id,
                "start_ms": start,
                "end_ms": end,
                "source_role": role,
                "editorial_role": editorial,
                "reference_role": (
                    "secondary-10"
                    if role in {"direct-evidence", "deterministic-graphic"}
                    else "primary-13"
                ),
                "layer_ids": layer_ids[shot_id],
                "caption_page_count": sum(
                    page["start_ms"] < end and page["end_ms"] > start
                    for page in caption_pages
                ),
                "evidence_ids": evidence_by_role.get(editorial, []),
            }
        )
    write_json(OUTPUT / "storyboard.json", storyboard)
    write_json(OUTPUT / "flow-shot-plan.json", [])
    write_json(
        OUTPUT / "flow-instructions.json",
        {
            "disabled": True,
            "reason": (
                "Training-reference parity for this factual news story uses "
                "real source pixels and licensed moving footage only."
            ),
        },
    )

    manifest = {
        "assets": [
            {
                **item,
                "checksum_sha256": sha256(OUTPUT / item["path"]),
            }
            for item in assets
        ]
    }
    write_json(OUTPUT / "asset-manifest.json", manifest)
    write_json(
        OUTPUT / "capture-manifest.json",
        {
            "source": {
                "path": str(SOURCE),
                "checksum_sha256": sha256(SOURCE),
                "read_only": True,
            },
            "official_bls_html": {
                "path": "source-captures/bls-cpi-08122026.html",
                "checksum_sha256": sha256(
                    OUTPUT
                    / "source-captures"
                    / "bls-cpi-08122026.html"
                ),
                "source_url": (
                    "https://www.bls.gov/news.release/archives/"
                    "cpi_08122026.htm"
                ),
            },
            "official_bls_release_pixels": {
                "path": "source-captures/bls-release-pre-source.png",
                "checksum_sha256": sha256(
                    OUTPUT
                    / "source-captures"
                    / "bls-release-pre-source.png"
                ),
            },
            "official_bls_table_pixels": {
                "path": "source-captures/bls-table-a-source.png",
                "checksum_sha256": sha256(
                    OUTPUT
                    / "source-captures"
                    / "bls-table-a-source.png"
                ),
            },
            "cnbc_editorial_capture": {
                "path": "source-captures/cnbc-dollar-cpi-browser.png",
                "checksum_sha256": sha256(
                    OUTPUT
                    / "source-captures"
                    / "cnbc-dollar-cpi-browser.png"
                ),
            },
        },
    )

    caption_coverage_ms = sum(
        page["end_ms"] - page["start_ms"] for page in caption_pages
    )
    durations = [
        end - start
        for start, end in zip(BOUNDARIES[:-1], BOUNDARIES[1:])
    ]
    sorted_durations = sorted(durations)
    median_duration = (
        sorted_durations[len(sorted_durations) // 2]
        if len(sorted_durations) % 2
        else (
            sorted_durations[len(sorted_durations) // 2 - 1]
            + sorted_durations[len(sorted_durations) // 2]
        )
        / 2
    )
    write_json(
        OUTPUT / "reference-profile.json",
        {
            "name": "0813-cpi-training-parity",
            "primary_reference": {
                "number": 13,
                "path": str(PRIMARY_REFERENCE),
                "checksum_sha256": sha256(PRIMARY_REFERENCE),
                "role": "news/evidence pacing, full-frame source grammar, resets",
            },
            "secondary_reference": {
                "number": 10,
                "path": str(SECONDARY_REFERENCE),
                "checksum_sha256": sha256(SECONDARY_REFERENCE),
                "role": "direct-source evidence, compact mono captions, diagrams",
            },
            "targets": {
                "shots": len(SHOT_ROLES),
                "hard_cuts": [34, 40],
                "median_shot_ms": [900, 1400],
                "planned_median_shot_ms": median_duration,
                "presenter_pixels": [0.14, 0.22],
                "real_direct_pixels_min": 0.55,
                "caption_coverage": [0.65, 0.75],
                "planned_caption_coverage": round(
                    caption_coverage_ms / DURATION_MS,
                    6,
                ),
                "flow_pixels": 0,
            },
        },
    )
    write_json(
        OUTPUT / "production-settings.json",
        {
            "primary_reference": 13,
            "secondary_reference": 10,
            "reference_profile": "technical-reference",
            "story_profile": "cpi-inflation-training",
            "voice_policy": "reference-compressed",
            "asset_policy": "evidence-first-free-licensed",
            "flow_operation_budget": 0,
            "human_final_approval_required": True,
        },
    )

    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
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
    write_json(
        OUTPUT / "production-job.json",
        {
            "id": "production-0813-training-parity",
            "source_path": str(SOURCE),
            "output_dir": str(OUTPUT),
            "state": "blueprint-ready",
            "primary_reference": 13,
            "secondary_reference": 10,
            "flow_operation_budget": 0,
            "approved_paid_operations": 0,
            "consumed_paid_operations": 0,
            "flow_profile": "sahilsharmabybit2",
            "flow_project_id": None,
            "flow_repository": (
                r"C:\Users\HPUSER\Documents\ChatGPT\New project"
            ),
            "artifacts": artifacts,
            "accepted_clips": [],
            "automated_pass": False,
            "human_approved": False,
            "final_reviewer": None,
            "state_history": [
                {
                    "state": "analyzing",
                    "at": now,
                    "detail": "V1 training-parity gap audit completed.",
                },
                {
                    "state": "blueprint-ready",
                    "at": now,
                    "detail": (
                        "Reference-13 news grammar and reference-10 "
                        "evidence/caption blueprint persisted."
                    ),
                },
            ],
            "error": None,
            "created_at": now,
            "updated_at": now,
        },
    )

    (OUTPUT / "analysis-report.md").write_text(
        """# 0813 V2 Training-Parity Audit

## Blocked V1 problems

- The opening petrol visual was an EV charging connector, not gasoline.
- The BLS browser capture was an access-denied page.
- Official evidence was redesigned into synthetic cards instead of direct source pixels.
- Presenter footage occupied 59.3% of visible pixels, far above the selected training references.
- Only 13 hard cuts and 2.48-second median shots made the edit feel slow and promotional.
- Continuous gray presenter framing, oversized social text, and 126 BPM techno did not match references #13/#10.
- Caption coverage was materially below the training pattern.

## V2 production correction

- 38 speech-aligned shots with 35 rendered hard cuts.
- Real gasoline-nozzle action, grocery action, housing footage, market footage, direct BLS/CNBC evidence, and restrained diagrams.
- Direct BLS overview, paragraph, table, and shelter-source crops.
- Presenter reduced to connective resets and small split/PIP roles.
- Share Tech Mono phrase captions over roughly 70% of runtime.
- Restrained 95 BPM documentary-tech music and speech-protected semantic SFX.
- Flow and generated factual imagery remain disabled.

**Verdict: proceed to render and pixel/audio verification.**
""",
        encoding="utf-8",
    )
    (OUTPUT / "edit-plan.md").write_text(
        """# 0813 V2 Edit Plan

Primary grammar: training reference #13 for news/evidence sequencing.
Secondary grammar: training reference #10 for source-pixel evidence,
compact mono captions, dark explanation frames, and restrained sound.

The edit opens on real fuel action, moves immediately into rent/housing,
shows official BLS evidence as overview → CPI macros → table macro, then
uses CNBC source pixels for the dollar reaction. Presenter footage is used
only for resets, the question, the lesson, and the CTA. The final payoff
contrasts the market headline with the full official release.
""",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "shots": len(SHOT_ROLES),
                "caption_pages": len(caption_pages),
                "caption_coverage": round(
                    caption_coverage_ms / DURATION_MS,
                    6,
                ),
                "blueprint": "blueprint.json",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

from imageio_ffmpeg import get_ffmpeg_exe
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


SERVER_DIR = Path(__file__).resolve().parent
WORKSPACE = SERVER_DIR.parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from app.editor.analysis import probe_video  # noqa: E402
from app.editor.production_v4 import ProductionStore  # noqa: E402
from app.editor.training_reference_0806 import (  # noqa: E402
    DURATION_MS,
    align_caption_specs,
    build_caption_specs,
    build_shot_schedule,
    create_blueprint,
    estimate_role_coverage,
)
from app.models import AssetRef, EvidenceItem  # noqa: E402
from app.production_models import (  # noqa: E402
    ProductionJobRecord,
    ProductionStateEvent,
)


SOURCE = Path(r"D:\Downloads\0806.mp4")
OUTPUT_DIR = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0806-production-v7-training-reference"
)
V4_DIR = WORKSPACE / "storage" / "deliverables" / "0806-production-v4"
V6_DIR = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0806-production-v6-social-kinetic-fast"
)
LICENSED_ROOT = WORKSPACE / "storage" / "assets" / "licensed" / "mixkit"
AUDIO_LIBRARY = (
    WORKSPACE / "storage" / "assets" / "audio" / "social-kinetic"
)
MUSIC_LIBRARY = (
    WORKSPACE
    / "storage"
    / "assets"
    / "audio"
    / "technical-reference"
    / "candidates"
)
BRAND_LOGO = (
    WORKSPACE
    / "storage"
    / "assets"
    / "brand"
    / "profit-bricks-forex-automation.png"
)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_file(source: Path, destination: Path) -> Path:
    if not source.is_file():
        raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def relative(path: Path) -> str:
    return path.relative_to(OUTPUT_DIR).as_posix()


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        Path(r"C:\Windows\Fonts") / name,
        Path(r"C:\Windows\Fonts\arial.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default(size=size)


def fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    font_name: str,
    initial_size: int,
    min_size: int,
    max_width: int,
) -> ImageFont.FreeTypeFont:
    size = initial_size
    while size >= min_size:
        candidate = font(font_name, size)
        bounds = draw.multiline_textbbox(
            (0, 0),
            text,
            font=candidate,
            spacing=-8,
            align="center",
        )
        if bounds[2] - bounds[0] <= max_width:
            return candidate
        size -= 2
    return font(font_name, min_size)


def prepare_graphics() -> dict[str, Path]:
    graphics = OUTPUT_DIR / "assets" / "graphics"
    graphics.mkdir(parents=True, exist_ok=True)

    hook = Image.new("RGBA", (900, 330), (0, 0, 0, 0))
    hook_draw = ImageDraw.Draw(hook)
    hook_font = fit_text(
        hook_draw,
        "FOREX TRADING\nROBOT?",
        font_name="georgiab.ttf",
        initial_size=112,
        min_size=88,
        max_width=850,
    )
    hook_draw.multiline_text(
        (450, 171),
        "FOREX TRADING\nROBOT?",
        font=hook_font,
        anchor="mm",
        align="center",
        spacing=-10,
        fill=(255, 255, 255, 255),
        stroke_width=3,
        stroke_fill=(0, 0, 0, 210),
    )
    hook_path = graphics / "hook-title.png"
    hook.save(hook_path)

    dark = Image.new("RGB", (1080, 1920), "#080C10")
    dark_draw = ImageDraw.Draw(dark, "RGBA")
    for y in range(0, 1920, 96):
        dark_draw.line((0, y, 1080, y), fill=(71, 116, 129, 18), width=1)
    for x in range(0, 1080, 96):
        dark_draw.line((x, 0, x, 1920), fill=(71, 116, 129, 14), width=1)
    dark_draw.ellipse(
        (-420, 560, 1_280, 2_260),
        outline=(53, 189, 202, 30),
        width=4,
    )
    dark_path = graphics / "dark-backdrop.png"
    dark.save(dark_path)

    light = Image.new("RGB", (1080, 1920), "#F5F4EF")
    light_draw = ImageDraw.Draw(light, "RGBA")
    for y in range(0, 1920, 120):
        light_draw.line((0, y, 1080, y), fill=(30, 50, 58, 12), width=1)
    light_draw.ellipse(
        (-360, -240, 1_220, 1_340),
        outline=(44, 150, 157, 28),
        width=5,
    )
    light_path = graphics / "light-backdrop.png"
    light.save(light_path)

    cool = Image.new("RGB", (1080, 1920), "#8FAEB4")
    cool_draw = ImageDraw.Draw(cool, "RGBA")
    for y in range(0, 1920, 120):
        cool_draw.line((0, y, 1080, y), fill=(17, 59, 66, 28), width=1)
    for x in range(0, 1080, 120):
        cool_draw.line((x, 0, x, 1920), fill=(17, 59, 66, 22), width=1)
    cool_draw.ellipse(
        (-360, 860, 1_260, 2_480),
        outline=(23, 76, 83, 42),
        width=5,
    )
    cool_draw.rectangle(
        (0, 0, 1080, 150),
        fill=(13, 48, 54, 46),
    )
    cool_path = graphics / "cool-backdrop.png"
    cool.save(cool_path)

    mono = font("consola.ttf", 42)
    mono_small = font("consola.ttf", 28)
    sans_bold = font("arialbd.ttf", 62)
    sans = font("arial.ttf", 36)

    wrong = Image.new("RGB", (1080, 1920), "#090D12")
    wrong_draw = ImageDraw.Draw(wrong, "RGBA")
    wrong_draw.rounded_rectangle(
        (84, 180, 996, 1_735),
        radius=34,
        fill=(10, 17, 23, 250),
        outline=(82, 171, 185, 118),
        width=2,
    )
    wrong_draw.text(
        (120, 230),
        "RULE ENGINE",
        font=mono_small,
        fill=(116, 214, 223, 255),
    )
    wrong_draw.rounded_rectangle(
        (130, 350, 950, 690),
        radius=22,
        fill=(18, 25, 32, 255),
        outline=(255, 255, 255, 28),
        width=2,
    )
    code_lines = [
        ("if (risk > limit) {", (222, 225, 229, 255)),
        ("    executeRule();", (111, 219, 228, 255)),
        ("}", (222, 225, 229, 255)),
    ]
    for index, (line, color) in enumerate(code_lines):
        wrong_draw.text(
            (175, 405 + index * 72),
            line,
            font=mono,
            fill=color,
        )
    wrong_draw.line(
        (540, 690, 540, 920),
        fill=(179, 190, 197, 190),
        width=5,
    )
    wrong_draw.polygon(
        [(540, 865), (410, 995), (540, 1_125), (670, 995)],
        fill=(18, 25, 32, 255),
        outline=(240, 194, 70, 255),
    )
    wrong_draw.text(
        (540, 995),
        "RULE?",
        font=mono_small,
        fill=(255, 223, 115, 255),
        anchor="mm",
    )
    wrong_draw.line(
        (475, 1_060, 280, 1_300),
        fill=(74, 205, 187, 255),
        width=8,
    )
    wrong_draw.line(
        (605, 1_060, 800, 1_300),
        fill=(232, 74, 83, 255),
        width=8,
    )
    wrong_draw.rounded_rectangle(
        (120, 1_300, 460, 1_520),
        radius=22,
        fill=(15, 61, 57, 255),
        outline=(74, 205, 187, 255),
        width=3,
    )
    wrong_draw.rounded_rectangle(
        (620, 1_300, 960, 1_520),
        radius=22,
        fill=(70, 23, 28, 255),
        outline=(232, 74, 83, 255),
        width=3,
    )
    wrong_draw.multiline_text(
        (290, 1_410),
        "RIGHT RULE\nEXPECTED ACTION",
        font=mono_small,
        fill=(236, 244, 241, 255),
        anchor="mm",
        align="center",
        spacing=10,
    )
    wrong_draw.multiline_text(
        (790, 1_410),
        "WRONG RULE\nWRONG ACTION",
        font=mono_small,
        fill=(255, 239, 239, 255),
        anchor="mm",
        align="center",
        spacing=10,
    )
    wrong_path = graphics / "wrong-rule-branch.png"
    wrong.save(wrong_path)

    reversal = Image.new("RGB", (1080, 1920), "#07090D")
    reversal_draw = ImageDraw.Draw(reversal, "RGBA")
    reversal_draw.text(
        (90, 150),
        "RISK REVERSAL",
        font=mono_small,
        fill=(232, 93, 101, 255),
    )
    center = (540, 960)
    for radius, alpha in ((210, 70), (330, 48), (470, 30)):
        reversal_draw.ellipse(
            (
                center[0] - radius,
                center[1] - radius,
                center[0] + radius,
                center[1] + radius,
            ),
            outline=(232, 74, 83, alpha),
            width=3,
        )
    reversal_draw.line(
        (150, 1_350, 405, 760, 650, 490),
        fill=(86, 212, 195, 255),
        width=18,
        joint="curve",
    )
    reversal_draw.polygon(
        [(650, 490), (610, 580), (700, 555)],
        fill=(86, 212, 195, 255),
    )
    reversal_draw.line(
        (650, 490, 775, 980, 905, 1_485),
        fill=(232, 74, 83, 255),
        width=18,
        joint="curve",
    )
    reversal_draw.polygon(
        [(905, 1_485), (850, 1_405), (940, 1_385)],
        fill=(232, 74, 83, 255),
    )
    reversal_draw.text(
        (160, 1_410),
        "HIGH RISK",
        font=sans_bold,
        fill=(243, 245, 246, 255),
    )
    reversal_draw.text(
        (575, 365),
        "RESULT UP",
        font=sans,
        fill=(120, 226, 207, 255),
    )
    reversal_draw.text(
        (650, 1_570),
        "THEN REVERSED",
        font=sans_bold,
        fill=(247, 114, 121, 255),
    )
    reversal_path = graphics / "risk-reversal.png"
    reversal.save(reversal_path)

    rules = Image.new("RGB", (1080, 1920), "#091014")
    rules_draw = ImageDraw.Draw(rules, "RGBA")
    rules_draw.text(
        (90, 150),
        "AUTOMATION LOGIC",
        font=mono_small,
        fill=(108, 215, 224, 255),
    )
    panels = [
        (
            (95, 360, 985, 865),
            "EXECUTION",
            "FOLLOWS THE RULE\nWITHOUT EMOTION",
            (50, 172, 179, 255),
        ),
        (
            (95, 1_050, 985, 1_555),
            "RISK CHOICE",
            "ONLY AS SAFE AS\nTHE RULE DESIGN",
            (220, 76, 84, 255),
        ),
    ]
    for box, title, body, accent in panels:
        rules_draw.rounded_rectangle(
            box,
            radius=28,
            fill=(15, 24, 30, 255),
            outline=accent,
            width=4,
        )
        rules_draw.text(
            (145, box[1] + 70),
            title,
            font=mono,
            fill=accent,
        )
        rules_draw.multiline_text(
            (145, box[1] + 180),
            body,
            font=sans_bold,
            fill=(242, 245, 246, 255),
            spacing=16,
        )
    rules_draw.line(
        (540, 865, 540, 1_050),
        fill=(172, 182, 188, 160),
        width=5,
    )
    rules_draw.polygon(
        [(540, 1_050), (510, 990), (570, 990)],
        fill=(172, 182, 188, 220),
    )
    rules_path = graphics / "rules-versus-risk.png"
    rules.save(rules_path)

    return {
        "graphic-hook-title": hook_path,
        "graphic-dark-backdrop": dark_path,
        "graphic-light-backdrop": light_path,
        "graphic-cool-backdrop": cool_path,
        "graphic-wrong-rule": wrong_path,
        "graphic-risk-reversal": reversal_path,
        "graphic-rules-versus-risk": rules_path,
    }


def prepare_evidence() -> dict[str, Path]:
    source_dir = V4_DIR / "assets" / "evidence"
    output_dir = OUTPUT_DIR / "assets" / "evidence"
    output_dir.mkdir(parents=True, exist_ok=True)

    history_source = source_dir / "metatrader5-atc-history.png"
    risk_source = source_dir / "mql5-atc-2008-risk-readable.png"
    original_history = copy_file(
        history_source,
        output_dir / history_source.name,
    )
    original_risk = copy_file(
        risk_source,
        output_dir / risk_source.name,
    )

    history = Image.open(history_source).convert("RGB")
    risk = Image.open(risk_source).convert("RGB")
    mono_label = font("consola.ttf", 28)
    mono_small = font("consola.ttf", 24)

    overview = Image.new("RGB", (1080, 1920), "#CFE4DF")
    overview_draw = ImageDraw.Draw(overview, "RGBA")
    overview_draw.rectangle((0, 0, 1080, 170), fill=(14, 54, 60, 255))
    overview_draw.text(
        (60, 84),
        "OFFICIAL METAQUOTES PAGE",
        font=mono_label,
        fill=(231, 247, 243, 255),
        anchor="lm",
    )
    overview_draw.rounded_rectangle(
        (48, 220, 1_032, 1_430),
        radius=26,
        fill=(248, 247, 241, 255),
        outline=(28, 88, 92, 70),
        width=3,
    )
    scale = min(930 / history.width, 1_130 / history.height)
    resized = history.resize(
        (round(history.width * scale), round(history.height * scale)),
        Image.Resampling.LANCZOS,
    )
    overview.paste(
        resized,
        ((1080 - resized.width) // 2, 275),
    )
    overview_draw.text(
        (60, 1_770),
        "METATRADER5.COM/EN/AUTOMATED-TRADING",
        font=mono_small,
        fill=(20, 62, 68, 255),
        anchor="lm",
    )
    overview_path = output_dir / "history-source-overview.png"
    overview.save(overview_path)

    championship = Image.new("RGB", (1080, 1920), "#EDE3CC")
    championship_draw = ImageDraw.Draw(championship, "RGBA")
    championship_draw.rectangle((0, 0, 126, 1920), fill=(18, 62, 68, 255))
    championship_draw.text(
        (172, 110),
        "CHAMPIONSHIP HISTORY",
        font=mono_label,
        fill=(20, 62, 68, 255),
    )
    section = ImageEnhance.Contrast(
        history.crop((70, 760, 1_370, 1_020))
    ).enhance(1.08)
    section = section.resize((880, 176), Image.Resampling.LANCZOS)
    championship_draw.rounded_rectangle(
        (150, 250, 1_030, 520),
        radius=20,
        fill=(250, 249, 245, 255),
        outline=(25, 75, 80, 70),
        width=3,
    )
    championship.paste(section, (150, 300))
    title_crop = history.crop((500, 835, 970, 875))
    title_crop = ImageEnhance.Sharpness(title_crop).enhance(1.25)
    title_crop = title_crop.resize((820, 70), Image.Resampling.LANCZOS)
    championship_draw.rounded_rectangle(
        (170, 760, 1_010, 940),
        radius=18,
        fill=(250, 249, 245, 255),
    )
    championship.paste(title_crop, (180, 820))
    years_crop = history.crop((525, 878, 865, 918))
    years_crop = ImageEnhance.Sharpness(years_crop).enhance(1.3)
    years_crop = years_crop.resize((820, 89), Image.Resampling.LANCZOS)
    championship_draw.rectangle(
        (170, 1_095, 1_010, 1_215),
        fill=(246, 220, 94, 105),
        outline=(34, 116, 119, 105),
        width=3,
    )
    championship.paste(years_crop, (180, 1_110))
    championship_draw.text(
        (172, 1_700),
        "SOURCE PIXELS / METAQUOTES",
        font=mono_small,
        fill=(20, 62, 68, 255),
        anchor="lm",
    )
    championship_path = output_dir / "history-source-excerpt.png"
    championship.save(championship_path)

    risk_excerpt = Image.new("RGB", (1080, 1920), "#D8E3EC")
    risk_draw = ImageDraw.Draw(risk_excerpt, "RGBA")
    risk_draw.rectangle((0, 0, 1080, 230), fill=(24, 41, 68, 255))
    risk_draw.text(
        (58, 110),
        "PRIMARY SOURCE / MQL5 ARTICLE 525",
        font=mono_label,
        fill=(219, 240, 250, 255),
        anchor="lm",
    )
    risk_resized = risk.resize((1_000, 346), Image.Resampling.LANCZOS)
    risk_draw.rounded_rectangle(
        (40, 300, 1_040, 686),
        radius=18,
        fill=(249, 248, 243, 255),
        outline=(29, 70, 103, 80),
        width=3,
    )
    risk_excerpt.paste(risk_resized, (40, 320))
    focus = risk.crop((0, 30, risk.width, 225)).convert("RGBA")
    focus_draw = ImageDraw.Draw(focus, "RGBA")
    focus_draw.rectangle(
        (148, 50, 280, 92),
        outline=(208, 157, 24, 150),
        width=4,
    )
    focus = focus.convert("RGB").resize((1_000, 154), Image.Resampling.LANCZOS)
    risk_draw.rounded_rectangle(
        (40, 830, 1_040, 1_045),
        radius=18,
        fill=(249, 248, 243, 255),
    )
    risk_excerpt.paste(focus, (40, 860))
    response = risk.crop((0, 245, risk.width, 430))
    response = ImageEnhance.Sharpness(response).enhance(1.25)
    response = response.resize((1_000, 146), Image.Resampling.LANCZOS)
    risk_draw.rounded_rectangle(
        (40, 1_210, 1_040, 1_420),
        radius=18,
        fill=(249, 248, 243, 255),
    )
    risk_excerpt.paste(response, (40, 1_240))
    risk_draw.text(
        (540, 1_612),
        "PRIMARY SOURCE — MQL5 ARTICLE 525",
        font=font("consola.ttf", 27),
        fill=(39, 76, 82, 255),
        anchor="mm",
    )
    risk_draw.rectangle((0, 1_520, 1080, 1_860), fill=(216, 227, 236, 255))
    risk_draw.text(
        (58, 1_740),
        "MQL5.COM/EN/ARTICLES/525",
        font=mono_small,
        fill=(29, 70, 103, 255),
        anchor="lm",
    )
    risk_excerpt_path = output_dir / "risk-source-excerpt.png"
    risk_excerpt.save(risk_excerpt_path)

    number = Image.new("RGB", (1080, 1920), "#E8CD8E")
    number_draw = ImageDraw.Draw(number, "RGBA")
    number_draw.rectangle((0, 0, 1080, 170), fill=(24, 41, 50, 255))
    number_draw.text(
        (58, 84),
        "VERIFIED SOURCE MACRO",
        font=mono_label,
        fill=(247, 238, 211, 255),
        anchor="lm",
    )
    paragraph = risk.crop((0, 35, risk.width, 155))
    paragraph = ImageEnhance.Contrast(paragraph).enhance(1.08)
    paragraph = paragraph.resize((1_000, 95), Image.Resampling.LANCZOS)
    number_draw.rounded_rectangle(
        (40, 280, 1_040, 435),
        radius=16,
        fill=(250, 248, 241, 255),
    )
    number.paste(paragraph, (40, 310))
    number_crop = risk.crop((152, 78, 276, 121))
    number_crop = ImageEnhance.Sharpness(number_crop).enhance(1.4)
    number_crop = number_crop.resize((900, 300), Image.Resampling.LANCZOS)
    number_draw.rounded_rectangle(
        (70, 690, 1_010, 1_070),
        radius=24,
        fill=(251, 249, 241, 255),
        outline=(117, 85, 21, 110),
        width=4,
    )
    number.paste(number_crop, (90, 725))
    number_draw.rectangle(
        (110, 1_105, 970, 1_125),
        fill=(25, 105, 105, 220),
    )
    number_draw.text(
        (540, 1_690),
        "MQL5.COM/EN/ARTICLES/525",
        font=mono_small,
        fill=(45, 54, 56, 255),
        anchor="mm",
    )
    number_path = output_dir / "risk-source-number.png"
    number.save(number_path)

    return {
        "evidence-history-original": original_history,
        "evidence-risk-original": original_risk,
        "evidence-history-overview": overview_path,
        "evidence-championship-excerpt": championship_path,
        "evidence-risk-excerpt": risk_excerpt_path,
        "evidence-risk-number": number_path,
    }


def prepare_music() -> tuple[Path, list[dict[str, Any]]]:
    candidates = [
        {
            "id": "1167",
            "name": "Close Up",
            "file": "close-up-1167.mp3",
            "estimated_bpm": 101.4,
            "high_ratio": 0.0110,
            "selected": False,
            "reason": "Too bass-heavy and less neutral than the reference.",
        },
        {
            "id": "140",
            "name": "Cyberpunk City",
            "file": "cyberpunk-city-140.mp3",
            "estimated_bpm": 96.2,
            "high_ratio": 0.0341,
            "selected": True,
            "reason": (
                "Closest technical mood and tempo; high frequencies are "
                "reduced during preprocessing."
            ),
        },
        {
            "id": "588",
            "name": "Feedback Dreams",
            "file": "feedback-dreams-588.mp3",
            "estimated_bpm": 87.3,
            "high_ratio": 0.0015,
            "selected": False,
            "reason": "Too sparse and atmospheric for the software-action beats.",
        },
        {
            "id": "132",
            "name": "Hazy After Hours",
            "file": "hazy-after-hours-132.mp3",
            "estimated_bpm": 80.0,
            "high_ratio": 0.0067,
            "selected": False,
            "reason": "Tempo and bass profile are too heavy for the narration.",
        },
        {
            "id": "292",
            "name": "Relax Beat",
            "file": "relax-beat-292.mp3",
            "estimated_bpm": 101.4,
            "high_ratio": 0.0026,
            "selected": False,
            "reason": "Clean but too relaxed for the risk and proof sections.",
        },
        {
            "id": "584",
            "name": "Rest Now",
            "file": "rest-now-584.mp3",
            "estimated_bpm": 83.4,
            "high_ratio": 0.0001,
            "selected": False,
            "reason": "Too ambient and slow for reference-#10 pacing.",
        },
    ]
    source = MUSIC_LIBRARY / "cyberpunk-city-140.mp3"
    output = (
        OUTPUT_DIR
        / "assets"
        / "audio"
        / "music-technical-documentary.wav"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [
        get_ffmpeg_exe(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-t",
        "42.5",
        "-af",
        (
            "atempo=0.977,"
            "highpass=f=35,"
            "lowpass=f=6500,"
            "equalizer=f=3000:t=q:w=0.8:g=-3,"
            "afade=t=in:st=0:d=0.35,"
            "afade=t=out:st=41.0:d=0.4,"
            "atrim=duration=41.4,"
            "aresample=48000"
        ),
        "-ar",
        "48000",
        "-ac",
        "2",
        "-c:a",
        "pcm_s16le",
        str(output),
    ]
    subprocess.run(command, check=True, timeout=300)
    return output, candidates


def prepare_assets(
    graphics: dict[str, Path],
    evidence_paths: dict[str, Path],
    music_path: Path,
) -> list[AssetRef]:
    assets: list[AssetRef] = []
    v4_blueprint = json.loads(
        (V4_DIR / "blueprint.json").read_text(encoding="utf-8")
    )
    v4_assets = {item["id"]: item for item in v4_blueprint["assets"]}

    presenter_source = V4_DIR / v4_assets["source-presenter"]["path"]
    presenter = copy_file(
        presenter_source,
        OUTPUT_DIR / "assets" / "presenter" / "source-presenter.mp4",
    )
    assets.append(
        AssetRef(
            id="source-presenter",
            kind="video",
            path=relative(presenter),
            keywords=["presenter", "source narration"],
            provenance="user-provided",
        )
    )

    product_ids = [
        "capture-mt5-hook-action",
        "capture-metaeditor-open",
        "capture-metaeditor-rule-highlight",
        "capture-mt5-navigator-ea",
        "capture-mt5-risk-inputs",
        "capture-mt5-risk-alternate",
        "capture-mt5-attach-ea",
        "capture-mt5-strategy-tester",
    ]
    for asset_id in product_ids:
        source = V4_DIR / v4_assets[asset_id]["path"]
        destination = copy_file(
            source,
            OUTPUT_DIR / "assets" / "product" / source.name,
        )
        assets.append(
            AssetRef(
                id=asset_id,
                kind="video",
                path=relative(destination),
                keywords=[asset_id, "MetaTrader", "privacy-reviewed demo"],
                provenance="local-safe-demo-capture",
                license="User-owned local demo capture",
            )
        )

    licensed_specs = [
        (
            "licensed-typing",
            LICENSED_ROOT / "typing-242.mp4",
            "242",
            "https://mixkit.co/free-stock-video/typing-on-a-laptop-242/",
            "typing on laptop",
        ),
        (
            "licensed-code-screen",
            LICENSED_ROOT / "code-screen-9757.mp4",
            "9757",
            "https://mixkit.co/free-stock-video/computer-code-in-the-screen-9757/",
            "computer code screen",
        ),
    ]
    for asset_id, source, remote_id, source_url, query in licensed_specs:
        destination = copy_file(
            source,
            OUTPUT_DIR / "assets" / "licensed" / source.name,
        )
        assets.append(
            AssetRef(
                id=asset_id,
                kind="video",
                path=relative(destination),
                keywords=[query, "tactile", "technical context"],
                provenance="internet:licensed-stock-video",
                license="Mixkit Free License",
                provider="Mixkit",
                remote_id=remote_id,
                creator="Mixkit contributor",
                source_url=source_url,
                license_url="https://mixkit.co/license/",
                search_query=query,
            )
        )

    for asset_id, path in graphics.items():
        assets.append(
            AssetRef(
                id=asset_id,
                kind="image",
                path=relative(path),
                keywords=[asset_id, "reference-10 technical graphic"],
                provenance="deterministic-production-graphic",
                license="Original production graphic",
            )
        )

    evidence_ids = {
        "evidence-history-overview",
        "evidence-championship-excerpt",
        "evidence-risk-excerpt",
        "evidence-risk-number",
    }
    for asset_id in evidence_ids:
        assets.append(
            AssetRef(
                id=asset_id,
                kind="image",
                path=relative(evidence_paths[asset_id]),
                keywords=[asset_id, "official source pixels"],
                provenance="official-source-capture-derived-crop",
                license="Editorial evidence excerpt",
            )
        )

    logo = copy_file(
        BRAND_LOGO,
        OUTPUT_DIR / "assets" / "brand" / "profit-bricks-logo.png",
    )
    assets.append(
        AssetRef(
            id="brand-logo-original",
            kind="image",
            path=relative(logo),
            keywords=["Profit Bricks", "brand logo"],
            provenance="user-provided-brand-asset",
            license="User-provided brand asset",
        )
    )

    dialogue_source = V4_DIR / v4_assets["dialogue-original"]["path"]
    dialogue = copy_file(
        dialogue_source,
        OUTPUT_DIR / "assets" / "audio" / "dialogue-original.wav",
    )
    assets.append(
        AssetRef(
            id="dialogue-original",
            kind="audio",
            path=relative(dialogue),
            keywords=["untouched narration", "48 kHz"],
            provenance="source-dialogue-master",
            license="User-provided narration",
        )
    )
    assets.append(
        AssetRef(
            id="music-technical-documentary",
            kind="audio",
            path=relative(music_path),
            keywords=["technical documentary", "94 bpm", "instrumental"],
            provenance="internet:licensed-stock-music",
            license="Mixkit Stock Music Free License",
            provider="Mixkit",
            remote_id="140",
            creator="Alejandro Magaña (A. M.)",
            source_url="https://mixkit.co/free-stock-music/tag/technology/",
            license_url="https://mixkit.co/license/#musicFree",
            search_query="restrained cinematic technology ambient",
        )
    )

    sfx_sources = {
        "sfx-impact": (
            AUDIO_LIBRARY / "sfx-impact.mp3",
            "1143",
            "impact",
        ),
        "sfx-click": (
            AUDIO_LIBRARY / "sfx-click.mp3",
            "1109",
            "click",
        ),
        "sfx-snap": (
            AUDIO_LIBRARY / "sfx-snap.mp3",
            "3124",
            "click",
        ),
        "sfx-paper": (
            AUDIO_LIBRARY / "sfx-whoosh.mp3",
            "1492",
            "whoosh",
        ),
        "sfx-proof": (
            AUDIO_LIBRARY / "sfx-impact.mp3",
            "1143",
            "impact",
        ),
        "sfx-reversal": (
            AUDIO_LIBRARY / "sfx-impact.mp3",
            "1143",
            "impact",
        ),
        "sfx-riser": (
            AUDIO_LIBRARY / "sfx-riser.mp3",
            "1144",
            "riser",
        ),
    }
    for asset_id, (source, remote_id, category) in sfx_sources.items():
        destination = copy_file(
            source,
            OUTPUT_DIR / "assets" / "audio" / f"{asset_id}{source.suffix}",
        )
        assets.append(
            AssetRef(
                id=asset_id,
                kind="audio",
                path=relative(destination),
                keywords=[category, "speech-safe sound effect"],
                provenance="internet:licensed-sound-effect",
                license="Mixkit Free License",
                provider="Mixkit",
                remote_id=remote_id,
                creator="Mixkit contributor",
                source_url=f"https://mixkit.co/free-sound-effects/{category}/",
                license_url="https://mixkit.co/license/",
                search_query=f"restrained {category} sound effect",
            )
        )
    return assets


def prepare_evidence_records(
    evidence_paths: dict[str, Path],
) -> list[EvidenceItem]:
    records = json.loads(
        (V4_DIR / "evidence.json").read_text(encoding="utf-8")
    )
    output: list[EvidenceItem] = []
    capture_map = {
        "metaquotes-atc-history": evidence_paths["evidence-history-original"],
        "mql5-atc-2008-risk": evidence_paths["evidence-risk-original"],
    }
    for item in records:
        if item["id"] not in capture_map:
            continue
        output.append(
            EvidenceItem.model_validate(
                {
                    **item,
                    "capture_path": relative(capture_map[item["id"]]),
                    "accessed_at": datetime.now(UTC).isoformat(),
                }
            )
        )
    return output


def write_reports(
    *,
    music_candidates: list[dict[str, Any]],
    assets: list[AssetRef],
    blueprint: Any,
) -> dict[str, str]:
    reports = {
        "training_pattern_report": "training-pattern-report.md",
        "v6_gap_audit": "v6-gap-audit.md",
        "reference_profile": "reference-profile.json",
        "storyboard": "storyboard.json",
        "caption_plan": "caption-plan.json",
        "sound_cue_sheet": "sound-cue-sheet.json",
        "music_candidate_report": "music-candidate-report.json",
        "asset_manifest": "asset-manifest.json",
        "capture_manifest": "capture-manifest.json",
        "dialogue_edl": "dialogue-edl.json",
        "motion_events": "motion-events.json",
        "flow_shot_plan": "flow-shot-plan.json",
        "blueprint": "blueprint.json",
        "transcript_aligned": "transcript-aligned.json",
    }
    (OUTPUT_DIR / reports["training_pattern_report"]).write_text(
        """# Training Reference Pattern Report

The analysis covered all 28,020 frames from the 14 training references.
Reference #10 is the primary grammar for this technical explanation; reference
#4 contributes only the risk/reversal diagram language.

- Subject or product appears before presenter explanation.
- Presenter footage is connective tissue, not the dominant visual.
- Software is shown through readable macro crops and one action per shot.
- Evidence follows overview, readable excerpt, then highlighted fact.
- Hard cuts dominate; internal motion comes from cursor actions, pushes and
  tracked highlights.
- Technical captions are short uppercase phrases in fitted black mono boxes.
- The image sequence alternates dark technical canvases, bright source pages
  and warm tactile footage.
- Music is restrained, speech-safe and slower than promotional techno.
- Endings return to presenter or product and stop cleanly.
""",
        encoding="utf-8",
    )
    (OUTPUT_DIR / reports["v6_gap_audit"]).write_text(
        """# V6 Gap Audit

V6 is blocked and preserved unchanged.

| Measure | Reference #10 | V6 |
|---|---:|---:|
| Cuts/minute | 24.0 | 23.2 |
| Median shot | 2.00 s | 2.33 s |
| Face-visible frames | 11.7% | 69.9% |
| Caption height | 2.7% | 4.4% |
| Dark frames | 39.9% | 0% |
| Bright frames | 24.4% | 0% |
| Luminance P10-P90 | 11.6-239.9 | 72.6-146.6 |
| Mixed-audio pulse | 89.3 BPM | 144.2 BPM |

The pacing was close, but the visual and sound grammar was incorrect:
presenter dominance, floating cards, promotional typography, generic
illustrations, narrow tonal range and bright fast music.
""",
        encoding="utf-8",
    )
    targets = {
        "name": "technical-reference",
        "primary_reference": 10,
        "secondary_reference": 4,
        "duration_ms": DURATION_MS,
        "hard_cuts": [17, 19],
        "median_shot_ms": [1800, 2300],
        "presenter_ratio": [0.14, 0.20],
        "flow_ratio_max": 0,
        "caption_coverage_ratio": [0.68, 0.75],
        "dark_frame_ratio": [0.35, 0.45],
        "bright_frame_ratio": [0.18, 0.28],
        "luminance_p10": [8, 22],
        "luminance_p90": [220, 245],
        "mean_saturation": [50, 90],
        "audio": {
            "integrated_lufs": [-14.5, -13.9],
            "true_peak_max": -1,
            "lra": [2.3, 3.5],
            "cut_audio_alignment_min": 90,
        },
        "planned_role_coverage": estimate_role_coverage(blueprint.layers),
    }
    write_json(OUTPUT_DIR / reports["reference_profile"], targets)
    shots = build_shot_schedule()
    layer_ids_by_shot = {
        shot["id"]: [
            layer.id
            for layer in blueprint.layers
            if layer.shot_id == shot["id"]
        ]
        for shot in shots
    }
    write_json(
        OUTPUT_DIR / reports["storyboard"],
        [
            {
                **shot,
                "layer_ids": layer_ids_by_shot[shot["id"]],
            }
            for shot in shots
        ],
    )
    write_json(
        OUTPUT_DIR / reports["caption_plan"],
        {
            "primary_reference": 10,
            "family": "technical-mono",
            "coverage_ratio": sum(
                page.end_ms - page.start_ms
                for page in blueprint.caption_pages
            )
            / DURATION_MS,
            "pages": [
                page.model_dump(mode="json")
                for page in blueprint.caption_pages
            ],
        },
    )
    write_json(
        OUTPUT_DIR / reports["sound_cue_sheet"],
        blueprint.audio.model_dump(mode="json"),
    )
    write_json(
        OUTPUT_DIR / reports["music_candidate_report"],
        {
            "policy": "licensed, vocal-free, no obvious loop",
            "reference_mix_target_bpm": [88, 100],
            "selected": "Cyberpunk City — Mixkit 140",
            "processing": (
                "Slowed to approximately 94 BPM, low-passed, high-frequency "
                "shelf reduced, faded and trimmed to 41.4 seconds."
            ),
            "candidates": music_candidates,
        },
    )
    manifest_assets = []
    for asset in assets:
        path = OUTPUT_DIR / asset.path
        manifest_assets.append(
            {
                **asset.model_dump(mode="json"),
                "checksum_sha256": sha256(path),
            }
        )
    write_json(
        OUTPUT_DIR / reports["asset_manifest"],
        {
            "policy": "evidence-first free-licensed",
            "assets": manifest_assets,
        },
    )
    write_json(
        OUTPUT_DIR / reports["capture_manifest"],
        {
            "profile": "local-metatrader",
            "privacy_reviewed": True,
            "captures": [
                {
                    "asset_id": asset.id,
                    "path": asset.path,
                    "checksum_sha256": sha256(OUTPUT_DIR / asset.path),
                }
                for asset in assets
                if asset.provenance == "local-safe-demo-capture"
            ],
        },
    )
    write_json(
        OUTPUT_DIR / reports["dialogue_edl"],
        [
            item.model_dump(mode="json")
            for item in blueprint.dialogue_edl
        ],
    )
    write_json(
        OUTPUT_DIR / reports["motion_events"],
        [
            item.model_dump(mode="json")
            for item in blueprint.motion_events
        ],
    )
    write_json(OUTPUT_DIR / reports["flow_shot_plan"], [])
    return reports


def main() -> int:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"V7 output already exists and will not be overwritten: {OUTPUT_DIR}"
        )
    OUTPUT_DIR.mkdir(parents=True)

    transcript = json.loads(
        (V6_DIR / "transcript-aligned.json").read_text(encoding="utf-8")
    )
    transcript_path = OUTPUT_DIR / "transcript-aligned.json"
    write_json(transcript_path, transcript)
    captions = align_caption_specs(
        specs=build_caption_specs(),
        transcript=transcript,
    )
    graphics = prepare_graphics()
    evidence_paths = prepare_evidence()
    music_path, music_candidates = prepare_music()
    assets = prepare_assets(graphics, evidence_paths, music_path)
    evidence = prepare_evidence_records(evidence_paths)
    metadata = probe_video(SOURCE)
    blueprint = create_blueprint(
        source_filename=SOURCE.name,
        source_metadata=metadata,
        assets=assets,
        evidence=evidence,
        caption_pages=captions,
        transcript=transcript,
    )
    write_json(
        OUTPUT_DIR / "blueprint.json",
        blueprint.model_dump(mode="json"),
    )
    artifacts = write_reports(
        music_candidates=music_candidates,
        assets=assets,
        blueprint=blueprint,
    )
    write_json(
        OUTPUT_DIR / "production-settings.json",
        {
            "primary_reference": 10,
            "secondary_reference": 4,
            "reference_profile": "technical-reference",
            "voice_policy": "preserve-verbatim",
            "flow_operation_budget": 0,
            "asset_policy": "free-licensed",
            "music_profile": "technical-documentary-94",
            "human_final_approval_required": True,
        },
    )
    artifacts["production_settings"] = "production-settings.json"
    now = datetime.now(UTC)
    ProductionStore(OUTPUT_DIR).create(
        ProductionJobRecord(
            id="production-0806-v7-training-reference",
            source_path=str(SOURCE),
            output_dir=str(OUTPUT_DIR),
            state="blueprint-ready",
            primary_reference=10,
            secondary_reference=4,
            flow_operation_budget=0,
            approved_paid_operations=0,
            consumed_paid_operations=0,
            artifacts=artifacts,
            automated_pass=False,
            human_approved=False,
            state_history=[
                ProductionStateEvent(
                    state="analyzing",
                    at=now,
                    detail=(
                        "All 28,020 training-reference frames and all 1,242 "
                        "V6 frames were audited."
                    ),
                ),
                ProductionStateEvent(
                    state="blueprint-ready",
                    at=now,
                    detail=(
                        "Reference-#10 technical blueprint persisted with "
                        "zero Flow operations."
                    ),
                ),
            ],
            created_at=now,
            updated_at=now,
        )
    )
    print(
        json.dumps(
            {
                "output_dir": str(OUTPUT_DIR),
                "layers": len(blueprint.layers),
                "shots": len(build_shot_schedule()),
                "caption_pages": len(captions),
                "caption_coverage": round(
                    sum(page.end_ms - page.start_ms for page in captions)
                    / DURATION_MS,
                    4,
                ),
                "flow_shots": len(blueprint.flow_shots),
                "planned_role_coverage": estimate_role_coverage(
                    blueprint.layers
                ),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

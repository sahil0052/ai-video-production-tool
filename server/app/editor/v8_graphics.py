from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps


WIDTH = 1080
HEIGHT = 1920
FONT_REGULAR = Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")
FONT_MONO = Path(r"C:\Windows\Fonts\consola.ttf")
FONT_SERIF = Path(r"C:\Windows\Fonts\georgiab.ttf")

_GRAPHICS: dict[str, dict[str, Any]] = {
    "graphic-ppi-producer": {
        "kind": "flow",
        "title": "PRODUCER PRICE",
        "subtitle": "The first commercial price change",
        "items": ["PRODUCER", "WHOLESALE", "RETAIL"],
        "active": 0,
        "accent": "#55DDE0",
    },
    "graphic-ppi-wholesale": {
        "kind": "flow",
        "title": "PRICE MOVES UPSTREAM",
        "subtitle": "Before the customer sees the final bill",
        "items": ["PRODUCER", "WHOLESALE", "RETAIL"],
        "active": 1,
        "accent": "#55DDE0",
    },
    "graphic-ppi-retail": {
        "kind": "flow",
        "title": "THEN RETAIL",
        "subtitle": "The change reaches the final sale",
        "items": ["PRODUCER", "WHOLESALE", "RETAIL"],
        "active": 2,
        "accent": "#55DDE0",
    },
    "graphic-cpi-vs-ppi": {
        "kind": "compare",
        "title": "CPI  ≠  PPI",
        "subtitle": "Two different points in the price chain",
        "left": ("CUSTOMER", "FINAL PRICE", "CPI"),
        "right": ("PRODUCER", "SELLING PRICE", "PPI"),
        "accent": "#E8D98B",
    },
    "graphic-zero-not-flat": {
        "kind": "split",
        "title": "ZERO IS A NET RESULT",
        "subtitle": "It does not mean every component stayed flat",
        "left": ("GOODS", "DOWN"),
        "right": ("SERVICES", "UP"),
        "accent": "#F25F5C",
    },
    "graphic-component-grid": {
        "kind": "component",
        "title": "INSIDE THE HEADLINE",
        "subtitle": "Different components can move differently",
        "accent": "#55DDE0",
    },
    "graphic-zero-balance": {
        "kind": "balance",
        "title": "OPPOSITE MOVES",
        "subtitle": "can settle at a flat headline",
        "accent": "#E8D98B",
    },
    "graphic-opposing-arrows": {
        "kind": "reversal",
        "title": "GOODS ↓   SERVICES ↑",
        "subtitle": "The verified components moved in opposite directions",
        "accent": "#F25F5C",
    },
    "graphic-net-zero": {
        "kind": "balance",
        "title": "NET: UNCHANGED",
        "subtitle": "Direction matters beneath the headline",
        "accent": "#55DDE0",
    },
    "graphic-ppi-risk-rule": {
        "kind": "rule",
        "title": "NUMBER ≠ REASON",
        "subtitle": "Execution still needs spread and confirmation rules",
        "items": ["READ RELEASE", "CHECK SPREAD", "WAIT CONFIRMATION"],
        "accent": "#55DDE0",
    },
    "graphic-backtest-practice": {
        "kind": "compare",
        "theme": "bright",
        "title": "PRACTICE  ≠  LIVE",
        "subtitle": "A backtest rehearses old conditions",
        "left": ("HISTORY", "KNOWN DATA", "BACKTEST"),
        "right": ("LIVE", "NEW CONDITIONS", "MARKET"),
        "accent": "#55DDE0",
    },
    "graphic-historical-data": {
        "kind": "timeline",
        "theme": "bright",
        "title": "HISTORICAL DATA",
        "subtitle": "Past ticks feed the test environment",
        "accent": "#55DDE0",
    },
    "graphic-fixed-spread": {
        "kind": "split",
        "theme": "bright",
        "title": "FIXED VS CHANGING",
        "subtitle": "A clean test can hide live friction",
        "left": ("TEST", "FIXED"),
        "right": ("LIVE", "MOVING"),
        "accent": "#F25F5C",
    },
    "graphic-perfect-prices": {
        "kind": "split",
        "theme": "bright",
        "title": "PERFECT TEST PRICES",
        "subtitle": "A clean simulation removes live-market friction",
        "left": ("BACKTEST", "CLEAN"),
        "right": ("LIVE", "VARIABLE"),
        "accent": "#55DDE0",
    },
    "graphic-delay-slippage": {
        "kind": "path",
        "title": "REQUEST → DELAY → FILL",
        "subtitle": "The live price can move before execution",
        "accent": "#F25F5C",
    },
    "graphic-overfit-history": {
        "kind": "overfit",
        "title": "PERFECT ON HISTORY",
        "subtitle": "The rule follows the old sample too closely",
        "accent": "#55DDE0",
        "phase": "history",
    },
    "graphic-overfit-unseen": {
        "kind": "overfit",
        "title": "WEAK ON UNSEEN DATA",
        "subtitle": "Memorization is not generalization",
        "accent": "#F25F5C",
        "phase": "unseen",
    },
    "graphic-overfit-unseen-bright": {
        "kind": "overfit",
        "theme": "bright",
        "title": "WEAK ON UNSEEN DATA",
        "subtitle": "Memorization is not generalization",
        "accent": "#F25F5C",
        "phase": "unseen",
    },
    "graphic-practice-not-guarantee": {
        "kind": "rule",
        "title": "PRACTICE SCORE ≠ GUARANTEE",
        "subtitle": "Forward testing checks a different environment",
        "items": ["BACKTEST", "DEMO FORWARD TEST", "LIVE DECISION"],
        "accent": "#E8D98B",
    },
    "graphic-unit-price": {
        "kind": "equation",
        "theme": "bright",
        "title": "1 UNIT × SAME PRICE",
        "subtitle": "Unit price stays constant",
        "accent": "#E8D98B",
    },
    "graphic-different-total": {
        "kind": "bars",
        "theme": "bright",
        "title": "QUANTITY CHANGES TOTAL",
        "subtitle": "More units create a larger total",
        "accent": "#55DDE0",
    },
    "graphic-same-move": {
        "kind": "split",
        "title": "SAME MARKET MOVE",
        "subtitle": "Two position sizes receive the same direction",
        "left": ("SMALL LOT", "1× MOVE"),
        "right": ("LARGE LOT", "1× MOVE"),
        "accent": "#55DDE0",
    },
    "graphic-relative-impact": {
        "kind": "bars",
        "title": "DIFFERENT IMPACT",
        "subtitle": "Relative size changes the consequence",
        "accent": "#F25F5C",
    },
    "graphic-relative-impact-large": {
        "kind": "bars",
        "title": "LARGER LOT, LARGER IMPACT",
        "subtitle": "The market move stays the same",
        "accent": "#F25F5C",
        "heights": (120, 330, 820),
    },
    "graphic-stop-distance": {
        "kind": "path",
        "title": "ENTRY → STOP DISTANCE",
        "subtitle": "Distance is only one part of risk",
        "accent": "#E8D98B",
    },
    "graphic-risk-equation": {
        "kind": "equation",
        "title": "STOP DISTANCE × LOT SIZE",
        "subtitle": "= ACTUAL RISK",
        "accent": "#F25F5C",
    },
    "graphic-wrong-repeat": {
        "kind": "loop",
        "title": "WRONG RULE, PERFECTLY REPEATED",
        "subtitle": "Automation scales the setting it receives",
        "accent": "#F25F5C",
    },
    "graphic-entry-lot-risk": {
        "kind": "rule",
        "theme": "bright",
        "title": "ENTRY • LOT • RISK",
        "subtitle": "Where, size, consequence",
        "items": ["ENTRY = WHERE", "LOT = SIZE", "RISK = CONSEQUENCE"],
        "accent": "#55DDE0",
    },
}


def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def _centered(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    *,
    font: ImageFont.FreeTypeFont,
    fill: str,
) -> None:
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(
        ((WIDTH - (box[2] - box[0])) / 2, y),
        text,
        font=font,
        fill=fill,
    )


def _header(draw: ImageDraw.ImageDraw, config: dict[str, Any]) -> None:
    accent = config["accent"]
    bright = config.get("theme") == "bright"
    draw.rectangle((0, 0, WIDTH, 18), fill=accent)
    draw.text(
        (72, 70),
        "ILLUSTRATIVE  /  PROFIT BRICKS",
        font=_font(FONT_MONO, 24),
        fill="#59666B" if bright else "#8D989B",
    )
    _centered(
        draw,
        config["title"],
        208,
        font=_font(FONT_BOLD, 70),
        fill="#111719" if bright else "#F3F4F2",
    )
    _centered(
        draw,
        config["subtitle"],
        320,
        font=_font(FONT_REGULAR, 34),
        fill="#59666B" if bright else "#AEB8BA",
    )


def _arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    fill: str,
    width: int = 10,
) -> None:
    draw.line((start, end), fill=fill, width=width)
    x, y = end
    draw.polygon(
        [(x, y), (x - 26, y - 18), (x - 26, y + 18)],
        fill=fill,
    )


def _node(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    *,
    active: bool,
    accent: str,
    bright: bool = False,
) -> None:
    if bright:
        fill = "#DDF6F5" if active else "#FFFFFF"
        outline = accent if active else "#9AA6AA"
        text_fill = "#111719"
    else:
        fill = "#F3F4F2" if active else "#121A1D"
        outline = accent if active else "#344247"
        text_fill = "#091012" if active else "#F3F4F2"
    draw.rounded_rectangle(box, radius=24, fill=fill, outline=outline, width=5)
    font = _font(FONT_MONO, 34)
    bounds = draw.textbbox((0, 0), text, font=font)
    draw.text(
        (
            (box[0] + box[2] - (bounds[2] - bounds[0])) / 2,
            (box[1] + box[3] - (bounds[3] - bounds[1])) / 2 - 6,
        ),
        text,
        font=font,
        fill=text_fill,
    )


def render_graphic(asset_id: str, output: Path) -> Path:
    if asset_id not in _GRAPHICS:
        raise ValueError(f"Unknown deterministic graphic: {asset_id}")
    config = _GRAPHICS[asset_id]
    bright = config.get("theme") == "bright"
    background = "#F3F0E7" if bright else "#061012"
    panel = "#FFFFFF" if bright else "#10191C"
    outline = "#9AA6AA" if bright else "#354449"
    text = "#111719" if bright else "#F3F4F2"
    muted = "#59666B" if bright else "#69777B"
    image = Image.new("RGB", (WIDTH, HEIGHT), background)
    draw = ImageDraw.Draw(image)
    _header(draw, config)
    accent = config["accent"]
    kind = config["kind"]

    if kind == "flow":
        for index, label in enumerate(config["items"]):
            top = 590 + index * 330
            _node(
                draw,
                (160, top, 920, top + 170),
                label,
                active=index == config["active"],
                accent=accent,
            )
            if index < 2:
                _arrow(
                    draw,
                    (540, top + 190),
                    (540, top + 292),
                    fill=accent,
                    width=8,
                )
    elif kind == "compare":
        for left, x in ((config["left"], 90), (config["right"], 570)):
            draw.rounded_rectangle(
                (x, 610, x + 420, 1370),
                radius=28,
                fill=panel,
                outline=outline,
                width=4,
            )
            for index, line in enumerate(left):
                _center_x = x + 210
                font = _font(
                    FONT_BOLD if index == 2 else FONT_MONO,
                    56 if index == 2 else 32,
                )
                bounds = draw.textbbox((0, 0), line, font=font)
                draw.text(
                    (
                        _center_x - (bounds[2] - bounds[0]) / 2,
                        720 + index * 230,
                    ),
                    line,
                    font=font,
                    fill=accent if index == 2 else text,
                )
    elif kind == "split":
        for index, side in enumerate((config["left"], config["right"])):
            x = 90 + index * 500
            color = "#F25F5C" if index == 0 else "#55DDE0"
            draw.rounded_rectangle(
                (x, 650, x + 400, 1330),
                radius=28,
                fill=panel,
                outline=color,
                width=5,
            )
            _center_x = x + 200
            for row, line in enumerate(side):
                font = _font(FONT_BOLD, 48 if row == 0 else 82)
                bounds = draw.textbbox((0, 0), line, font=font)
                draw.text(
                    (
                        _center_x - (bounds[2] - bounds[0]) / 2,
                        790 + row * 250,
                    ),
                    line,
                    font=font,
                    fill=color if row else text,
                )
    elif kind == "reversal":
        draw.rounded_rectangle(
            (80, 600, 500, 1460),
            radius=34,
            fill="#211014",
            outline="#F25F5C",
            width=5,
        )
        draw.rounded_rectangle(
            (580, 600, 1000, 1460),
            radius=34,
            fill="#0B2024",
            outline="#55DDE0",
            width=5,
        )
        draw.line((390, 760, 190, 1260), fill="#F25F5C", width=28)
        draw.polygon(
            [(190, 1325), (128, 1190), (258, 1242)],
            fill="#F25F5C",
        )
        draw.line((690, 1280, 890, 780), fill="#55DDE0", width=28)
        draw.polygon(
            [(890, 715), (952, 850), (822, 798)],
            fill="#55DDE0",
        )
        draw.text(
            (155, 700),
            "GOODS",
            font=_font(FONT_MONO, 42),
            fill="#F3F4F2",
        )
        draw.text(
            (655, 1320),
            "SERVICES",
            font=_font(FONT_MONO, 42),
            fill="#F3F4F2",
        )
        _centered(
            draw,
            "OPPOSITE DIRECTIONS",
            1570,
            font=_font(FONT_BOLD, 52),
            fill="#F3F4F2",
        )
    elif kind == "balance":
        draw.line((180, 1040, 900, 1040), fill="#59686D", width=12)
        draw.ellipse((510, 970, 570, 1030), fill="#F3F4F2")
        draw.polygon(
            [(170, 980), (380, 700), (380, 1260)],
            fill="#F25F5C",
        )
        draw.polygon(
            [(910, 1100), (700, 820), (700, 1380)],
            fill="#55DDE0",
        )
        _centered(draw, "DOWN", 1430, font=_font(FONT_MONO, 34), fill="#F25F5C")
        _centered(draw, "UP", 1510, font=_font(FONT_MONO, 34), fill="#55DDE0")
    elif kind == "component":
        labels = ["GOODS", "SERVICES", "ENERGY", "TRADE"]
        for index, label in enumerate(labels):
            column = index % 2
            row = index // 2
            x = 100 + column * 490
            y = 620 + row * 390
            draw.rounded_rectangle(
                (x, y, x + 390, y + 290),
                radius=28,
                fill="#111A1D",
                outline=accent if index < 2 else "#344247",
                width=4,
            )
            draw.text(
                (x + 42, y + 52),
                label,
                font=_font(FONT_MONO, 36),
                fill="#F3F4F2",
            )
            draw.line(
                (x + 42, y + 190, x + 330, y + 190),
                fill=("#F25F5C" if index % 2 == 0 else "#55DDE0"),
                width=18,
            )
    elif kind == "timeline":
        draw.line(
            (130, 1020, 950, 1020),
            fill="#657277" if bright else "#3A484D",
            width=10,
        )
        for index, label in enumerate(("PAST", "TEST", "CHECK")):
            x = 170 + index * 360
            draw.ellipse((x - 28, 992, x + 28, 1048), fill=accent)
            draw.text(
                (x - 54, 1110),
                label,
                font=_font(FONT_MONO, 30),
                fill=text,
            )
        _arrow(draw, (170, 860), (870, 860), fill=accent)
    elif kind == "path":
        points = [(120, 1050), (340, 1050), (500, 820), (690, 1180), (940, 1180)]
        draw.line(points, fill=accent, width=14, joint="curve")
        for x, y in points:
            draw.ellipse((x - 22, y - 22, x + 22, y + 22), fill="#F3F4F2")
        draw.text((390, 690), "FRICTION", font=_font(FONT_MONO, 34), fill=accent)
    elif kind == "overfit":
        draw.line((150, 1380, 150, 650), fill="#4A575B", width=6)
        draw.line((150, 1380, 930, 1380), fill="#4A575B", width=6)
        points = []
        phase = config.get("phase")
        for index in range(13):
            x = 170 + index * 58
            if phase == "history":
                y = 1110 - int(130 * ((index % 3) - 1))
            else:
                y = 940 + int(26 * index) + (90 if index % 2 else -60)
            points.append((x, y))
        draw.line(points, fill=accent, width=12, joint="curve")
    elif kind == "equation":
        _centered(
            draw,
            config["title"],
            780,
            font=_font(FONT_MONO, 58),
            fill=text,
        )
        draw.line((180, 960, 900, 960), fill=accent, width=10)
        _centered(
            draw,
            config["subtitle"],
            1070,
            font=_font(FONT_BOLD, 78),
            fill=accent,
        )
    elif kind == "bars":
        for index, height in enumerate(
            config.get("heights", (210, 430, 690))
        ):
            x = 170 + index * 270
            draw.rounded_rectangle(
                (x, 1420 - height, x + 150, 1420),
                radius=20,
                fill=accent if index == 2 else "#405158",
            )
        draw.line((120, 1420, 960, 1420), fill="#7D898D", width=6)
    elif kind == "loop":
        draw.arc((210, 650, 870, 1370), 35, 320, fill=accent, width=18)
        draw.polygon([(830, 650), (920, 680), (850, 750)], fill=accent)
        _centered(
            draw,
            "SAME SETTING",
            925,
            font=_font(FONT_MONO, 50),
            fill="#F3F4F2",
        )
    elif kind == "rule":
        for index, item in enumerate(config["items"]):
            y = 650 + index * 260
            _node(
                draw,
                (120, y, 960, y + 160),
                item,
                active=index == 1,
                accent=accent,
                bright=bright,
            )
    else:
        raise ValueError(f"Unsupported graphic kind: {kind}")

    draw.text(
        (72, 1810),
        "DIAGRAM — NOT A PERFORMANCE RESULT",
        font=_font(FONT_MONO, 22),
        fill=muted,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, quality=95)
    return output


_EVIDENCE_CROPS = {
    "overview": (0.00, 0.00, 1.00, 1.00),
    "forecast": (0.00, 0.00, 1.00, 0.34),
    "actual": (0.00, 0.105, 1.00, 0.37),
    "zero": (0.00, 0.105, 1.00, 0.37),
    "zero-attribution": (0.00, 0.00, 1.00, 0.38),
    "services": (0.00, 0.38, 1.00, 0.62),
    "goods": (0.00, 0.67, 1.00, 0.91),
    "goods-services": (0.00, 0.24, 1.00, 0.91),
}


def render_evidence_crop(
    source: Path,
    output: Path,
    crop_name: str,
) -> Path:
    if crop_name not in _EVIDENCE_CROPS:
        raise ValueError(f"Unknown evidence crop: {crop_name}")
    with Image.open(source).convert("RGB") as original:
        x0, y0, x1, y1 = _EVIDENCE_CROPS[crop_name]
        crop = original.crop(
            (
                round(original.width * x0),
                round(original.height * y0),
                round(original.width * x1),
                round(original.height * y1),
            )
        )
    if crop_name == "overview":
        canvas = Image.new("RGB", (WIDTH, HEIGHT), "#F5F3ED")
        draw = ImageDraw.Draw(canvas)
        draw.rectangle((0, 0, WIDTH, 18), fill="#B69D55")
        contained = ImageOps.contain(
            crop,
            (970, 1660),
            method=Image.Resampling.LANCZOS,
        )
        x = (WIDTH - contained.width) // 2
        y = 130 + (1660 - contained.height) // 2
        canvas.paste(contained, (x, y))
        draw.text(
            (60, 1825),
            "bls.gov  •  Producer Price Indexes — July 2026",
            font=_font(FONT_REGULAR, 25),
            fill="#555A5B",
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output, quality=95)
        return output

    bright_page = crop_name in {"actual", "zero-attribution"}
    canvas = Image.new(
        "RGB",
        (WIDTH, HEIGHT),
        "#F5F3ED" if bright_page else "#091012",
    )
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, WIDTH, 18), fill="#B69D55")
    draw.text(
        (60, 66),
        "SOURCE PIXELS  /  U.S. BUREAU OF LABOR STATISTICS",
        font=_font(FONT_MONO, 22),
        fill="#495357" if bright_page else "#98A3A6",
    )
    headline = {
        "forecast": "OFFICIAL RELEASE",
        "actual": "ACTUAL: 0.0%",
        "zero": "UNCHANGED: 0.0%",
        "zero-attribution": "JULY 2026: UNCHANGED",
        "services": "SERVICES: +0.2%",
        "goods": "GOODS: −0.7%",
        "goods-services": "GOODS DOWN / SERVICES UP",
    }[crop_name]
    _centered(
        draw,
        headline,
        220,
        font=_font(FONT_BOLD, 68),
        fill="#111718" if bright_page else "#F3F4F2",
    )
    _centered(
        draw,
        "VERIFIED SOURCE EXCERPT",
        330,
        font=_font(FONT_MONO, 28),
        fill="#8A6D21" if bright_page else "#B69D55",
    )
    contained = ImageOps.contain(
        crop,
        (990, 930),
        method=Image.Resampling.LANCZOS,
    )
    x = (WIDTH - contained.width) // 2
    y = 540 + (930 - contained.height) // 2
    draw.rounded_rectangle(
        (30, 500, 1050, 1510),
        radius=18,
        fill="#FFFFFF" if bright_page else "#F5F3ED",
        outline="#B69D55",
        width=4,
    )
    canvas.paste(contained, (x, y))
    draw.rounded_rectangle(
        (x - 8, y - 8, x + contained.width + 8, y + contained.height + 8),
        radius=12,
        outline="#C4BFAF",
        width=3,
    )
    draw.text(
        (60, 1785),
        "bls.gov  •  Producer Price Indexes — July 2026",
        font=_font(FONT_REGULAR, 25),
        fill="#515B5E" if bright_page else "#9AA5A8",
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output, quality=95)
    return output

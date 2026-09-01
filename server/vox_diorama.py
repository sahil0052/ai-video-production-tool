"""
Vox paper-diorama still generator.

Builds aged-print collage plates in the "Paper Diorama" language documented in
`CL3 Vox Videos/image-prompts.md`: aged-print backgrounds, halftone black-and-white
cutouts with rough keylines and offset accent strokes, giant stat numbers, torn
paper layers, rubber stamps, pins with thread and print grain.

Plates are rendered at 1620x1440 (exactly 1080:960) so the procedural camera moves
in the split-screen builder crop and rescale without distorting the artwork.

Depth is faked the way the prompt system asks for it: background panels are blurred
and darkened, mid layers get soft contact shadows, foreground layers get hard
offset shadows and full sharpness.
"""

from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

CANVAS = (1620, 1440)

# `#D62E1F` is the accent that leaked into the reference plate; keep it exact.
PALETTE = {
    "paper_light": (234, 225, 204),
    "paper_mid": (208, 195, 169),
    "paper_dark": (170, 154, 126),
    "paper_deep": (138, 123, 99),
    "ink": (26, 23, 20),
    "ink_soft": (62, 57, 50),
    "ink_faint": (112, 104, 92),
    "accent_red": (214, 46, 31),
    "stamp_red": (178, 38, 28),
    "cream": (240, 234, 218),
}

FONT_DIR = Path(r"C:\Windows\Fonts")
FONT_GIANT = FONT_DIR / "impact.ttf"
FONT_HEAVY = FONT_DIR / "seguibl.ttf"
FONT_BOLD = FONT_DIR / "arialbd.ttf"
FONT_COND = FONT_DIR / "bahnschrift.ttf"
FONT_MONO = FONT_DIR / "consolab.ttf"
FONT_SERIF = FONT_DIR / "georgia.ttf"


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default()


def _text_size(draw: ImageDraw.ImageDraw, text: str, fnt) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


# ---------------------------------------------------------------------------
# paper stock
# ---------------------------------------------------------------------------


def aged_paper(size: tuple[int, int], seed: int, tone: str = "paper_mid") -> Image.Image:
    """Warm paper stock with fiber noise, blotching and an edge falloff."""
    rng = np.random.default_rng(seed)
    w, h = size
    base = np.array(PALETTE[tone], dtype=np.float32)
    field = np.repeat(np.repeat(base[None, None, :], h, axis=0), w, axis=1)

    # broad tonal drift so large flats never read as digital
    coarse = rng.normal(0.0, 1.0, (max(2, h // 48), max(2, w // 48))).astype(np.float32)
    coarse = np.array(
        Image.fromarray(((coarse * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8))
        .resize((w, h), Image.BICUBIC),
        dtype=np.float32,
    )
    field *= (0.95 + 0.10 * (coarse / 255.0))[..., None]

    # paper fiber
    fiber = rng.normal(0.0, 5.2, (h, w)).astype(np.float32)
    field += fiber[..., None]

    img = Image.fromarray(field.clip(0, 255).astype(np.uint8), "RGB")

    # foxing blotches - kept faint so large flats stay readable behind type
    blotch = Image.new("L", size, 0)
    bd = ImageDraw.Draw(blotch)
    pr = random.Random(seed * 31 + 7)
    for _ in range(18):
        cx, cy = pr.randrange(w), pr.randrange(h)
        rr = pr.randint(int(min(w, h) * 0.02), int(min(w, h) * 0.08))
        bd.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=pr.randint(8, 22))
    blotch = blotch.filter(ImageFilter.GaussianBlur(min(w, h) * 0.018))
    img = Image.composite(Image.new("RGB", size, PALETTE["paper_dark"]), img, blotch)

    # edge falloff
    vig = Image.new("L", size, 0)
    vd = ImageDraw.Draw(vig)
    inset = int(min(w, h) * 0.06)
    vd.rectangle((inset, inset, w - inset, h - inset), fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(inset * 0.9))
    img = Image.composite(img, Image.blend(img, Image.new("RGB", size, PALETTE["paper_deep"]), 0.42), vig)
    return img


def grain(img: Image.Image, strength: float = 9.0, seed: int = 0) -> Image.Image:
    """Print grain over the finished plate."""
    rng = np.random.default_rng(seed + 991)
    arr = np.asarray(img.convert("RGB"), dtype=np.float32)
    noise = rng.normal(0.0, strength, arr.shape[:2]).astype(np.float32)
    arr += noise[..., None]
    # faint misregistration on the red channel, like offset print
    out = Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGB")
    r, g, b = out.split()
    r = ImageChops.offset(r, 1, 0)
    return Image.merge("RGB", (r, g, b))


# ---------------------------------------------------------------------------
# halftone
# ---------------------------------------------------------------------------


def halftone(
    source: Image.Image,
    cell: int = 9,
    angle: float = 45.0,
    ink: tuple[int, int, int] = (22, 20, 18),
    gamma: float = 1.0,
    alpha: Image.Image | None = None,
) -> Image.Image:
    """Render `source` as an RGBA halftone dot screen on a rotated lattice."""
    gray = source.convert("L")
    w, h = gray.size
    lum = np.asarray(gray, dtype=np.float32) / 255.0
    if gamma != 1.0:
        lum = np.clip(lum, 0.0, 1.0) ** gamma
    mask = None
    if alpha is not None:
        mask = np.asarray(alpha.convert("L").resize((w, h)), dtype=np.float32) / 255.0

    ss = 2
    out = Image.new("RGBA", (w * ss, h * ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(out)
    th = math.radians(angle)
    ca, sa = math.cos(th), math.sin(th)
    reach = int(math.hypot(w, h) / 2) + cell * 2
    rad_max = cell * 0.80

    for v in range(-reach, reach + cell, cell):
        for u in range(-reach, reach + cell, cell):
            x = u * ca - v * sa + w / 2.0
            y = u * sa + v * ca + h / 2.0
            xi, yi = int(x), int(y)
            if xi < 0 or yi < 0 or xi >= w or yi >= h:
                continue
            cover = 1.0 if mask is None else mask[yi, xi]
            if cover < 0.35:
                continue
            dark = (1.0 - float(lum[yi, xi])) * cover
            if dark <= 0.05:
                continue
            r = rad_max * math.sqrt(min(1.0, dark))
            if r < 0.35:
                continue
            draw.ellipse(
                (
                    (x - r) * ss,
                    (y - r) * ss,
                    (x + r) * ss,
                    (y + r) * ss,
                ),
                fill=(*ink, 255),
            )
    return out.resize((w, h), Image.LANCZOS)


def keyline(rgba: Image.Image, width: int = 9, color: tuple[int, int, int] = (243, 238, 224)) -> Image.Image:
    """Rough cream keyline behind a cutout, the way a scissor-cut sticker reads."""
    a = rgba.split()[3]
    grown = a.filter(ImageFilter.MaxFilter(3))
    for _ in range(max(1, width // 2)):
        grown = grown.filter(ImageFilter.MaxFilter(3))
    grown = grown.filter(ImageFilter.GaussianBlur(0.8)).point(lambda v: 255 if v > 90 else 0)
    plate = Image.new("RGBA", rgba.size, (*color, 0))
    plate.putalpha(grown)
    plate.alpha_composite(rgba)
    return plate


def cutout_from_photo(
    photo: Image.Image,
    target_h: int,
    cell: int = 8,
    key_tolerance: int = 46,
) -> Image.Image | None:
    """Halftone cutout from a studio-isolated photo.

    Background is removed by flood-filling from the border against a light key.
    Returns None when the photo is not isolated enough to key cleanly.
    """
    photo = photo.convert("RGB")
    w, h = photo.size
    scale = target_h / h
    photo = photo.resize((max(1, int(w * scale)), target_h), Image.LANCZOS)
    w, h = photo.size

    arr = np.asarray(photo, dtype=np.int16)
    border = np.concatenate([arr[0, :, :], arr[-1, :, :], arr[:, 0, :], arr[:, -1, :]])
    key = np.median(border, axis=0)
    if key.min() < 150:  # not a light isolated background
        return None

    dist = np.sqrt(((arr - key[None, None, :]) ** 2).sum(axis=2))
    bg = dist < key_tolerance

    # keep only background connected to the frame edge
    seen = np.zeros_like(bg, dtype=bool)
    stack: list[tuple[int, int]] = []
    for x in range(w):
        for y in (0, h - 1):
            if bg[y, x]:
                stack.append((y, x))
    for y in range(h):
        for x in (0, w - 1):
            if bg[y, x]:
                stack.append((y, x))
    while stack:
        y, x = stack.pop()
        if y < 0 or x < 0 or y >= h or x >= w or seen[y, x] or not bg[y, x]:
            continue
        seen[y, x] = True
        stack.extend(((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)))

    subject = (~seen).astype(np.uint8) * 255
    coverage = subject.mean() / 255.0
    if coverage > 0.86 or coverage < 0.05:
        return None

    mask = Image.fromarray(subject, "L").filter(ImageFilter.MedianFilter(5))
    mask = mask.filter(ImageFilter.GaussianBlur(1.2)).point(lambda v: 255 if v > 128 else 0)

    # reject fragmented keys: the figure must survive as one dominant blob
    solid = np.asarray(mask, dtype=bool)
    if not _largest_blob_ratio(solid) >= 0.70:
        return None

    box = mask.getbbox()
    if box is None:
        return None
    photo = photo.crop(box)
    mask = mask.crop(box)

    # Tonal work on subject pixels only. Dark suits otherwise crush to a solid
    # silhouette; the reference plates keep dot texture in clothing and faces.
    flat = np.asarray(photo.convert("L"), dtype=np.float32) / 255.0
    inside = np.asarray(mask, dtype=bool)
    if inside.sum() < 64:
        return None
    vals = flat[inside]
    lo, hi = np.percentile(vals, 2.0), np.percentile(vals, 98.0)
    if hi - lo < 0.04:
        return None
    flat = np.clip((flat - lo) / (hi - lo), 0.0, 1.0)
    flat = flat**0.62  # lift shadows so fabric screens instead of filling
    flat = np.clip(0.06 + flat * 0.90, 0.0, 1.0)
    graphic = Image.fromarray((flat * 255).astype(np.uint8), "L")

    dots = halftone(graphic, cell=cell, angle=45.0, ink=PALETTE["ink"], gamma=1.0, alpha=mask)
    return keyline(dots, width=9)


def _largest_blob_ratio(mask: np.ndarray) -> float:
    """Fraction of the mask occupied by its largest 4-connected component."""
    h, w = mask.shape
    total = int(mask.sum())
    if total == 0:
        return 0.0
    seen = np.zeros_like(mask, dtype=bool)
    best = 0
    for sy in range(0, h, 4):
        for sx in range(0, w, 4):
            if not mask[sy, sx] or seen[sy, sx]:
                continue
            size = 0
            stack = [(sy, sx)]
            while stack:
                y, x = stack.pop()
                if y < 0 or x < 0 or y >= h or x >= w or seen[y, x] or not mask[y, x]:
                    continue
                seen[y, x] = True
                size += 1
                stack.extend(((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)))
            best = max(best, size)
    return best / total


# ---------------------------------------------------------------------------
# print furniture
# ---------------------------------------------------------------------------


def torn_edge(size: tuple[int, int], seed: int, side: str = "top") -> Image.Image:
    """Alpha mask whose named side is a torn paper edge."""
    w, h = size
    rng = random.Random(seed)
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    if side in ("top", "bottom"):
        span, amp = w, h * 0.045
        pts = []
        x = 0
        y0 = h * (0.10 if side == "top" else 0.90)
        while x <= span:
            pts.append((x, y0 + rng.uniform(-amp, amp) + math.sin(x / 90.0) * amp * 0.6))
            x += rng.randint(14, 40)
        pts.append((span, y0))
        poly = pts + ([(span, h), (0, h)] if side == "top" else [(span, 0), (0, 0)])
    else:
        span, amp = h, w * 0.045
        x0 = w * (0.10 if side == "left" else 0.90)
        pts = []
        y = 0
        while y <= span:
            pts.append((x0 + rng.uniform(-amp, amp) + math.sin(y / 90.0) * amp * 0.6, y))
            y += rng.randint(14, 40)
        pts.append((x0, span))
        poly = pts + ([(w, span), (w, 0)] if side == "left" else [(0, span), (0, 0)])
    d.polygon(poly, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(1.1))


def place(
    base: Image.Image,
    layer: Image.Image,
    xy: tuple[int, int],
    depth: str = "mid",
    rotate: float = 0.0,
) -> None:
    """Composite `layer` at a named depth.

    far  - blurred, tonally pushed back, no shadow
    mid  - soft contact shadow
    near - hard offset shadow, full sharpness
    """
    if rotate:
        layer = layer.rotate(rotate, resample=Image.BICUBIC, expand=True)
    if layer.mode != "RGBA":
        layer = layer.convert("RGBA")

    if depth == "far":
        layer = layer.filter(ImageFilter.GaussianBlur(3.4))
        rgb = layer.convert("RGB")
        rgb = Image.blend(rgb, Image.new("RGB", layer.size, PALETTE["paper_deep"]), 0.34)
        rgb.putalpha(layer.split()[3].point(lambda v: int(v * 0.88)))
        layer = rgb
    elif depth == "fg":
        layer = layer.filter(ImageFilter.GaussianBlur(2.2))

    if depth in ("mid", "near", "fg"):
        off, blur, opacity = {
            "mid": (7, 11, 96),
            "near": (18, 9, 132),
            "fg": (26, 20, 118),
        }[depth]
        shadow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        shadow.putalpha(layer.split()[3].point(lambda v: int(v * opacity / 255)))
        shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
        base.alpha_composite(shadow, (xy[0] + off, xy[1] + off))

    base.alpha_composite(layer, xy)


def giant_number(
    text: str,
    height: int,
    color: tuple[int, int, int] = PALETTE["ink"],
    tint: tuple[int, int, int] | None = None,
) -> Image.Image:
    """Giant ultra-condensed stat type with worn print texture."""
    fnt = font(FONT_GIANT, height)
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    tw, th = _text_size(probe, text, fnt)
    pad = int(height * 0.16)
    img = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    box = d.textbbox((0, 0), text, font=fnt)
    d.text((pad - box[0], pad - box[1]), text, font=fnt, fill=(*color, 255))

    # worn ink: knock holes out of the alpha with a coarse noise field
    rng = np.random.default_rng(abs(hash(text)) % 9973)
    wear = rng.random((img.height // 6 + 2, img.width // 6 + 2)).astype(np.float32)
    wear = np.array(
        Image.fromarray((wear * 255).astype(np.uint8)).resize(img.size, Image.BICUBIC),
        dtype=np.float32,
    )
    a = np.asarray(img.split()[3], dtype=np.float32)
    a *= np.clip(0.62 + wear / 255.0 * 0.60, 0.0, 1.0)
    img.putalpha(Image.fromarray(a.clip(0, 255).astype(np.uint8), "L"))

    if tint is not None:
        under = Image.new("RGBA", img.size, (0, 0, 0, 0))
        shade = Image.new("RGBA", img.size, (*tint, 255))
        shade.putalpha(img.split()[3])
        under.alpha_composite(shade, (int(height * 0.035), int(height * 0.035)))
        under.alpha_composite(img)
        img = under
    return img


def stamp(text: str, height: int, color: tuple[int, int, int] = PALETTE["stamp_red"]) -> Image.Image:
    """Rubber stamp: outlined box, roughened ink, slight rotation applied by caller."""
    fnt = font(FONT_HEAVY, height)
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    tw, th = _text_size(probe, text, fnt)
    padx, pady = int(height * 0.46), int(height * 0.34)
    img = Image.new("RGBA", (tw + padx * 2, th + pady * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lw = max(3, height // 12)
    d.rectangle((lw, lw, img.width - lw, img.height - lw), outline=(*color, 255), width=lw)
    box = d.textbbox((0, 0), text, font=fnt)
    d.text((padx - box[0], pady - box[1]), text, font=fnt, fill=(*color, 255))

    rng = np.random.default_rng(abs(hash(text)) % 7919 + 13)
    wear = rng.random((img.height // 4 + 2, img.width // 4 + 2)).astype(np.float32)
    wear = np.array(
        Image.fromarray((wear * 255).astype(np.uint8)).resize(img.size, Image.BICUBIC),
        dtype=np.float32,
    )
    a = np.asarray(img.split()[3], dtype=np.float32) * np.clip(0.40 + wear / 255.0 * 0.85, 0, 1)
    img.putalpha(Image.fromarray(a.clip(0, 255).astype(np.uint8), "L"))
    return img


def accent_strokes(
    size: tuple[int, int],
    seed: int,
    count: int = 5,
    color: tuple[int, int, int] = PALETTE["accent_red"],
    thickness: int = 22,
) -> Image.Image:
    """Offset marker strokes; the reference uses them behind cutouts.

    They read as accents, not rules: short, semi-opaque, and never spanning the
    plate, so they sit under artwork instead of striping across it.
    """
    rng = random.Random(seed)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w, h = size
    for i in range(count):
        y = int(h * (0.16 + 0.68 * i / max(1, count - 1))) + rng.randint(-14, 14)
        x0 = rng.randint(0, int(w * 0.62))
        x1 = x0 + rng.randint(int(w * 0.16), int(w * 0.34))
        t = thickness + rng.randint(-5, 6)
        d.line((x0, y, min(w, x1), y + rng.randint(-7, 7)), fill=(*color, 205), width=t)
    return img.filter(ImageFilter.GaussianBlur(1.0))


def card(
    size: tuple[int, int],
    label: str,
    value: str = "",
    tone: str = "cream",
    seed: int = 0,
    accent: bool = False,
) -> Image.Image:
    """Index card / logo plate with a label and optional value."""
    w, h = size
    img = aged_paper(size, seed, tone).convert("RGBA")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, w - 1, h - 1), outline=(*PALETTE["ink_faint"], 190), width=2)
    if accent:
        d.rectangle((0, 0, w - 1, int(h * 0.085)), fill=(*PALETTE["accent_red"], 255))

    lf = font(FONT_COND, max(16, int(h * (0.20 if value else 0.30))))
    box = d.textbbox((0, 0), label, font=lf)
    lw = box[2] - box[0]
    ly = int(h * (0.16 if value else 0.34))
    d.text(((w - lw) // 2 - box[0], ly - box[1]), label, font=lf, fill=(*PALETTE["ink_soft"], 255))
    if value:
        vf = font(FONT_GIANT, int(h * 0.52))
        vbox = d.textbbox((0, 0), value, font=vf)
        vw = vbox[2] - vbox[0]
        d.text(
            ((w - vw) // 2 - vbox[0], int(h * 0.40) - vbox[1]),
            value,
            font=vf,
            fill=(*PALETTE["ink"], 255),
        )
    return img


def ticker_tape(width: int, height: int, entries: Sequence[tuple[str, bool]], seed: int = 0) -> Image.Image:
    """Narrow paper strip of ticker entries; True marks a red (down/alert) entry."""
    img = aged_paper((width, height), seed, "cream").convert("RGBA")
    d = ImageDraw.Draw(img)
    fnt = font(FONT_MONO, int(height * 0.42))
    x = int(height * 0.4)
    for text, hot in entries:
        col = PALETTE["accent_red"] if hot else PALETTE["ink_soft"]
        d.text((x, int(height * 0.28)), text, font=fnt, fill=(*col, 255))
        x += int(d.textlength(text, font=fnt)) + int(height * 0.9)
        if x > width:
            break
    d.line((0, 1, width, 1), fill=(*PALETTE["ink_faint"], 120), width=2)
    d.line((0, height - 2, width, height - 2), fill=(*PALETTE["ink_faint"], 120), width=2)
    return img


def pin_and_thread(
    base: Image.Image,
    points: Sequence[tuple[int, int]],
    color: tuple[int, int, int] = PALETTE["accent_red"],
) -> None:
    """Red thread routed through push pins, drawn over the current stack."""
    d = ImageDraw.Draw(base)
    if len(points) > 1:
        d.line(list(points), fill=(*color, 235), width=5, joint="curve")
    for px, py in points:
        d.ellipse((px - 13, py - 13, px + 13, py + 13), fill=(20, 18, 16, 90))
        d.ellipse((px - 11, py - 11, px + 11, py + 11), fill=(*color, 255))
        d.ellipse((px - 5, py - 7, px - 1, py - 3), fill=(255, 244, 236, 210))


# ---------------------------------------------------------------------------
# background panels
# ---------------------------------------------------------------------------


def newsprint_panel(size: tuple[int, int], seed: int, headline: str = "", columns: int = 4) -> Image.Image:
    """Fake newspaper page: headline slab plus greeked column text."""
    img = aged_paper(size, seed, "paper_light")
    d = ImageDraw.Draw(img)
    w, h = size
    rng = random.Random(seed)
    y = int(h * 0.05)
    if headline:
        hf = font(FONT_SERIF, int(h * 0.075))
        d.text((int(w * 0.05), y), headline, font=hf, fill=PALETTE["ink"])
        y += int(h * 0.105)
        d.line((int(w * 0.05), y, int(w * 0.95), y), fill=PALETTE["ink_soft"], width=3)
        y += int(h * 0.03)

    col_w = int((w * 0.90) / columns)
    gutter = int(col_w * 0.10)
    for c in range(columns):
        cx = int(w * 0.05) + c * col_w
        cy = y
        while cy < h * 0.95:
            if rng.random() < 0.05:
                d.rectangle(
                    (cx, cy, cx + col_w - gutter, cy + int(h * 0.022)),
                    fill=PALETTE["ink_soft"],
                )
                cy += int(h * 0.038)
                continue
            line_w = int((col_w - gutter) * rng.uniform(0.55, 1.0))
            d.line((cx, cy, cx + line_w, cy), fill=PALETTE["ink_faint"], width=max(2, int(h * 0.004)))
            cy += int(h * 0.0135)
        if c < columns - 1:
            gx = cx + col_w - gutter // 2
            d.line((gx, y, gx, int(h * 0.95)), fill=PALETTE["ink_faint"], width=1)
    return img


def ledger_panel(size: tuple[int, int], seed: int, title: str = "LEDGER") -> Image.Image:
    """Ruled accounting page with numeric columns."""
    img = aged_paper(size, seed, "paper_mid")
    d = ImageDraw.Draw(img)
    w, h = size
    rng = random.Random(seed + 5)
    tf = font(FONT_BOLD, int(h * 0.042))
    d.text((int(w * 0.05), int(h * 0.035)), title, font=tf, fill=PALETTE["ink"])
    top = int(h * 0.11)
    rows = 26
    row_h = int((h * 0.84) / rows)
    nf = font(FONT_MONO, int(row_h * 0.62))
    cols = [0.05, 0.42, 0.58, 0.74, 0.88]
    for r in range(rows):
        ry = top + r * row_h
        d.line((int(w * 0.05), ry, int(w * 0.95), ry), fill=PALETTE["ink_faint"], width=1)
        name_w = int(w * rng.uniform(0.13, 0.33))
        d.line(
            (int(w * cols[0]), ry + row_h // 2, int(w * cols[0]) + name_w, ry + row_h // 2),
            fill=PALETTE["ink_faint"],
            width=max(2, row_h // 6),
        )
        for c in cols[1:]:
            val = f"{rng.uniform(1.2, 99.9):.2f}"
            d.text((int(w * c), ry + row_h * 0.18), val, font=nf, fill=PALETTE["ink_soft"])
    for c in cols[1:]:
        d.line((int(w * c) - 8, top, int(w * c) - 8, top + rows * row_h), fill=PALETTE["ink_faint"], width=1)
    return img


def chart_panel(size: tuple[int, int], seed: int, label: str = "XAU/USD") -> Image.Image:
    """Engraved price chart with hatch fill under the curve."""
    img = aged_paper(size, seed, "paper_light")
    d = ImageDraw.Draw(img)
    w, h = size
    rng = random.Random(seed + 11)
    for i in range(1, 9):
        gy = int(h * i / 9)
        d.line((0, gy, w, gy), fill=PALETTE["ink_faint"], width=1)
    for i in range(1, 13):
        gx = int(w * i / 13)
        d.line((gx, 0, gx, h), fill=PALETTE["ink_faint"], width=1)

    n = 90
    pts = []
    level = 0.55
    for i in range(n):
        level += rng.uniform(-0.055, 0.062)
        level = min(0.92, max(0.12, level))
        pts.append((int(w * i / (n - 1)), int(h * (1.0 - level))))
    # hatch under the curve
    for hx in range(0, w, 13):
        idx = min(n - 1, int(hx / w * (n - 1)))
        d.line((hx, pts[idx][1], hx, h), fill=PALETTE["ink_faint"], width=1)
    d.line(pts, fill=PALETTE["ink"], width=max(3, int(h * 0.006)), joint="curve")

    lf = font(FONT_BOLD, int(h * 0.05))
    d.text((int(w * 0.04), int(h * 0.04)), label, font=lf, fill=PALETTE["ink"])
    return img


def blueprint_panel(size: tuple[int, int], seed: int, label: str = "") -> Image.Image:
    """Technical grid sheet on a deeper stock."""
    img = aged_paper(size, seed, "paper_dark")
    d = ImageDraw.Draw(img)
    w, h = size
    step = int(min(w, h) * 0.030)
    for gx in range(0, w, step):
        d.line((gx, 0, gx, h), fill=PALETTE["ink_faint"], width=1)
    for gy in range(0, h, step):
        d.line((0, gy, w, gy), fill=PALETTE["ink_faint"], width=1)
    for gx in range(0, w, step * 5):
        d.line((gx, 0, gx, h), fill=PALETTE["ink_soft"], width=2)
    for gy in range(0, h, step * 5):
        d.line((0, gy, w, gy), fill=PALETTE["ink_soft"], width=2)
    rng = random.Random(seed + 3)
    for _ in range(9):
        x0, y0 = rng.randrange(0, w - step * 6), rng.randrange(0, h - step * 6)
        d.rectangle(
            (x0, y0, x0 + step * rng.randint(3, 6), y0 + step * rng.randint(2, 5)),
            outline=PALETTE["ink_soft"],
            width=2,
        )
    if label:
        d.text((int(w * 0.04), int(h * 0.03)), label, font=font(FONT_BOLD, int(h * 0.045)), fill=PALETTE["ink"])
    return img


def land_mask_from_map(photo: Image.Image, size: tuple[int, int]) -> Image.Image | None:
    """Extract a clean landmass mask from an aged cartographic photo.

    Land on these plates is warm gold against a dark sea, so a luminance-plus-warmth
    test separates them. Small components are dropped to clear printed marginalia
    (numeral overlays, compass roses). The result is fitted into `size` preserving
    the source aspect, so continents keep their real proportions instead of
    stretching to the plate.
    """
    import cv2

    arr = np.asarray(photo.convert("RGB"), dtype=np.float32)
    # Drop the plate margin. Aged map scans carry a rusty border band that keys as
    # warm as the land does and would weld a flat bar onto the northern latitudes.
    mh, mw = arr.shape[0], arr.shape[1]
    inset_y, inset_x = int(mh * 0.075), int(mw * 0.015)
    arr = arr[inset_y : mh - inset_y, inset_x : mw - inset_x]
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    raw = (((lum > 55) & ((r - b) > 25)).astype(np.uint8)) * 255

    # Only despeckle. Morphological closing bridges the oceans, and interior gaps
    # from engraved detail are welcome here - they read as print texture once the
    # mask is stippled.
    count, labels, stats, _ = cv2.connectedComponentsWithStats(raw, connectivity=8)
    floor = raw.size * 0.0006  # below this a blob is print noise, not an island
    keep = np.zeros(count, dtype=bool)
    for i in range(1, count):
        keep[i] = stats[i, cv2.CC_STAT_AREA] >= floor
    raw = np.where(keep[labels], 255, 0).astype(np.uint8)

    sw, sh = raw.shape[1], raw.shape[0]
    tw, th = size
    scale = min(tw / sw, th / sh)
    fw, fh = max(1, int(sw * scale)), max(1, int(sh * scale))
    fitted = Image.fromarray(raw, "L").resize((fw, fh), Image.LANCZOS)
    mask = Image.new("L", size, 0)
    mask.paste(fitted, ((tw - fw) // 2, (th - fh) // 2))
    mask = mask.point(lambda v: 255 if v > 120 else 0)

    frac = float(np.asarray(mask, dtype=np.float32).mean()) / 255.0
    if not 0.05 <= frac <= 0.55:
        return None
    return mask


def map_panel(size: tuple[int, int], seed: int, map_source: Path | None = None) -> Image.Image:
    """Faded world plate: graticule, stippled landmass, red route arcs.

    Uses `map_source` for a true world outline when one is supplied and keys
    cleanly; otherwise falls back to coarse procedural landmasses.
    """
    img = aged_paper(size, seed, "paper_mid")
    d = ImageDraw.Draw(img)
    w, h = size

    for i in range(1, 12):
        gy = int(h * i / 12)
        d.line((0, gy, w, gy), fill=PALETTE["ink_faint"], width=1)
    for i in range(1, 20):
        gx = int(w * i / 20)
        d.line((gx, 0, gx, h), fill=PALETTE["ink_faint"], width=1)
    d.line((0, h // 2, w, h // 2), fill=PALETTE["ink_soft"], width=3)

    land: Image.Image | None = None
    if map_source is not None and Path(map_source).is_file():
        try:
            land = land_mask_from_map(Image.open(map_source), size)
        except OSError:
            land = None

    if land is None:
        masses = [
            [(0.10, 0.20), (0.20, 0.14), (0.27, 0.26), (0.22, 0.40), (0.13, 0.38)],
            [(0.20, 0.50), (0.27, 0.46), (0.31, 0.60), (0.26, 0.80), (0.20, 0.70)],
            [(0.46, 0.16), (0.56, 0.13), (0.58, 0.25), (0.50, 0.30), (0.45, 0.25)],
            [(0.47, 0.34), (0.57, 0.32), (0.60, 0.52), (0.53, 0.72), (0.46, 0.55)],
            [(0.60, 0.18), (0.80, 0.14), (0.88, 0.30), (0.76, 0.44), (0.62, 0.36)],
            [(0.82, 0.62), (0.92, 0.60), (0.94, 0.74), (0.85, 0.76)],
        ]
        land = Image.new("L", size, 0)
        ld = ImageDraw.Draw(land)
        for poly in masses:
            ld.polygon([(int(px * w), int(py * h)) for px, py in poly], fill=255)
        land = land.filter(ImageFilter.GaussianBlur(min(w, h) * 0.008))
        land = land.point(lambda v: 255 if v > 110 else 0)

    stipple = halftone(Image.new("L", size, 150), cell=10, angle=45.0, ink=PALETTE["ink_soft"], alpha=land)
    img = img.convert("RGBA")
    img.alpha_composite(stipple)
    d = ImageDraw.Draw(img)
    outline = land.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(3))
    edge = Image.new("RGBA", size, (*PALETTE["ink"], 0))
    edge.putalpha(outline.point(lambda v: 190 if v > 60 else 0))
    img.alpha_composite(edge)

    rng = random.Random(seed + 17)
    for _ in range(7):
        x0, y0 = rng.randrange(int(w * 0.1), int(w * 0.9)), rng.randrange(int(h * 0.15), int(h * 0.85))
        x1, y1 = rng.randrange(int(w * 0.1), int(w * 0.9)), rng.randrange(int(h * 0.15), int(h * 0.85))
        mx, my = (x0 + x1) // 2, min(y0, y1) - abs(x1 - x0) // 5
        pts = []
        for t in range(0, 21):
            u = t / 20
            bx = (1 - u) ** 2 * x0 + 2 * (1 - u) * u * mx + u * u * x1
            by = (1 - u) ** 2 * y0 + 2 * (1 - u) * u * my + u * u * y1
            pts.append((bx, by))
        d.line(pts, fill=(*PALETTE["accent_red"], 150), width=3, joint="curve")
    return img.convert("RGB")


def circuit_panel(size: tuple[int, int], seed: int) -> Image.Image:
    """Circuit trace print on aged stock."""
    img = aged_paper(size, seed, "paper_dark")
    d = ImageDraw.Draw(img)
    w, h = size
    rng = random.Random(seed + 23)
    step = int(min(w, h) * 0.05)
    for _ in range(46):
        x, y = rng.randrange(0, w, step), rng.randrange(0, h, step)
        pts = [(x, y)]
        for _ in range(rng.randint(2, 5)):
            if rng.random() < 0.5:
                x += rng.choice((-1, 1)) * step * rng.randint(1, 4)
            else:
                y += rng.choice((-1, 1)) * step * rng.randint(1, 4)
            pts.append((max(0, min(w, x)), max(0, min(h, y))))
        d.line(pts, fill=PALETTE["ink_soft"], width=max(2, step // 9), joint="curve")
        d.ellipse((pts[-1][0] - 7, pts[-1][1] - 7, pts[-1][0] + 7, pts[-1][1] + 7), outline=PALETTE["ink"], width=3)
    for _ in range(11):
        x, y = rng.randrange(0, int(w * 0.85)), rng.randrange(0, int(h * 0.85))
        cw, ch = step * rng.randint(2, 4), step * rng.randint(2, 3)
        d.rectangle((x, y, x + cw, y + ch), outline=PALETTE["ink"], width=3)
        for i in range(1, 5):
            px = x + cw * i // 5
            d.line((px, y - step // 2, px, y), fill=PALETTE["ink_soft"], width=3)
            d.line((px, y + ch, px, y + ch + step // 2), fill=PALETTE["ink_soft"], width=3)
    return img


def alert_wash(size: tuple[int, int], strength: float = 0.34) -> Image.Image:
    """The named ALERT WASH beat: red pass biased to the frame edges."""
    w, h = size
    wash = Image.new("RGBA", size, (*PALETTE["accent_red"], 0))
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    d.rectangle((0, 0, w, h), fill=int(255 * strength))
    inset = int(min(w, h) * 0.22)
    d.ellipse((inset, inset, w - inset, h - inset), fill=int(255 * strength * 0.30))
    mask = mask.filter(ImageFilter.GaussianBlur(inset * 0.6))
    wash.putalpha(mask)
    return wash

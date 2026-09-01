"""
0825 Vox split-screen master.

Builds a 1080x1920 vertical master from `0825.mp4`: an animated paper-diorama
stream fills the top half, the raw presenter fills the bottom half, and burnt-in
Hinglish captions run along the lower safe area.

The diorama plates are composed from `vox_diorama` primitives in the "Paper
Diorama" language of `CL3 Vox Videos/image-prompts.md` - aged print, halftone
cutouts, giant stat numbers, rubber stamps, pins and thread. Every scene changes
its background and gets exactly one committed camera move. Audio stays
sound-design only: no music, no VO, seven procedural cues on real beats.

Scene durations are declared in frames so the six clips sum to the source's exact
1555 frames at 30fps rather than drifting on floating-point seconds.

Run:
    server/.venv/Scripts/python.exe server/build_0825_vox_splitscreen_master.py
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import wave
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from imageio_ffmpeg import get_ffmpeg_exe
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vox_diorama import (  # noqa: E402
    CANVAS,
    PALETTE,
    accent_strokes,
    aged_paper,
    alert_wash,
    blueprint_panel,
    card,
    chart_panel,
    circuit_panel,
    cutout_from_photo,
    giant_number,
    grain,
    halftone,
    keyline,
    ledger_panel,
    map_panel,
    newsprint_panel,
    pin_and_thread,
    place,
    stamp,
    ticker_tape,
    torn_edge,
)

FFMPEG = get_ffmpeg_exe()
WORKSPACE = Path(__file__).resolve().parent.parent
SOURCE_VIDEO = Path(r"D:\Downloads\0825.mp4")
SLUG = "0825-vox-splitscreen-master"
OUTPUT_DIR = WORKSPACE / "storage" / "deliverables" / SLUG
WORK_DIR = OUTPUT_DIR / "work"
ASSET_DIR = WORKSPACE / "storage" / "assets" / "vox_0825_source"

FPS = 30
TOP_W, TOP_H = 1080, 960
SR = 48000


# ---------------------------------------------------------------------------
# script
# ---------------------------------------------------------------------------

# Verified against two faster-whisper passes (small + medium) over the source
# audio; the 40.96-47.14 line was re-transcribed at `medium` because `small`
# dropped its subject.
SCRIPT: list[tuple[float, float, str]] = [
    (0.00, 4.06, "Aapne notice kiya hai GOLD ka price literally SECONDS mein change ho jaata hai"),
    (4.16, 6.86, "Lekin question ye hai price change karta KAUN hai"),
    (6.98, 9.30, "Simple answer hai BUYERS aur SELLERS"),
    (9.38, 11.60, "Jab buyers zyada price dene ko ready hote hain"),
    (11.70, 13.54, "Aur sellers apni price change karte hain"),
    (13.60, 14.96, "Toh market price bhi move hota hai"),
    (15.04, 16.06, "Imagine ek GOLD SHOP"),
    (16.18, 18.18, "Agar ek buyer 7000 offer kar raha hai"),
    (18.36, 19.36, "Price wahi ho sakta hai"),
    (19.44, 21.76, "Lekin agar buyers 7050 bhi dene lagein"),
    (22.02, 23.90, "Seller bhi apni asking price badha sakta hai"),
    (23.90, 28.22, "Ab imagine karo ye process ek shop mein nahi poori DUNIYA mein SIMULTANEOUSLY ho raha hai"),
    (28.22, 32.92, "BANKS INSTITUTIONS TRADERS aur INVESTORS continuously buy aur sell kar rahe hain"),
    (32.92, 38.22, "Aur jab important ECONOMIC NEWS aati hai buyers aur sellers ka BALANCE seconds mein change ho sakta hai"),
    (38.22, 40.96, "Isi liye GOLD ka price SUDDENLY move kar sakta hai"),
    (40.96, 47.14, "Isi fast moving market mein EA pre-defined rules ke according conditions MONITOR kar ke AUTOMATICALLY action le sakta hai"),
    (47.14, 51.66, "Aise Forex Gold aur EA concepts simple language mein samajhne hain toh FOLLOW KAR LO"),
]

# Alarm words take red, data words take cyan; a page inherits whichever it holds.
RED_WORDS = {"GOLD", "SELLERS", "SUDDENLY", "ECONOMIC", "NEWS", "KAUN", "FOLLOW", "BALANCE"}
CYAN_WORDS = {
    "SECONDS", "BUYERS", "7000", "7050", "DUNIYA", "SIMULTANEOUSLY", "SHOP",
    "BANKS", "INSTITUTIONS", "TRADERS", "INVESTORS", "EA", "MONITOR", "AUTOMATICALLY",
}


@dataclass
class Scene:
    key: str
    frames: int
    motion: str
    compose: str
    plate: Path | None = field(default=None, compare=False)


# Frame counts sum to 1555 - the source's exact frame count - so the diorama
# stream and the presenter stream stay locked with no tail padding.
SCENES: list[Scene] = [
    Scene("s1_hook", 206, "push_in", "compose_hook"),
    Scene("s2_sides", 243, "pan_left", "compose_two_sides"),
    Scene("s3_shop", 268, "dive_down", "compose_gold_shop"),
    Scene("s4_world", 271, "pan_left", "compose_whole_world"),
    Scene("s5_news", 241, "push_in", "compose_news"),
    Scene("s6_ea", 326, "push_in", "compose_ea"),
]

# Procedural cues on semantic beats, not on a grid.
SFX_CUES: list[tuple[str, int, float]] = [
    ("riser", 0, 0.55),          # open
    ("tick", 2400, 0.70),        # "SECONDS mein change"
    ("paper_pop", 4160, 0.65),   # "question ye hai"
    ("stamp_thud", 6980, 0.85),  # "BUYERS aur SELLERS"
    ("paper_whoosh", 14960, 0.70),  # cut to the gold shop
    ("tick", 19440, 0.80),       # 7000 -> 7050 tick-up
    ("paper_whoosh", 23900, 0.70),  # pull back to the world
    ("alert_drop", 32920, 0.90),  # economic news
    ("riser", 40960, 0.60),      # EA
    ("chime", 47140, 0.80),      # CTA
]


# ---------------------------------------------------------------------------
# audio cues
# ---------------------------------------------------------------------------


def make_wav(path: Path, samples: np.ndarray, sr: int = SR) -> Path:
    """Write a mono 16-bit WAV, clipped to full scale."""
    data = np.clip(samples, -1.0, 1.0)
    pcm = (data * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return path


def generate_vox_sfx_suite(out_dir: Path) -> dict[str, Path]:
    """Seven procedural cues. Carried from the 0824 master: these define the style."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cues: dict[str, Path] = {}

    # stamp_thud - sub thump plus paper crunch
    n = int(SR * 0.6)
    t = np.arange(n) / SR
    thud = np.sin(2 * np.pi * 62 * t) * np.exp(-t * 11.0)
    crunch = np.random.default_rng(11).normal(0, 1, n) * np.exp(-t * 34.0) * 0.35
    cues["stamp_thud"] = make_wav(out_dir / "stamp_thud.wav", thud * 0.9 + crunch)

    # paper_whoosh - filtered noise with a sine-squared envelope
    n = int(SR * 0.24)
    t = np.arange(n) / SR
    noise = np.random.default_rng(23).normal(0, 1, n)
    env = np.sin(np.pi * t / t[-1]) ** 2
    cues["paper_whoosh"] = make_wav(out_dir / "paper_whoosh.wav", noise * env * 0.55)

    # paper_pop
    n = int(SR * 0.12)
    t = np.arange(n) / SR
    cues["paper_pop"] = make_wav(
        out_dir / "paper_pop.wav", np.sin(2 * np.pi * 1500 * t) * np.exp(-t * 46.0) * 0.5
    )

    # tick
    n = int(SR * 0.05)
    t = np.arange(n) / SR
    cues["tick"] = make_wav(
        out_dir / "tick.wav", np.sin(2 * np.pi * 2600 * t) * np.exp(-t * 120.0) * 0.45
    )

    # riser - exponential frequency ramp
    n = int(SR * 0.8)
    t = np.arange(n) / SR
    freq = 80 * (460 / 80) ** (t / t[-1])
    phase = 2 * np.pi * np.cumsum(freq) / SR
    cues["riser"] = make_wav(out_dir / "riser.wav", np.sin(phase) * (t / t[-1]) ** 1.5 * 0.42)

    # alert_drop - descending sub
    n = int(SR * 0.7)
    t = np.arange(n) / SR
    freq = 160 * (40 / 160) ** (t / t[-1])
    phase = 2 * np.pi * np.cumsum(freq) / SR
    cues["alert_drop"] = make_wav(out_dir / "alert_drop.wav", np.sin(phase) * np.exp(-t * 3.2) * 0.7)

    # chime - C6 + E6 dyad
    n = int(SR * 0.5)
    t = np.arange(n) / SR
    dyad = np.sin(2 * np.pi * 1046.5 * t) + np.sin(2 * np.pi * 1318.5 * t)
    cues["chime"] = make_wav(out_dir / "chime.wav", dyad * np.exp(-t * 5.0) * 0.28)

    return cues


# ---------------------------------------------------------------------------
# plate helpers
# ---------------------------------------------------------------------------


def place_at(
    base: Image.Image,
    layer: Image.Image,
    fx: float,
    fy: float,
    depth: str = "mid",
    rotate: float = 0.0,
) -> None:
    """Centre `layer` on the plate at fractional coordinates, clamped in bounds.

    Stamps and giant type change size with their text and grow again when rotated,
    so fractional top-left placement silently pushes them off-canvas. Centring and
    clamping keeps every element whole no matter how the copy changes.
    """
    probe = layer.rotate(rotate, resample=Image.BICUBIC, expand=True) if rotate else layer
    lw, lh = probe.size
    margin = 18
    x = int(W * fx - lw / 2)
    y = int(H * fy - lh / 2)
    x = max(margin, min(W - lw - margin, x))
    y = max(margin, min(H - lh - margin, y))
    place(base, probe, (x, y), depth)


def clipping(photo_path: Path, size: tuple[int, int], cell: int = 4, seed: int = 0) -> Image.Image:
    """A halftoned photo clipping with a torn bottom edge and a print keyline.

    Photos that are not shot against a light background cannot be keyed into a
    free-standing cutout, so they get pasted in as rectangular print clippings -
    which is how the reference plates handle scenery and objects anyway.

    `cell` stays small here. A person cutout survives coarse dots because it is one
    big silhouette, but a product shot needs enough dots across the subject to carry
    its form: at cell 9 a stack of ingots prints as noise, at cell 4 it reads.
    """
    photo = Image.open(photo_path).convert("RGB")
    pw, ph = photo.size
    tw, th = size
    scale = max(tw / pw, th / ph)
    photo = photo.resize((max(1, int(pw * scale)), max(1, int(ph * scale))), Image.LANCZOS)
    left = (photo.width - tw) // 2
    top = (photo.height - th) // 2
    photo = photo.crop((left, top, left + tw, top + th))

    flat = np.asarray(photo.convert("L"), dtype=np.float32) / 255.0
    lo, hi = np.percentile(flat, 2.0), np.percentile(flat, 98.0)
    if hi - lo > 0.04:
        flat = np.clip((flat - lo) / (hi - lo), 0.0, 1.0)

    # Halftone assumes a light substrate: ink where the source is dark. A studio
    # product shot on black therefore prints its background solid and its subject as
    # voids. Polarity is a property of the background, not the whole frame, so test
    # the border - a dim but light-substrate scene (newsprint in shadow) has a low
    # overall median yet a clearly lit border, and must not be inverted.
    edge = 10
    border = np.concatenate([
        flat[:edge].ravel(), flat[-edge:].ravel(),
        flat[:, :edge].ravel(), flat[:, -edge:].ravel(),
    ])
    if float(np.median(border)) < 0.28:
        flat = 1.0 - flat

    flat = np.clip(0.12 + (flat**0.62) * 0.86, 0.0, 1.0)
    graphic = Image.fromarray((flat * 255).astype(np.uint8), "L")

    plate = aged_paper(size, seed, "cream").convert("RGBA")
    plate.alpha_composite(halftone(graphic, cell=cell, angle=45.0, ink=PALETTE["ink"]))
    plate.putalpha(torn_edge(size, seed + 5, "bottom").point(lambda v: 255 if v > 40 else 0))
    return keyline(plate, width=7)


def torn_strip(size: tuple[int, int], seed: int, tone: str = "cream", side: str = "bottom") -> Image.Image:
    """A paper strip with one torn edge, for banding a plate."""
    strip = aged_paper(size, seed, tone).convert("RGBA")
    strip.putalpha(torn_edge(size, seed, side).point(lambda v: 255 if v > 40 else 0))
    return strip


def load_cutouts(names: list[str], target_h: int, cell: int = 8) -> list[Image.Image]:
    """Key the named source photos into halftone cutouts, skipping any that fail."""
    out: list[Image.Image] = []
    for name in names:
        path = ASSET_DIR / f"{name}.jpg"
        if not path.is_file():
            continue
        try:
            photo = Image.open(path).convert("RGB")
        except OSError:
            continue
        cut = cutout_from_photo(photo, target_h, cell=cell)
        if cut is not None:
            out.append(cut)
    return out


def finish(base: Image.Image, seed: int) -> Image.Image:
    """Flatten a composed plate and lay print grain over the whole stack."""
    return grain(base.convert("RGB"), strength=8.0, seed=seed)


# ---------------------------------------------------------------------------
# scene composers - each returns a CANVAS-sized RGB plate
# ---------------------------------------------------------------------------

W, H = CANVAS


def compose_hook() -> Image.Image:
    """0.00-6.86  GOLD moves in SECONDS - and who moves it?"""
    base = chart_panel((W, H), 101, label="XAU/USD  SPOT GOLD").convert("RGBA")
    base.alpha_composite(accent_strokes((W, H), 102, count=4, thickness=26))

    place(base, torn_strip((W, int(H * 0.20)), 103, "paper_light", "bottom"), (0, 0), "far")
    place_at(base, clipping(ASSET_DIR / "goldbars_1.jpg", (600, 450), cell=4, seed=104),
             0.74, 0.28, "mid", rotate=-3.0)

    place_at(base, giant_number("SECONDS", 250, tint=PALETTE["accent_red"]), 0.36, 0.46, "near")
    place_at(base, card((430, 250), "PRICE MOVES IN", "1s", seed=105, accent=True),
             0.20, 0.71, "near", rotate=-2.0)
    place_at(base, stamp("WHO?", 190), 0.70, 0.72, "near", rotate=-9.0)

    place(base, ticker_tape(W, 92, [
        ("XAU 3412.60", False), ("+18.40", False), ("XAU 3418.90", False),
        ("-6.20", True), ("XAU 3421.05", False), ("+2.15", False),
    ], seed=106), (0, int(H * 0.89)), "fg")
    return finish(base, 101)


def compose_two_sides() -> Image.Image:
    """6.86-14.96  Buyers on one side, sellers on the other."""
    base = ledger_panel((W, H), 201, title="ORDER BOOK").convert("RGBA")
    place(base, torn_strip((int(W * 0.52), H), 202, "paper_light", "right"), (0, 0), "far")
    base.alpha_composite(accent_strokes((W, H), 203, count=5, thickness=24))

    buyers = load_cutouts(["person_b_0", "person_b_1"], int(H * 0.52))
    sellers = load_cutouts(["person_c_2", "person_c_3"], int(H * 0.52))

    for i, cut in enumerate(buyers):
        place(base, cut, (int(W * (0.03 + 0.13 * i)), int(H * (0.40 - 0.03 * i))),
              "mid" if i == 0 else "near", rotate=-2.0 + 3.0 * i)
    for i, cut in enumerate(sellers):
        place(base, cut, (int(W * (0.60 + 0.14 * i)), int(H * (0.40 - 0.02 * i))),
              "mid" if i == 0 else "near", rotate=2.0 - 3.0 * i)

    place_at(base, giant_number("BUYERS", 150), 0.22, 0.14, "near")
    place_at(base, giant_number("SELLERS", 150, tint=PALETTE["accent_red"]), 0.77, 0.14, "near")
    place_at(base, card((360, 210), "BID", "7,000", seed=204), 0.17, 0.83, "near", rotate=-3.0)
    place_at(base, card((360, 210), "ASK", "7,050", seed=205, accent=True),
             0.79, 0.83, "near", rotate=3.0)
    return finish(base, 201)


def compose_gold_shop() -> Image.Image:
    """14.96-23.90  One shop, one counter: 7,000 becomes 7,050."""
    base = blueprint_panel((W, H), 301, label="GOLD SHOP / COUNTER PLAN").convert("RGBA")
    place(base, torn_strip((W, int(H * 0.26)), 302, "paper_mid", "top"),
          (0, int(H * 0.74)), "far")
    # goldcoins_1, not _2: _2 is a Bitcoin, and a crypto coin next to a spot-gold
    # asking price would assert something the script never says.
    place_at(base, clipping(ASSET_DIR / "goldcoins_1.jpg", (680, 500), cell=4, seed=303),
             0.26, 0.28, "mid", rotate=-2.5)

    place_at(base, card((400, 230), "BUYER OFFERS", "7,000", seed=304),
             0.76, 0.18, "near", rotate=2.0)
    place_at(base, card((400, 230), "THEN OFFERS", "7,050", seed=305, accent=True),
             0.78, 0.47, "near", rotate=-3.0)

    place_at(base, giant_number("+50", 290, tint=PALETTE["accent_red"]), 0.22, 0.70, "near")
    place_at(base, card((420, 190), "ASKING PRICE", "UP", seed=306),
             0.75, 0.74, "near", rotate=2.5)
    place_at(base, stamp("DEAL", 170), 0.62, 0.93, "fg", rotate=-8.0)
    return finish(base, 301)


def compose_whole_world() -> Image.Image:
    """23.90-32.92  The same process, everywhere, at once."""
    base = map_panel((W, H), 401, map_source=ASSET_DIR / "worldmap_3.jpg").convert("RGBA")

    labels = [
        ("BANKS", (0.05, 0.07)),
        ("INSTITUTIONS", (0.62, 0.11)),
        ("TRADERS", (0.06, 0.74)),
        ("INVESTORS", (0.62, 0.80)),
    ]
    cw, ch = 410, 170
    boxes = [(int(W * fx), int(H * fy)) for _, (fx, fy) in labels]

    # Thread and pins first, so both sit behind the cards. Pinning at the inner
    # corner rather than the card centre keeps the pin head off the label - a pin
    # drawn last at the centre lands squarely on the word.
    corners = [
        (boxes[0][0] + cw, boxes[0][1] + ch),
        (boxes[1][0], boxes[1][1] + ch),
        (boxes[2][0] + cw, boxes[2][1]),
        (boxes[3][0], boxes[3][1]),
    ]
    pin_and_thread(base, [corners[0], corners[3], corners[1], corners[2]])

    place_at(base, giant_number("24/7", 240, color=PALETTE["cream"], tint=PALETTE["accent_red"]),
             0.50, 0.44, "near")

    for i, ((text, _), (x, y)) in enumerate(zip(labels, boxes)):
        place(base, card((cw, ch), text, seed=410 + i, accent=(i % 2 == 0)),
              (x, y), "near", rotate=-3.0 + 2.0 * i)

    place_at(base, stamp("SIMULTANEOUS", 120), 0.50, 0.66, "fg", rotate=-6.0)
    return finish(base, 401)


def compose_news() -> Image.Image:
    """32.92-40.96  Economic news flips the balance in seconds."""
    # Headline kept short: newsprint_panel sets it at 7.5% of plate height with no
    # wrapping, so a longer string runs off the right edge.
    base = newsprint_panel((W, H), 501, headline="ECONOMIC DATA HITS", columns=4).convert("RGBA")
    base.alpha_composite(accent_strokes((W, H), 503, count=6, thickness=28))
    place_at(base, clipping(ASSET_DIR / "newspaper_1.jpg", (700, 520), cell=4, seed=502),
             0.74, 0.30, "mid", rotate=3.0)

    place(base, torn_strip((W, int(H * 0.17)), 504, "cream", "bottom"), (0, int(H * 0.46)), "near")
    place_at(base, giant_number("NEWS", 210, tint=PALETTE["accent_red"]), 0.26, 0.50, "fg")

    place_at(base, card((430, 220), "BALANCE SHIFTS IN", "2s", seed=505, accent=True),
             0.22, 0.72, "near", rotate=-2.0)
    place_at(base, card((380, 200), "GOLD", "MOVES", seed=506), 0.74, 0.74, "near", rotate=3.0)
    place_at(base, stamp("BREAKING", 150), 0.48, 0.91, "fg", rotate=-7.0)

    base.alpha_composite(alert_wash((W, H), strength=0.18))
    return finish(base, 501)


def compose_ea() -> Image.Image:
    """40.96-51.83  An EA monitors the rules and acts - then the CTA."""
    base = circuit_panel((W, H), 601).convert("RGBA")
    place(base, torn_strip((W, int(H * 0.22)), 602, "paper_light", "bottom"), (0, 0), "far")

    place_at(base, giant_number("EA", 300, tint=PALETTE["accent_red"]), 0.18, 0.17, "near")
    rules = [("RULE 01", "MONITOR"), ("RULE 02", "TRIGGER"), ("RULE 03", "EXECUTE")]
    for i, (label, value) in enumerate(rules):
        place_at(base, card((430, 200), label, value, seed=610 + i, accent=(i == 2)),
                 0.75, 0.15 + 0.22 * i, "near", rotate=-2.5 + 2.5 * i)

    place_at(base, card((470, 210), "ACTS", "AUTO", seed=613), 0.22, 0.47, "near", rotate=2.0)
    place_at(base, stamp("FOLLOW", 210), 0.40, 0.76, "fg", rotate=-8.0)
    place(base, ticker_tape(W, 92, [
        ("FOREX", False), ("GOLD", False), ("EA", True), ("SIMPLE LANGUAGE", False),
    ], seed=614), (0, int(H * 0.90)), "fg")
    return finish(base, 601)


COMPOSERS = {
    "compose_hook": compose_hook,
    "compose_two_sides": compose_two_sides,
    "compose_gold_shop": compose_gold_shop,
    "compose_whole_world": compose_whole_world,
    "compose_news": compose_news,
    "compose_ea": compose_ea,
}


# ---------------------------------------------------------------------------
# camera motion
# ---------------------------------------------------------------------------


def create_vox_camera_motion_clip(
    image_path: Path, output_clip_path: Path, frames: int, motion_type: str = "push_in"
) -> Path:
    """Render one committed camera move over a still, as a TOP_W x TOP_H clip.

    Crop-and-resize with a Bezier ease so the move settles instead of stopping
    dead. `frames` is exact - the six clips must sum to the source frame count.
    """
    plate = cv2.imread(str(image_path))
    if plate is None:
        raise RuntimeError(f"cannot read plate: {image_path}")
    ph, pw = plate.shape[:2]

    writer = cv2.VideoWriter(
        str(output_clip_path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (TOP_W, TOP_H)
    )
    if not writer.isOpened():
        raise RuntimeError(f"cannot open writer: {output_clip_path}")

    for i in range(frames):
        prog = i / max(1, frames - 1)
        ease = prog * prog * (3.0 - 2.0 * prog)

        if motion_type == "push_in":
            scale = 1.0 + 0.15 * ease
            fx, fy = 0.5, 0.5
        elif motion_type == "pan_left":
            scale = 1.08
            fx, fy = 0.2 + 0.6 * ease, 0.5
        elif motion_type == "dive_down":
            scale = 1.10
            fx, fy = 0.5, 0.1 + 0.7 * ease
        else:
            scale = 1.0
            fx, fy = 0.5, 0.5

        cw, ch = int(pw / scale), int(ph / scale)
        x = int((pw - cw) * fx)
        y = int((ph - ch) * fy)
        crop = plate[y : y + ch, x : x + cw]
        writer.write(cv2.resize(crop, (TOP_W, TOP_H), interpolation=cv2.INTER_LANCZOS4))

    writer.release()
    return output_clip_path


# ---------------------------------------------------------------------------
# captions
# ---------------------------------------------------------------------------


def fmt_time(sec: float) -> str:
    sec = max(0.0, sec)
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build_vox_subtitles(ass_path: Path) -> Path:
    """Burn-in captions: four-word pages, one style per page by keyword."""
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Consolas,42,&H00FFFFFF,&H000000FF,&H000B1012,&HE00B1012,1,0,0,0,100,100,1,0,3,14,0,2,40,40,140,1
Style: HighlightCyan,Consolas,44,&H0000E5FF,&H000000FF,&H000B1012,&HE00B1012,1,0,0,0,100,100,1,0,3,16,0,2,40,40,140,1
Style: HighlightRed,Consolas,44,&H001F2ED6,&H000000FF,&H000B1012,&HE00B1012,1,0,0,0,100,100,1,0,3,16,0,2,40,40,140,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for start, end, text in SCRIPT:
        words = text.split()
        pages = [words[i : i + 4] for i in range(0, len(words), 4)]
        if not pages:
            continue
        span = (end - start) / len(pages)
        for idx, page in enumerate(pages):
            upper = {w.upper().strip(".,") for w in page}
            if upper & RED_WORDS:
                style = "HighlightRed"
            elif upper & CYAN_WORDS:
                style = "HighlightCyan"
            else:
                style = "Default"
            p_start = start + idx * span
            p_end = min(end, p_start + span)
            body = " ".join(page).upper()
            lines.append(
                f"Dialogue: 0,{fmt_time(p_start)},{fmt_time(p_end)},{style},,0,0,0,,{body}"
            )

    ass_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ass_path


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------


def run(cmd: list[str], label: str) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        tail = "\n".join((proc.stderr or "").strip().splitlines()[-25:])
        raise RuntimeError(f"{label} failed (exit {proc.returncode}):\n{tail}")
    return proc.stderr or ""


def measure_loudnorm(inputs: list[str], audio_chains: list[str]) -> dict[str, str]:
    """First loudnorm pass: measure the mixed programme.

    Single-pass loudnorm is a streaming estimator - it cannot know a programme's
    integrated loudness or true peak until it has heard all of it, so it lands wide
    of the target and its TP ceiling does not hold. Measuring first, then correcting
    with the measured values, is what actually hits -14 LUFS / -1.0 dBTP.
    """
    chains = list(audio_chains)
    chains.append("[a_mixed]loudnorm=I=-14:TP=-1.0:LRA=7:print_format=json[a_probe]")
    stderr = run(
        inputs + [
            "-filter_complex", ";".join(chains),
            "-map", "[a_probe]", "-f", "null", os.devnull,
        ],
        "loudnorm measure",
    )
    start = stderr.rfind("{")
    end = stderr.rfind("}")
    if start == -1 or end == -1:
        raise RuntimeError("loudnorm measure produced no JSON summary")
    return json.loads(stderr[start : end + 1])


def concat_clips(clips: list[Path], out_path: Path) -> Path:
    listing = WORK_DIR / "clips.txt"
    listing.write_text(
        "".join(f"file '{p.as_posix()}'\n" for p in clips), encoding="utf-8"
    )
    run(
        [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
         "-c:v", "libx264", "-preset", "fast", "-crf", "14",
         "-pix_fmt", "yuv420p", "-r", str(FPS), str(out_path)],
        "concat",
    )
    return out_path


def render_master(top_half: Path, ass_path: Path, sfx: dict[str, Path], out_path: Path) -> Path:
    ass_filter_path = str(ass_path).replace("\\", "/").replace(":", "\\:")

    inputs = [FFMPEG, "-y", "-i", str(SOURCE_VIDEO), "-i", str(top_half)]
    for key, _, _ in SFX_CUES:
        inputs += ["-i", str(sfx[key])]

    video_chains = [
        f"[1:v]scale={TOP_W}:{TOP_H},fps={FPS}[v_top]",
        f"[0:v]scale=1080:1920,crop=1080:960:0:380,fps={FPS}[v_bottom]",
        "[v_top][v_bottom]vstack=inputs=2[v_split]",
        "[v_split]drawbox=x=0:y=956:w=1080:h=8:color=#1A1A1A@1.0:t=fill[v_divided]",
        "[v_divided]eq=contrast=1.08:brightness=0.01:saturation=1.12[v_graded]",
        f"[v_graded]ass='{ass_filter_path}'[v_out]",
    ]

    # amix normalises by input count, so the dialogue would land ~21 dB down with
    # eleven inputs; normalize=0 keeps the cue `volume` values meaning what they say
    # and leaves the final level to loudnorm.
    audio_chains: list[str] = []
    labels = []
    for i, (_, delay_ms, vol) in enumerate(SFX_CUES):
        tag = f"sfx{i}"
        audio_chains.append(f"[{i + 2}:a]adelay={delay_ms}|{delay_ms},volume={vol}[{tag}]")
        labels.append(f"[{tag}]")
    audio_chains.append(
        f"[0:a]{''.join(labels)}amix=inputs={len(labels) + 1}:duration=first:"
        "normalize=0:dropout_transition=2[a_mixed]"
    )

    m = measure_loudnorm(inputs, audio_chains)
    print(
        f"  measured  I={m['input_i']} LUFS  TP={m['input_tp']} dBTP  LRA={m['input_lra']}"
    )
    # loudnorm's own TP option is a soft ceiling and cannot save already-clipped
    # source: this presenter audio arrives at +1.4 dBTP, so the linear make-up gain
    # lands well over 0 dBFS and only a real limiter brings it back. `level=false`
    # matters - alimiter auto-levels to the ceiling by default, which would undo the
    # loudness target. The ceiling is set below -1.0 dBFS to leave room for AAC
    # reconstruction overshoot, which is measured as true peak but not as sample peak.
    correct = [
        "[a_mixed]loudnorm=I=-14:TP=-1.0:LRA=7:linear=true"
        f":measured_I={m['input_i']}:measured_TP={m['input_tp']}"
        f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
        f":offset={m['target_offset']}[a_normed]",
        "[a_normed]alimiter=limit=0.83:attack=5:release=50:level=false[a_out]",
    ]

    run(
        inputs + [
            "-filter_complex", ";".join(video_chains + audio_chains + correct),
            "-map", "[v_out]", "-map", "[a_out]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "15", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
            str(out_path),
        ],
        "master",
    )
    return out_path


def main() -> int:
    if not SOURCE_VIDEO.is_file():
        print(f"missing source: {SOURCE_VIDEO}")
        return 1
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    plates_dir = WORK_DIR / "plates"
    plates_dir.mkdir(parents=True, exist_ok=True)

    total = sum(s.frames for s in SCENES)
    print(f"scenes: {len(SCENES)}  frames: {total}  ({total / FPS:.2f}s @ {FPS}fps)")

    clips: list[Path] = []
    for scene in SCENES:
        plate_path = plates_dir / f"{scene.key}.png"
        COMPOSERS[scene.compose]().save(plate_path)
        scene.plate = plate_path
        clip = create_vox_camera_motion_clip(
            plate_path, WORK_DIR / f"{scene.key}.mp4", scene.frames, scene.motion
        )
        clips.append(clip)
        print(f"  {scene.key:10s} {scene.frames:4d}f  {scene.motion}")

    top_half = concat_clips(clips, WORK_DIR / "top_half.mp4")
    ass_path = build_vox_subtitles(WORK_DIR / "captions.ass")
    sfx = generate_vox_sfx_suite(WORK_DIR / "sfx")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    master = render_master(top_half, ass_path, sfx, OUTPUT_DIR / f"{SLUG}.mp4")
    print(f"MASTER {master}  {master.stat().st_size / 1_000_000:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

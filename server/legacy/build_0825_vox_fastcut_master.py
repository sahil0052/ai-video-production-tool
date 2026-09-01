"""
0825 Vox split-screen master, fast-cut recut.

Same source and same split-screen construction as
`build_0825_vox_splitscreen_master.py`, but the diorama stream is re-cut to
seventeen scenes of about three seconds each instead of six of about eight. Every
scene gets its own plate, its own substrate and its own camera move, so the top
half changes completely on a three-second cadence.

Three consequences of the shorter hold, all deliberate:

* Plates carry fewer elements. A viewer has three seconds and a moving camera; a
  plate with six cards and two stamps reads as clutter, so each one is built
  around a single hero with at most two supports.
* Substrates rotate. The panel generators all draw print furniture - rules,
  columns, traces - and seventeen of them in a row reads as one long page, so
  full-plate halftone photographs and bare poster stock are mixed in.
* The sound cues are pre-mixed into one bed rather than passed to ffmpeg as one
  input per cue. Sixteen cut accents plus seven semantic cues would otherwise
  mean twenty-three decoder inputs and a filter graph to match.

Scene lengths are declared in frames, split from the source's exact frame count,
so the seventeen clips sum to it with no floating-point drift.

Run:
    server/.venv/Scripts/python.exe server/build_0825_vox_fastcut_master.py
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_0825_vox_splitscreen_master as base  # noqa: E402
from build_0825_vox_splitscreen_master import (  # noqa: E402
    ASSET_DIR,
    FFMPEG,
    FPS,
    SOURCE_VIDEO,
    SR,
    TOP_H,
    TOP_W,
    build_vox_subtitles,
    clipping,
    concat_clips,
    finish,
    generate_vox_sfx_suite,
    load_cutouts,
    make_wav,
    measure_loudnorm,
    place_at,
    run,
    torn_strip,
)
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
    giant_number,
    halftone,
    ledger_panel,
    map_panel,
    newsprint_panel,
    pin_and_thread,
    place,
    stamp,
    ticker_tape,
)

W, H = CANVAS

WORKSPACE = Path(__file__).resolve().parent.parent
SLUG = "0825-vox-fastcut-master"
OUTPUT_DIR = WORKSPACE / "storage" / "deliverables" / SLUG
WORK_DIR = OUTPUT_DIR / "work"

# Measured off the source with cv2; asserted against the real file in main() so a
# different cut of the source fails loudly instead of drifting out of sync.
TOTAL_FRAMES = 1555


# ---------------------------------------------------------------------------
# scene plan
# ---------------------------------------------------------------------------


@dataclass
class Scene:
    key: str
    frames: int
    motion: str
    compose: str
    plate: Path | None = field(default=None, compare=False)


# (key, camera move, composer). Ordered against the transcript, so each plate is
# on screen while the line it illustrates is being spoken. No two neighbours share
# a camera move, and no two share a substrate except the pair of world plates -
# where one keys the real map and the other falls back to procedural landmasses.
PLAN: list[tuple[str, str, str]] = [
    ("c01_seconds", "push_in", "compose_seconds"),
    ("c02_who", "pan_right", "compose_who"),
    ("c03_two_sides", "pan_left", "compose_two_sides"),
    ("c04_bid_up", "push_in", "compose_bid_up"),
    ("c05_ask_side", "rise_up", "compose_ask_side"),
    ("c06_shop", "dive_down", "compose_shop"),
    ("c07_7050", "push_in", "compose_7050"),
    ("c08_plus50", "pan_left", "compose_plus50"),
    ("c09_world", "push_out", "compose_world"),
    ("c10_banks", "dive_down", "compose_banks"),
    ("c11_traders", "pan_right", "compose_traders"),
    ("c12_news", "push_in", "compose_news"),
    ("c13_balance", "pan_left", "compose_balance"),
    ("c14_suddenly", "dive_down", "compose_suddenly"),
    ("c15_ea", "push_in", "compose_ea"),
    ("c16_auto", "rise_up", "compose_auto"),
    ("c17_follow", "push_in", "compose_follow"),
]


def split_frames(total: int, parts: int) -> list[int]:
    """Split `total` frames into `parts` that sum to it exactly.

    Rounding cumulative edges rather than each part keeps the error from
    accumulating: the remainder lands as a one-frame difference spread across the
    run instead of a short or long tail clip.
    """
    edges = [round(total * i / parts) for i in range(parts + 1)]
    return [edges[i + 1] - edges[i] for i in range(parts)]


SCENES: list[Scene] = [
    Scene(key, frames, motion, compose)
    for (key, motion, compose), frames in zip(PLAN, split_frames(TOTAL_FRAMES, len(PLAN)))
]

assert sum(s.frames for s in SCENES) == TOTAL_FRAMES


# ---------------------------------------------------------------------------
# extra substrates
# ---------------------------------------------------------------------------


def photo_bed(name: str, seed: int, cell: int = 5, wash: float = 0.44) -> Image.Image:
    """A full-plate halftone photograph used as the substrate itself.

    The paper wash over the screen is not decoration - a raw halftone at this size
    fights any type laid on it, and knocking it back is what lets a giant number
    sit on top and still read.
    """
    photo = Image.open(ASSET_DIR / f"{name}.jpg").convert("RGB")
    pw, ph = photo.size
    scale = max(W / pw, H / ph)
    photo = photo.resize((max(1, int(pw * scale)), max(1, int(ph * scale))), Image.LANCZOS)
    left, top = (photo.width - W) // 2, (photo.height - H) // 2
    photo = photo.crop((left, top, left + W, top + H))

    flat = np.asarray(photo.convert("L"), dtype=np.float32) / 255.0
    lo, hi = np.percentile(flat, 2.0), np.percentile(flat, 98.0)
    if hi - lo > 0.04:
        flat = np.clip((flat - lo) / (hi - lo), 0.0, 1.0)

    # Same border test as `clipping`: halftone puts ink where the source is dark, so
    # a subject shot on black would print its background solid. Every bed currently
    # used keys light, but the test stays so swapping an asset cannot silently
    # invert the plate.
    edge = 10
    border = np.concatenate([
        flat[:edge].ravel(), flat[-edge:].ravel(),
        flat[:, :edge].ravel(), flat[:, -edge:].ravel(),
    ])
    if float(np.median(border)) < 0.28:
        flat = 1.0 - flat

    flat = np.clip(0.10 + (flat**0.70) * 0.88, 0.0, 1.0)
    graphic = Image.fromarray((flat * 255).astype(np.uint8), "L")

    plate = aged_paper((W, H), seed, "paper_light").convert("RGBA")
    plate.alpha_composite(halftone(graphic, cell=cell, angle=45.0, ink=PALETTE["ink"]))
    plate.alpha_composite(Image.new("RGBA", (W, H), (*PALETTE["paper_light"], int(255 * wash))))
    return plate


def stat_panel(seed: int, tone: str = "paper_light") -> Image.Image:
    """Bare poster stock: paper, a baseline grid, a ruled border, nothing else.

    Some beats are a single number. They land harder on an empty plate than fought
    against a chart or a ledger, and the plainness gives the seventeen-scene run a
    rest between the busier substrates.
    """
    img = aged_paper((W, H), seed, tone)
    d = ImageDraw.Draw(img)
    for i in range(1, 9):
        y = int(H * i / 9)
        d.line((int(W * 0.07), y, int(W * 0.93), y), fill=PALETTE["ink_faint"], width=1)
    d.rectangle(
        (int(W * 0.045), int(H * 0.045), int(W * 0.955), int(H * 0.955)),
        outline=PALETTE["ink_soft"],
        width=4,
    )
    return img


# ---------------------------------------------------------------------------
# scene composers - each returns a CANVAS-sized RGB plate
# ---------------------------------------------------------------------------


def compose_seconds() -> Image.Image:
    """0.00-3.03  GOLD moves in SECONDS."""
    plate = chart_panel((W, H), 1101, label="XAU/USD  SPOT GOLD").convert("RGBA")
    plate.alpha_composite(accent_strokes((W, H), 1102, count=3, thickness=26))
    place_at(plate, giant_number("SECONDS", 250, tint=PALETTE["accent_red"]), 0.50, 0.44, "near")
    place_at(plate, card((440, 240), "PRICE MOVES IN", "1s", seed=1103, accent=True),
             0.22, 0.76, "near", rotate=-2.5)
    place(plate, ticker_tape(W, 92, [
        ("XAU 3412.60", False), ("+18.40", False), ("XAU 3418.90", False),
        ("-6.20", True), ("XAU 3421.05", False),
    ], seed=1104), (0, int(H * 0.84)), "fg")
    return finish(plate, 1101)


def compose_who() -> Image.Image:
    """3.03-6.10  So who actually moves it?"""
    plate = photo_bed("goldbars_3", 1201, cell=5, wash=0.50)
    place_at(plate, giant_number("KAUN?", 310, tint=PALETTE["accent_red"]), 0.44, 0.40, "near")
    place_at(plate, stamp("WHO MOVES IT", 130), 0.54, 0.70, "fg", rotate=-7.0)
    return finish(plate, 1201)


def compose_two_sides() -> Image.Image:
    """6.10-9.13  BUYERS on one side, SELLERS on the other.

    One figure per side rather than two. Two cutouts at this size overlap into a
    single dark mass, which loses the whole point of the plate - that there are two
    opposed parties.
    """
    plate = ledger_panel((W, H), 1301, title="ORDER BOOK").convert("RGBA")
    place(plate, torn_strip((int(W * 0.46), H), 1302, "paper_light", "right"), (0, 0), "far")

    for cut in load_cutouts(["person_b_0"], int(H * 0.54)):
        place(plate, cut, (int(W * 0.09), int(H * 0.32)), "near", rotate=-2.0)
    for cut in load_cutouts(["person_c_2"], int(H * 0.54)):
        place(plate, cut, (int(W * 0.63), int(H * 0.32)), "near", rotate=2.0)

    place_at(plate, giant_number("BUYERS", 150), 0.25, 0.17, "near")
    place_at(plate, giant_number("SELLERS", 150, tint=PALETTE["accent_red"]), 0.72, 0.17, "near")
    return finish(plate, 1301)


def compose_bid_up() -> Image.Image:
    """9.13-12.20  Buyers become willing to pay more."""
    plate = stat_panel(1401).convert("RGBA")
    plate.alpha_composite(accent_strokes((W, H), 1402, count=4, thickness=30))
    place_at(plate, giant_number("BID UP", 300, tint=PALETTE["accent_red"]), 0.50, 0.38, "near")
    place_at(plate, card((520, 250), "BUYERS PAY", "MORE", seed=1403, accent=True),
             0.50, 0.74, "near", rotate=-2.0)
    return finish(plate, 1401)


def compose_ask_side() -> Image.Image:
    """12.20-15.23  Sellers move their asking price, so the market moves."""
    plate = ledger_panel((W, H), 1501, title="ASK SIDE").convert("RGBA")
    place(plate, torn_strip((W, int(H * 0.22)), 1502, "paper_mid", "bottom"), (0, 0), "far")

    # Two picks failed here before this one. person_c_0 keys to nothing at all - pure
    # white background, and the subject's shirt goes with it. person_b_2 is shot on
    # flat pink, which keys away and takes his face and shirt with it, leaving a
    # hollow outline. person_b_1 is on light grey with tonal separation at the collar,
    # which is what the keyer actually needs.
    for cut in load_cutouts(["person_b_1"], int(H * 0.52)):
        place(plate, cut, (int(W * 0.08), int(H * 0.34)), "near", rotate=-2.0)

    place_at(plate, giant_number("ASK", 320), 0.62, 0.34, "near")
    place_at(plate, card((460, 230), "SELLER MOVES", "PRICE", seed=1503, accent=True),
             0.66, 0.72, "near", rotate=2.5)
    return finish(plate, 1501)


def compose_shop() -> Image.Image:
    """15.23-18.30  One shop, one counter, one 7,000 offer."""
    plate = blueprint_panel((W, H), 1601, label="GOLD SHOP / COUNTER PLAN").convert("RGBA")
    place_at(plate, clipping(ASSET_DIR / "goldcoins_1.jpg", (700, 520), cell=4, seed=1602),
             0.28, 0.36, "mid", rotate=-2.5)
    place_at(plate, card((440, 250), "BUYER OFFERS", "7,000", seed=1603), 0.74, 0.32, "near",
             rotate=2.0)
    place_at(plate, stamp("ONE COUNTER", 120), 0.48, 0.78, "fg", rotate=-6.0)
    return finish(plate, 1601)


def compose_7050() -> Image.Image:
    """18.30-21.37  Then buyers start offering 7,050."""
    plate = photo_bed("goldcoins_0", 1701, cell=4, wash=0.34)
    place_at(plate, giant_number("7,050", 300, tint=PALETTE["accent_red"]), 0.50, 0.38, "near")
    place_at(plate, card((480, 230), "BUYERS NOW", "OFFER", seed=1702, accent=True),
             0.50, 0.74, "near", rotate=2.0)
    return finish(plate, 1701)


def compose_plus50() -> Image.Image:
    """21.37-24.40  So the seller raises the asking price."""
    plate = stat_panel(1801, tone="paper_mid").convert("RGBA")
    place(plate, torn_strip((W, int(H * 0.20)), 1802, "cream", "top"), (0, int(H * 0.80)), "far")
    place_at(plate, giant_number("+50", 330, tint=PALETTE["accent_red"]), 0.36, 0.40, "near")
    place_at(plate, card((470, 230), "ASKING PRICE", "UP", seed=1803, accent=True),
             0.74, 0.42, "near", rotate=3.0)
    place_at(plate, stamp("DEAL", 160), 0.50, 0.78, "fg", rotate=-8.0)
    return finish(plate, 1801)


def compose_world() -> Image.Image:
    """24.40-27.47  Not one shop - the whole world, at once."""
    plate = map_panel((W, H), 1901, map_source=ASSET_DIR / "worldmap_3.jpg").convert("RGBA")
    place_at(plate, giant_number("24/7", 300, color=PALETTE["cream"], tint=PALETTE["accent_red"]),
             0.50, 0.40, "near")
    # stamp() boxes the text, so a long word is wide regardless of height: at 100 this
    # still spanned the full plate and both ends were lost to the camera crop. Smaller
    # and dropped below the continents, where it prints on light paper instead of over
    # the dark stippled landmass.
    place_at(plate, stamp("SIMULTANEOUS", 80), 0.50, 0.82, "fg", rotate=-5.0)
    return finish(plate, 1901)


def compose_banks() -> Image.Image:
    """27.47-30.50  Banks and institutions, wired together."""
    # This started as a second map_panel with no map_source, on the theory that the
    # procedural fallback would look different enough from the keyed plate to carry
    # two world beats in a row. It does not - the fallback draws six blurred polygons
    # that read as random blobs, not continents. A blueprint carries a participant
    # network better anyway, and it keeps the one good world map to a single scene.
    plate = blueprint_panel((W, H), 2001, label="GLOBAL MARKET / PARTICIPANTS").convert("RGBA")
    cw, ch = 480, 200
    boxes = [(int(W * 0.07), int(H * 0.22)), (int(W * 0.52), int(H * 0.58))]
    pin_and_thread(plate, [
        (boxes[0][0] + cw, boxes[0][1] + ch),
        (int(W * 0.50), int(H * 0.45)),
        (boxes[1][0], boxes[1][1]),
    ])
    place(plate, card((cw, ch), "BANKS", seed=2002, accent=True), boxes[0], "near", rotate=-3.0)
    place(plate, card((cw, ch), "INSTITUTIONS", seed=2003), boxes[1], "near", rotate=2.5)
    place_at(plate, stamp("BUY / SELL", 105), 0.74, 0.20, "fg", rotate=6.0)
    return finish(plate, 2001)


def compose_traders() -> Image.Image:
    """30.50-33.57  Traders and investors, buying and selling continuously.

    Figures sized to read at a glance and labelled directly beneath, rather than
    small in the middle with the cards stranded along the bottom edge.
    """
    plate = ledger_panel((W, H), 2101, title="ORDER FLOW").convert("RGBA")
    plate.alpha_composite(accent_strokes((W, H), 2102, count=3, thickness=24))

    for i, cut in enumerate(load_cutouts(["person_c_1", "person_b_3"], int(H * 0.50))):
        place(plate, cut, (int(W * (0.11 + 0.48 * i)), int(H * 0.16)), "near",
              rotate=-2.5 + 5.0 * i)

    place_at(plate, card((430, 170), "TRADERS", seed=2103, accent=True), 0.24, 0.80, "near",
             rotate=-3.0)
    place_at(plate, card((430, 170), "INVESTORS", seed=2104), 0.74, 0.80, "near", rotate=3.0)
    return finish(plate, 2101)


def compose_news() -> Image.Image:
    """33.57-36.63  Then important economic news lands."""
    # Headline kept short: newsprint_panel sets it at 7.5% of plate height with no
    # wrapping, so a longer string runs off the right edge.
    plate = newsprint_panel((W, H), 2201, headline="ECONOMIC DATA HITS", columns=4).convert("RGBA")
    place_at(plate, clipping(ASSET_DIR / "newspaper_1.jpg", (680, 500), cell=4, seed=2202),
             0.74, 0.34, "mid", rotate=3.0)
    place_at(plate, giant_number("NEWS", 280, tint=PALETTE["accent_red"]), 0.26, 0.46, "fg")
    place_at(plate, stamp("BREAKING", 145), 0.44, 0.80, "fg", rotate=-7.0)
    return finish(plate, 2201)


def compose_balance() -> Image.Image:
    """36.63-39.70  The balance between the two sides flips in seconds."""
    # cell 4, not 5: the source is a page of fine gothic type and a coarser screen
    # turns it into grey mush. alert_wash is left off here - stacked on a warm photo
    # bed it tints the whole plate salmon, which reads as a colour error next to the
    # cream and tan of every other scene.
    plate = photo_bed("newspaper_3", 2301, cell=4, wash=0.38)
    place_at(plate, giant_number("BALANCE", 230, tint=PALETTE["accent_red"]), 0.50, 0.36, "near")
    place_at(plate, card((420, 220), "FLIPS IN", "2s", seed=2302, accent=True), 0.28, 0.72,
             "near", rotate=-2.5)
    place_at(plate, stamp("SHIFT", 150), 0.74, 0.74, "fg", rotate=6.0)
    return finish(plate, 2301)


def compose_suddenly() -> Image.Image:
    """39.70-42.77  Which is why gold can move suddenly."""
    plate = chart_panel((W, H), 2401, label="XAU/USD  SPIKE").convert("RGBA")
    plate.alpha_composite(accent_strokes((W, H), 2402, count=5, thickness=32))
    place_at(plate, giant_number("SUDDENLY", 215, tint=PALETTE["accent_red"]), 0.50, 0.40, "near")
    place_at(plate, card((460, 230), "GOLD PRICE", "MOVES", seed=2403, accent=True),
             0.50, 0.76, "near", rotate=2.0)
    # Barely any: alert_wash is a strong red tint and even a tenth of it turned this
    # plate salmon, which reads as a colour error beside the cream and tan of the
    # other sixteen. This much only warms the paper.
    plate.alpha_composite(alert_wash((W, H), strength=0.05))
    return finish(plate, 2401)


def compose_ea() -> Image.Image:
    """42.77-45.83  An EA monitors pre-defined rules."""
    plate = circuit_panel((W, H), 2501).convert("RGBA")
    place_at(plate, giant_number("EA", 320, tint=PALETTE["accent_red"]), 0.20, 0.30, "near")
    place_at(plate, card((470, 210), "RULE 01", "MONITOR", seed=2502), 0.72, 0.26, "near",
             rotate=-2.5)
    place_at(plate, card((470, 210), "RULE 02", "TRIGGER", seed=2503, accent=True), 0.72, 0.62,
             "near", rotate=2.5)
    return finish(plate, 2501)


def compose_auto() -> Image.Image:
    """45.83-48.90  And acts automatically when they are met."""
    plate = blueprint_panel((W, H), 2601, label="AUTO EXECUTION / LOGIC").convert("RGBA")
    place_at(plate, giant_number("AUTO", 300, tint=PALETTE["accent_red"]), 0.36, 0.38, "near")
    place_at(plate, card((450, 220), "ACTS", "ALONE", seed=2603, accent=True), 0.74, 0.44,
             "near", rotate=3.0)
    place_at(plate, stamp("EXECUTE", 150), 0.48, 0.78, "fg", rotate=-7.0)
    return finish(plate, 2601)


def compose_follow() -> Image.Image:
    """48.90-51.83  Forex, gold and EA in simple language - follow."""
    plate = circuit_panel((W, H), 2701).convert("RGBA")
    place(plate, torn_strip((W, int(H * 0.24)), 2702, "cream", "top"), (0, int(H * 0.76)), "far")
    place_at(plate, stamp("FOLLOW", 205), 0.48, 0.42, "fg", rotate=-7.0)
    place(plate, ticker_tape(W, 92, [
        ("FOREX", False), ("GOLD", False), ("EA", True), ("SIMPLE LANGUAGE", False),
    ], seed=2703), (0, int(H * 0.82)), "fg")
    return finish(plate, 2701)


COMPOSERS = {name: obj for name, obj in list(globals().items()) if name.startswith("compose_")}


# ---------------------------------------------------------------------------
# camera motion
# ---------------------------------------------------------------------------


def camera_window(motion: str, ease: float) -> tuple[float, float, float]:
    """Crop scale and centre for one frame of a named move.

    Six moves rather than three: with seventeen cuts, reusing three would put the
    same move back on screen every ninth second, which reads as a loop.
    """
    if motion == "push_in":
        return 1.0 + 0.15 * ease, 0.5, 0.5
    if motion == "push_out":
        return 1.15 - 0.15 * ease, 0.5, 0.5
    if motion == "pan_left":
        return 1.08, 0.20 + 0.60 * ease, 0.5
    if motion == "pan_right":
        return 1.08, 0.80 - 0.60 * ease, 0.5
    if motion == "dive_down":
        return 1.10, 0.5, 0.15 + 0.70 * ease
    if motion == "rise_up":
        return 1.10, 0.5, 0.85 - 0.70 * ease
    return 1.0, 0.5, 0.5


def create_motion_clip(image_path: Path, out_path: Path, frames: int, motion: str) -> Path:
    """Render one committed camera move over a still, as a TOP_W x TOP_H clip."""
    plate = cv2.imread(str(image_path))
    if plate is None:
        raise RuntimeError(f"cannot read plate: {image_path}")
    ph, pw = plate.shape[:2]

    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (TOP_W, TOP_H))
    if not writer.isOpened():
        raise RuntimeError(f"cannot open writer: {out_path}")

    for i in range(frames):
        prog = i / max(1, frames - 1)
        ease = prog * prog * (3.0 - 2.0 * prog)
        scale, fx, fy = camera_window(motion, ease)
        cw, ch = int(pw / scale), int(ph / scale)
        x, y = int((pw - cw) * fx), int((ph - ch) * fy)
        crop = plate[y : y + ch, x : x + cw]
        writer.write(cv2.resize(crop, (TOP_W, TOP_H), interpolation=cv2.INTER_LANCZOS4))

    writer.release()
    return out_path


# ---------------------------------------------------------------------------
# sound bed
# ---------------------------------------------------------------------------

# Cues tied to meaning rather than to the cut grid: (cue, ms, gain).
SEMANTIC_CUES: list[tuple[str, int, float]] = [
    ("riser", 0, 0.50),
    ("tick", 2400, 0.60),
    ("stamp_thud", 6980, 0.70),
    ("tick", 19440, 0.70),
    ("paper_whoosh", 23900, 0.60),
    ("alert_drop", 32920, 0.80),
    ("riser", 42770, 0.50),
    ("chime", 48900, 0.70),
]


def build_sfx_bed(cues: dict[str, Path], out_path: Path) -> Path:
    """Sum every cue into one mono bed the length of the programme.

    Seventeen cuts want an accent on each one, and passing twenty-three cues to
    ffmpeg as twenty-three inputs means twenty-three decoders and an `adelay` per
    cue. Summing them here is one input and one `volume`, and it makes collision
    handling trivial: a cut accent within 150ms of a semantic cue is dropped rather
    than stacked on top of it, which would just read as a thump.
    """
    total = int(SR * TOTAL_FRAMES / FPS) + SR
    bed = np.zeros(total, dtype=np.float32)

    def add(name: str, at_ms: int, gain: float) -> None:
        data = np.frombuffer(
            Path(cues[name]).read_bytes()[44:], dtype=np.int16
        ).astype(np.float32) / 32768.0
        start = int(SR * at_ms / 1000)
        end = min(total, start + data.size)
        if end > start:
            bed[start:end] += data[: end - start] * gain

    semantic_ms = [ms for _, ms, _ in SEMANTIC_CUES]
    for name, at_ms, gain in SEMANTIC_CUES:
        add(name, at_ms, gain)

    # One quiet accent per cut. Alternating whoosh and pop keeps sixteen of them from
    # turning into a metronome, and the low gains keep them under the dialogue.
    frame = 0
    for i, scene in enumerate(SCENES):
        if i:
            at_ms = int(1000 * frame / FPS)
            if all(abs(at_ms - s) > 150 for s in semantic_ms):
                add("paper_whoosh" if i % 2 else "paper_pop", at_ms, 0.34 if i % 2 else 0.30)
        frame += scene.frames

    peak = float(np.abs(bed).max())
    if peak > 0.95:
        bed *= 0.95 / peak
    return make_wav(out_path, bed)


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------


def render_master(top_half: Path, ass_path: Path, sfx_bed: Path, out_path: Path) -> Path:
    ass_filter_path = str(ass_path).replace("\\", "/").replace(":", "\\:")
    inputs = [FFMPEG, "-y", "-i", str(SOURCE_VIDEO), "-i", str(top_half), "-i", str(sfx_bed)]

    video_chains = [
        f"[1:v]scale={TOP_W}:{TOP_H},fps={FPS}[v_top]",
        f"[0:v]scale=1080:1920,crop=1080:960:0:380,fps={FPS}[v_bottom]",
        "[v_top][v_bottom]vstack=inputs=2[v_split]",
        "[v_split]drawbox=x=0:y=956:w=1080:h=8:color=#1A1A1A@1.0:t=fill[v_divided]",
        "[v_divided]eq=contrast=1.08:brightness=0.01:saturation=1.12[v_graded]",
        f"[v_graded]ass='{ass_filter_path}'[v_out]",
    ]
    # normalize=0 so the bed's own gain staging survives; amix would otherwise halve
    # both inputs and leave the final level to chance.
    audio_chains = [
        "[2:a]volume=1.0[a_bed]",
        "[0:a][a_bed]amix=inputs=2:duration=first:normalize=0:dropout_transition=2[a_mixed]",
    ]

    m = measure_loudnorm(inputs, audio_chains)
    print(f"  measured  I={m['input_i']} LUFS  TP={m['input_tp']} dBTP  LRA={m['input_lra']}")
    # The presenter audio arrives clipped at about +1.4 dBTP, so linear make-up gain
    # lands over 0 dBFS and loudnorm's TP option - a soft ceiling - cannot hold it.
    # `level=false` matters: alimiter auto-levels to its ceiling by default, which
    # would undo the loudness target. The ceiling sits below -1.0 dBFS to leave room
    # for AAC reconstruction overshoot, which reads as true peak but not sample peak.
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

    cap = cv2.VideoCapture(str(SOURCE_VIDEO))
    actual = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    if actual != TOTAL_FRAMES:
        print(f"source is {actual} frames, plan assumes {TOTAL_FRAMES} - update TOTAL_FRAMES")
        return 1

    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    plates_dir = WORK_DIR / "plates"
    plates_dir.mkdir(parents=True, exist_ok=True)

    print(f"scenes: {len(SCENES)}  frames: {TOTAL_FRAMES}  ({TOTAL_FRAMES / FPS:.2f}s @ {FPS}fps)")

    clips: list[Path] = []
    for scene in SCENES:
        plate_path = plates_dir / f"{scene.key}.png"
        COMPOSERS[scene.compose]().save(plate_path)
        scene.plate = plate_path
        clips.append(create_motion_clip(
            plate_path, WORK_DIR / f"{scene.key}.mp4", scene.frames, scene.motion
        ))
        print(f"  {scene.key:14s} {scene.frames:3d}f  {scene.frames / FPS:4.2f}s  {scene.motion}")

    base.WORK_DIR = WORK_DIR  # concat_clips writes its listing beside the clips
    top_half = concat_clips(clips, WORK_DIR / "top_half.mp4")
    ass_path = build_vox_subtitles(WORK_DIR / "captions.ass")
    sfx_bed = build_sfx_bed(generate_vox_sfx_suite(WORK_DIR / "sfx"), WORK_DIR / "sfx_bed.wav")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    master = render_master(top_half, ass_path, sfx_bed, OUTPUT_DIR / f"{SLUG}.mp4")
    print(f"MASTER {master}  {master.stat().st_size / 1_000_000:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

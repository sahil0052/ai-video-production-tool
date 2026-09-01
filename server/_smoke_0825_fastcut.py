"""Compose the seventeen fast-cut plates and write review-sized previews.

Scratch harness only - it exists so all seventeen plates can be eyeballed for
clipped elements, illegible clippings and inverted halftones before paying for the
clip and encode pass. Deletes its own stale output first so a plate that fails to
compose cannot leave a previous run's PNG behind looking like a pass.

Also writes contact sheets, since seventeen plates are easier to judge for variety
side by side than one at a time - repeated substrates and repeated layouts only
show up in comparison.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image

import build_0825_vox_fastcut_master as B

OUT = Path(__file__).resolve().parent.parent / "storage" / "_vox_smoke" / "fastcut"
TILE = (405, 360)
COLS = 3


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("*.png"):
        stale.unlink()

    tiles: list[tuple[str, Image.Image]] = []
    for scene in B.SCENES:
        t0 = time.time()
        plate = B.COMPOSERS[scene.compose]()
        plate.save(OUT / f"{scene.key}.png")
        plate.resize((540, 480), Image.LANCZOS).save(OUT / f"{scene.key}_sm.png")
        tiles.append((scene.key, plate.resize(TILE, Image.LANCZOS).convert("RGB")))
        print(f"{scene.key:14s} {scene.frames:3d}f {scene.motion:9s} {time.time() - t0:5.1f}s")

    for page in range((len(tiles) + 8) // 9):
        chunk = tiles[page * 9 : page * 9 + 9]
        rows = (len(chunk) + COLS - 1) // COLS
        sheet = Image.new("RGB", (TILE[0] * COLS, TILE[1] * rows), (30, 28, 25))
        for i, (_, tile) in enumerate(chunk):
            sheet.paste(tile, ((i % COLS) * TILE[0], (i // COLS) * TILE[1]))
        sheet.save(OUT / f"_sheet{page + 1}.png")
        print(f"sheet{page + 1}: {', '.join(k for k, _ in chunk)}")


if __name__ == "__main__":
    main()

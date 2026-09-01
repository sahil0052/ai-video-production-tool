"""Compare halftone cell sizes for the three photo clippings.

The product shots print as noise at cell=9. This renders each source at several
cell sizes plus the raw tonal stage, so the failure can be attributed to dot
coarseness or to the tonal/inversion step rather than guessed at.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from PIL import Image

import build_0825_vox_splitscreen_master as B

OUT = Path(__file__).resolve().parent.parent / "storage" / "_vox_smoke" / "clip_test"
NAMES = ["goldbars_1.jpg", "goldcoins_2.jpg", "newspaper_0.jpg"]
CELLS = [3, 4, 6, 9]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("*.png"):
        stale.unlink()

    for name in NAMES:
        src = B.ASSET_DIR / name
        photo = Image.open(src).convert("L")
        arr = np.asarray(photo, dtype=np.float32) / 255.0
        print(f"{name:16s} size={photo.size} median={np.median(arr):.3f} "
              f"mean={arr.mean():.3f} p2={np.percentile(arr, 2):.3f} "
              f"p98={np.percentile(arr, 98):.3f}  -> invert={np.median(arr) < 0.45}")

        strip = Image.new("RGB", (620 * len(CELLS), 460), (240, 236, 224))
        for i, cell in enumerate(CELLS):
            clip = B.clipping(src, (600, 440), cell=cell, seed=7)
            strip.paste(clip.convert("RGB"), (620 * i + 10, 10), clip.split()[3])
        strip.save(OUT / f"{Path(name).stem}_cells.png")
        strip.resize((strip.width // 2, strip.height // 2), Image.LANCZOS).save(
            OUT / f"{Path(name).stem}_cells_sm.png"
        )


if __name__ == "__main__":
    main()

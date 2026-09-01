"""Compose the six 0825 diorama plates and write review-sized previews.

Scratch harness only - it exists so plates can be eyeballed without paying for
the full clip/encode pass. Deletes its own stale output first so a plate that
fails to compose cannot leave a previous run's PNG behind looking like a pass.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image

import build_0825_vox_splitscreen_master as B

OUT = Path(__file__).resolve().parent.parent / "storage" / "_vox_smoke" / "plates"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob("*.png"):
        stale.unlink()

    for scene in B.SCENES:
        t0 = time.time()
        plate = getattr(B, scene.compose)()
        plate.save(OUT / f"{scene.key}.png")
        plate.resize((540, 480), Image.LANCZOS).save(OUT / f"{scene.key}_sm.png")
        print(f"{scene.key:10s} {plate.size} {time.time() - t0:5.1f}s")


if __name__ == "__main__":
    main()

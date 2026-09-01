from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path

from build_0813_backtest_v8 import build_blueprint as build_backtest
from build_0813_lotsize_v8 import build_blueprint as build_lot_size
from build_0813_ppi_v8 import build_blueprint as build_ppi
from build_0813_v8_pipeline import build_story, render_story


WORKSPACE = Path(__file__).resolve().parent.parent
OUTPUT_ROOT = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0813-all-three-v9-training-match"
)


def blueprints():
    return tuple(
        replace(blueprint, output_dir=OUTPUT_ROOT / blueprint.story_id)
        for blueprint in (
            build_ppi(),
            build_backtest(),
            build_lot_size(),
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "stage",
        choices=("plan", "render", "all"),
        nargs="?",
        default="all",
    )
    arguments = parser.parse_args()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    results = []
    for blueprint in blueprints():
        if arguments.stage in {"plan", "all"}:
            build_story(blueprint)
        if arguments.stage in {"render", "all"}:
            output = render_story(blueprint)
            results.append(
                {
                    "story_id": blueprint.story_id,
                    "output": str(output),
                }
            )
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

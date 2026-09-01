from __future__ import annotations

import argparse
from pathlib import Path
import sys

from build_0813_v8_pipeline import load_blueprint, render_story


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--story",
        choices=["ppi", "backtest", "lot-size", "all"],
        default="all",
    )
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    story = build_parser().parse_args().story
    stories = (
        ["ppi", "backtest", "lot-size"]
        if story == "all"
        else [story]
    )
    for story_id in stories:
        blueprint = load_blueprint(story_id)
        output = render_story(blueprint)
        print(f"{story_id}: {Path(output)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

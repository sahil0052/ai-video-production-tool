from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a bespoke reference-style production edit for a new "
            "talking-head tech or trading story."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("plan", "run"):
        action = subparsers.add_parser(command)
        action.add_argument("source", type=Path)
        action.add_argument("output_dir", type=Path)
        action.add_argument(
            "--style-reference",
            type=Path,
            default=Path(
                r"D:\Downloads\Trading_Reel 02(06-08-26).mp4"
            ),
        )
        action.add_argument(
            "--brand-logo",
            type=Path,
            default=Path(
                r"D:\Downloads\JEPG Profit Bricks Logo-01.jpg (1).jpeg"
            ),
        )
    assemble = subparsers.add_parser("assemble")
    assemble.add_argument("output_dir", type=Path)
    remaster = subparsers.add_parser("remaster")
    remaster.add_argument("output_dir", type=Path)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    arguments = build_parser().parse_args()
    from app.editor.reference_story import (
        assemble_reference_story,
        build_reference_story_blueprint,
        remaster_reference_story,
    )

    if arguments.command == "plan":
        result = build_reference_story_blueprint(
            source=arguments.source,
            output_dir=arguments.output_dir,
            style_reference=arguments.style_reference,
            brand_logo=arguments.brand_logo,
        )
    elif arguments.command == "assemble":
        result = assemble_reference_story(
            output_dir=arguments.output_dir,
        )
    elif arguments.command == "remaster":
        result = remaster_reference_story(
            output_dir=arguments.output_dir,
        )
    else:
        build_reference_story_blueprint(
            source=arguments.source,
            output_dir=arguments.output_dir,
            style_reference=arguments.style_reference,
            brand_logo=arguments.brand_logo,
        )
        result = assemble_reference_story(
            output_dir=arguments.output_dir,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build and render the 0810 internet-sourced reference edit."
        )
    )
    commands = parser.add_subparsers(dest="command", required=True)

    plan = commands.add_parser("plan")
    plan.add_argument("source", type=Path)
    plan.add_argument("output_dir", type=Path)
    plan.add_argument("--style-reference", type=Path, default=None)
    plan.add_argument("--brand-logo", type=Path, default=None)
    plan.add_argument("--force", action="store_true")

    assemble = commands.add_parser("assemble")
    assemble.add_argument("output_dir", type=Path)

    approve = commands.add_parser("approve")
    approve.add_argument("output_dir", type=Path)
    approve.add_argument("--reviewer", required=True)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    arguments = build_parser().parse_args()
    if arguments.command == "plan":
        from app.editor.internet_story_0810 import build_0810_blueprint

        result = build_0810_blueprint(
            source=arguments.source,
            output_dir=arguments.output_dir,
            style_reference=arguments.style_reference,
            brand_logo=arguments.brand_logo,
            force=arguments.force,
        )
    elif arguments.command == "assemble":
        from app.editor.internet_story_0810 import assemble_0810_story

        result = assemble_0810_story(output_dir=arguments.output_dir)
    else:
        from app.editor.production_v4 import approve_production_edit

        result = approve_production_edit(
            output_dir=arguments.output_dir,
            reviewer=arguments.reviewer,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

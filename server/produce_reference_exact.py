from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan and assemble the 0806 V5 edit against one supplied "
            "user reference."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("plan", "run"):
        action = subparsers.add_parser(command)
        action.add_argument("source", type=Path)
        action.add_argument("reference", type=Path)
        action.add_argument("output_dir", type=Path)

    assemble = subparsers.add_parser("assemble")
    assemble.add_argument("output_dir", type=Path)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    arguments = build_parser().parse_args()

    from app.editor.reference_exact import (
        assemble_exact_reference,
        build_exact_reference_blueprint,
    )

    if arguments.command == "plan":
        result = build_exact_reference_blueprint(
            source=arguments.source,
            reference=arguments.reference,
            output_dir=arguments.output_dir,
        )
    elif arguments.command == "assemble":
        result = assemble_exact_reference(
            output_dir=arguments.output_dir,
        )
    else:
        build_exact_reference_blueprint(
            source=arguments.source,
            reference=arguments.reference,
            output_dir=arguments.output_dir,
        )
        result = assemble_exact_reference(
            output_dir=arguments.output_dir,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

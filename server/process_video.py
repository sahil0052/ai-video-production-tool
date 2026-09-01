import argparse
import os
from pathlib import Path
import sys

from app.editor.pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Process one vertical MP4 through the training-derived Cutline "
            "tech-story editing pipeline."
        )
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--profile",
        choices=["tech-story-v1"],
        default="tech-story-v1",
    )
    parser.add_argument(
        "--assets",
        default="auto",
        help="Use 'auto', 'off', or a local licensed asset-library path.",
    )
    parser.add_argument(
        "--internet-assets",
        choices=["auto", "off", "required"],
        default="auto",
        help=(
            "Use licensed internet media when available, disable it, or "
            "require at least one downloaded asset."
        ),
    )
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    arguments = build_parser().parse_args()
    if arguments.assets == "off":
        os.environ["VIDEO_EDITOR_ASSET_LIBRARY"] = str(
            arguments.output.parent / ".cutline-no-assets"
        )
    elif arguments.assets != "auto":
        os.environ["VIDEO_EDITOR_ASSET_LIBRARY"] = str(
            Path(arguments.assets).expanduser().resolve()
        )
    os.environ["VIDEO_EDITOR_INTERNET_ASSETS"] = arguments.internet_assets

    work_dir = arguments.output.parent
    result = run_pipeline(
        source=arguments.source.resolve(),
        output=arguments.output.resolve(),
        work_dir=work_dir.resolve(),
        progress=lambda stage, percent: print(
            f"{percent:3d}% {stage}", flush=True
        ),
    )
    print(result.model_dump_json(indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

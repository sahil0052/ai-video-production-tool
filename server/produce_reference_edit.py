import argparse
import json
from pathlib import Path
import sys

from app.editor.reference_production import produce_reference_edit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build a bespoke, evidence-first reference-matched production "
            "edit from one portrait talking-head MP4."
        )
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--primary-reference",
        type=int,
        required=True,
        choices=range(1, 15),
    )
    parser.add_argument(
        "--secondary-reference",
        type=int,
        required=True,
        choices=range(1, 15),
    )
    parser.add_argument(
        "--asset-policy",
        choices=["maximum-match", "free-licensed"],
        default="maximum-match",
    )
    parser.add_argument(
        "--quality-target",
        choices=["reference-standard", "reference-max"],
        default="reference-standard",
    )
    parser.add_argument(
        "--capture-profile",
        choices=["none", "local-metatrader"],
        default="none",
    )
    parser.add_argument(
        "--voice-policy",
        choices=["retime-safe", "preserve-verbatim"],
        default="retime-safe",
    )
    parser.add_argument(
        "--visual-revision",
        choices=["v2", "v3", "v4"],
        default="v4",
    )
    parser.add_argument(
        "--time-budget-min",
        type=int,
        default=30,
    )
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    arguments = build_parser().parse_args()
    if arguments.visual_revision == "v4":
        from app.editor.production_v4 import plan_production_edit

        result = plan_production_edit(
            source=arguments.source,
            output_dir=arguments.output_dir,
            primary_reference=arguments.primary_reference,
            secondary_reference=arguments.secondary_reference,
            asset_policy=arguments.asset_policy,
            quality_target=arguments.quality_target,
            capture_profile=arguments.capture_profile,
            voice_policy=arguments.voice_policy,
            flow_operation_budget=3,
        )
    else:
        result = produce_reference_edit(
            source=arguments.source,
            output_dir=arguments.output_dir,
            primary_reference=arguments.primary_reference,
            secondary_reference=arguments.secondary_reference,
            asset_policy=arguments.asset_policy,
            time_budget_min=arguments.time_budget_min,
            quality_target=arguments.quality_target,
            capture_profile=arguments.capture_profile,
            voice_policy=arguments.voice_policy,
            visual_revision=arguments.visual_revision,
            progress=lambda stage, percent: print(
                f"{percent:3d}% {stage}",
                flush=True,
            ),
        )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

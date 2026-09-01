from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan, generate, review, assemble and approve a staged "
            "Flow-assisted production video edit."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan")
    plan.add_argument("source", type=Path)
    plan.add_argument("output_dir", type=Path)
    plan.add_argument(
        "--primary-reference",
        type=int,
        choices=range(1, 15),
        default=10,
    )
    plan.add_argument(
        "--secondary-reference",
        type=int,
        choices=range(1, 15),
        default=4,
    )
    plan.add_argument(
        "--asset-policy",
        choices=[
            "free-licensed",
            "maximum-match",
            "evidence-first-free",
        ],
        default="free-licensed",
    )
    plan.add_argument(
        "--quality-target",
        choices=["reference-standard", "reference-max"],
        default="reference-max",
    )
    plan.add_argument(
        "--capture-profile",
        choices=["none", "local-metatrader"],
        default="local-metatrader",
    )
    plan.add_argument(
        "--voice-policy",
        choices=[
            "retime-safe",
            "preserve-verbatim",
            "reference-compressed",
            "natural-1x",
        ],
        default="preserve-verbatim",
    )
    plan.add_argument("--style-reference", type=Path, default=None)
    plan.add_argument(
        "--reference-profile",
        choices=["technical-reference", "social-kinetic"],
        default="technical-reference",
    )
    plan.add_argument(
        "--story-profile",
        choices=[
            "auto",
            "automation-future",
            "rofx-case",
            "cpi-inflation",
            "ppi-training-v8",
            "backtest-training-v8",
            "lot-size-training-v8",
        ],
        default="auto",
    )
    plan.add_argument(
        "--flow-operation-budget",
        type=int,
        choices=range(0, 9),
        default=3,
    )
    plan.add_argument(
        "--flow-repository",
        type=Path,
        default=None,
    )
    plan.add_argument(
        "--flow-profile",
        default="sahilsharmabybit2",
    )

    generate = subparsers.add_parser("generate")
    generate.add_argument("output_dir", type=Path)
    generate.add_argument(
        "--approve-paid-ops",
        type=int,
        choices=range(1, 9),
        required=True,
    )

    assemble = subparsers.add_parser("assemble")
    assemble.add_argument("output_dir", type=Path)

    review = subparsers.add_parser("review")
    review.add_argument("output_dir", type=Path)

    approve = subparsers.add_parser("approve")
    approve.add_argument("output_dir", type=Path)
    approve.add_argument("--reviewer", required=True)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    arguments = build_parser().parse_args()

    is_v8_plan = (
        arguments.command == "plan"
        and arguments.story_profile.endswith("-training-v8")
    )
    if is_v8_plan:
        from build_0813_v8_pipeline import plan_story_cli

        result = plan_story_cli(
            source=arguments.source,
            output_dir=arguments.output_dir,
            story_profile=arguments.story_profile,
        )
    elif arguments.command == "assemble" and (
        arguments.output_dir / "production-job.json"
    ).is_file():
        record = json.loads(
            (arguments.output_dir / "production-job.json").read_text(
                encoding="utf-8"
            )
        )
        if record.get("story_id") in {"ppi", "backtest", "lot-size"}:
            from build_0813_v8_pipeline import assemble_story_cli

            result = assemble_story_cli(arguments.output_dir)
        else:
            from app.editor.production_v4 import assemble_production_edit

            result = assemble_production_edit(
                output_dir=arguments.output_dir,
            )
    elif arguments.command == "review":
        from review_0813_v8 import audit_story, evaluate_story, review_output

        if (arguments.output_dir / "edit-plan.json").is_file():
            job = json.loads(
                (arguments.output_dir / "production-job.json").read_text(
                    encoding="utf-8"
                )
            )
            metrics = audit_story(
                arguments.output_dir.resolve(),
                str(job["story_id"]),
            )
            result = evaluate_story(
                story_id=str(job["story_id"]),
                metrics=metrics,
            )
        else:
            result = review_output(arguments.output_dir.resolve())
    else:
        from app.editor.production_v4 import (
            approve_production_edit,
            assemble_production_edit,
            generate_flow_candidates,
            plan_production_edit,
        )

        if arguments.command == "plan":
            result = plan_production_edit(
                source=arguments.source,
                output_dir=arguments.output_dir,
                primary_reference=arguments.primary_reference,
                secondary_reference=arguments.secondary_reference,
                asset_policy=arguments.asset_policy,
                quality_target=arguments.quality_target,
                capture_profile=arguments.capture_profile,
                voice_policy=arguments.voice_policy,
                flow_operation_budget=arguments.flow_operation_budget,
                flow_repository=arguments.flow_repository,
                flow_profile=arguments.flow_profile,
                style_reference=arguments.style_reference,
                reference_profile=arguments.reference_profile,
                story_profile=arguments.story_profile,
            )
        elif arguments.command == "generate":
            result = generate_flow_candidates(
                output_dir=arguments.output_dir,
                approve_paid_ops=arguments.approve_paid_ops,
            )
        elif arguments.command == "assemble":
            result = assemble_production_edit(
                output_dir=arguments.output_dir,
            )
        else:
            result = approve_production_edit(
                output_dir=arguments.output_dir,
                reviewer=arguments.reviewer,
            )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

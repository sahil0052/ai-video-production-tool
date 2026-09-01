from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def build_reference_story_v2_blueprint(**kwargs):
    from app.editor.reference_story_v2 import (
        build_reference_story_v2_blueprint as implementation,
    )

    return implementation(**kwargs)


def generate_flow_candidates(**kwargs):
    from app.editor.production_v4 import (
        generate_flow_candidates as implementation,
    )

    return implementation(**kwargs)


def review_flow_candidate(**kwargs):
    from app.editor.production_v4 import (
        review_flow_candidate as implementation,
    )

    return implementation(**kwargs)


def assemble_reference_story_v2(**kwargs):
    from app.editor.reference_story_v2 import (
        assemble_reference_story_v2 as implementation,
    )

    return implementation(**kwargs)


def remaster_reference_story_v2(**kwargs):
    from app.editor.reference_story_v2 import (
        remaster_reference_story_v2 as implementation,
    )

    return implementation(**kwargs)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the Flow-assisted 0809 visual-upgrade V2 edit."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan")
    plan.add_argument("source", type=Path)
    plan.add_argument("output_dir", type=Path)

    generate = subparsers.add_parser("generate")
    generate.add_argument("output_dir", type=Path)
    generate.add_argument("--approve-paid-ops", type=int, required=True)

    accept = subparsers.add_parser("accept")
    accept.add_argument("output_dir", type=Path)
    accept.add_argument("--shot-id", required=True)
    accept.add_argument("--attempt", type=int, required=True)
    accept.add_argument("--start-ms", type=int, required=True)
    accept.add_argument("--end-ms", type=int, required=True)
    accept.add_argument("--semantic-score", type=int, default=5)
    accept.add_argument("--composition-score", type=int, default=4)
    accept.add_argument("--motion-score", type=int, default=4)
    accept.add_argument("--continuity-score", type=int, default=4)
    accept.add_argument("--style-score", type=int, default=4)
    accept.add_argument("--editability-score", type=int, default=4)

    assemble = subparsers.add_parser("assemble")
    assemble.add_argument("output_dir", type=Path)

    remaster = subparsers.add_parser("remaster")
    remaster.add_argument("output_dir", type=Path)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    arguments = build_parser().parse_args()
    if arguments.command == "plan":
        result = build_reference_story_v2_blueprint(
            source=arguments.source,
            output_dir=arguments.output_dir,
        )
    elif arguments.command == "generate":
        result = generate_flow_candidates(
            output_dir=arguments.output_dir,
            approve_paid_ops=arguments.approve_paid_ops,
        )
    elif arguments.command == "accept":
        result = review_flow_candidate(
            output_dir=arguments.output_dir,
            shot_id=arguments.shot_id,
            attempt=arguments.attempt,
            accepted=True,
            scores={
                "prompt_fidelity": arguments.semantic_score,
                "composition": arguments.composition_score,
                "motion_quality": arguments.motion_score,
                "continuity": arguments.continuity_score,
                "artifact_integrity": arguments.style_score,
                "editorial_usefulness": arguments.editability_score,
            },
            accepted_start_ms=arguments.start_ms,
            accepted_end_ms=arguments.end_ms,
            reviewer="codex-production-review",
        )
    elif arguments.command == "assemble":
        result = assemble_reference_story_v2(
            output_dir=arguments.output_dir,
        )
    else:
        result = remaster_reference_story_v2(
            output_dir=arguments.output_dir,
        )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

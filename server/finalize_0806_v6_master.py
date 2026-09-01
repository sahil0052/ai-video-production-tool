from __future__ import annotations

import json
from pathlib import Path
import sys


SERVER_DIR = Path(__file__).resolve().parent
WORKSPACE = SERVER_DIR.parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from app.editor.production_assembly import (  # noqa: E402
    compile_production_plan,
    master_production_render,
    run_automated_production_review,
)
from app.editor.production_v4 import ProductionStore  # noqa: E402


OUTPUT_DIR = (
    WORKSPACE
    / "storage"
    / "deliverables"
    / "0806-production-v6-social-kinetic-fast"
)


def main() -> int:
    store = ProductionStore(OUTPUT_DIR)
    record = store.load()
    if record.state != "blueprint-ready":
        raise ValueError(
            f"Master-only repair requires blueprint-ready, got {record.state}"
        )
    plan = compile_production_plan(OUTPUT_DIR)
    rendered = OUTPUT_DIR / "rendered-v4.mp4"
    edited = OUTPUT_DIR / "edited.mp4"
    if not rendered.is_file():
        raise FileNotFoundError(rendered)

    store.transition(
        "assembling",
        detail=(
            "Reusing the matching corrected Remotion render for a measured "
            "final-grade and mastered-audio repair."
        ),
        updates={"error": None},
    )
    try:
        master_production_render(
            plan=plan,
            rendered=rendered,
            output=edited,
            duration_seconds=plan.duration_ms / 1000,
            target_lufs=plan.audio.integrated_lufs,
            target_true_peak=plan.audio.true_peak_dbtp,
            target_lra=plan.audio.target_lra_lu,
        )
        store.transition(
            "automated-review",
            detail="Corrected final master complete; release gates are running.",
        )
        report = run_automated_production_review(
            output_dir=OUTPUT_DIR,
            plan=plan,
            edited=edited,
        )
    except Exception:
        current = store.load()
        if current.state in {"assembling", "automated-review"}:
            store.transition(
                "blueprint-ready",
                detail="Master-only repair failed; prior production assets remain intact.",
                updates={"automated_pass": False},
            )
        raise

    if report["automated_pass"]:
        final = store.transition(
            "awaiting-final-approval",
            detail=(
                "Automated gates passed; side-by-side human approval "
                "is required before release."
            ),
            updates={"automated_pass": True, "error": None},
        )
    else:
        final = store.transition(
            "blueprint-ready",
            detail=(
                "Automated gates blocked release. Review review-report.json "
                "before retrying."
            ),
            updates={
                "automated_pass": False,
                "error": (
                    "Automated production gates failed. Review "
                    "review-report.json before retrying assembly."
                ),
            },
        )
    print(json.dumps(final.model_dump(mode="json"), indent=2))
    return 0 if report["automated_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

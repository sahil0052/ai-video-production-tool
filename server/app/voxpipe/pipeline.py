from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

from app.voxpipe.stages.transcription import transcribe_video_whisper
from app.voxpipe.stages.planner import plan_beats_from_transcript
from app.voxpipe.stages.asset_resolver import resolve_assets_for_plan
from app.voxpipe.stages.synthesizer import synthesize_master_video
from app.voxpipe.stages.verifier import verify_rendered_master, QCReport
from app.voxpipe.core.encode_standards import get_job_deliverable_dir, WORKSPACE_ROOT

logger = logging.getLogger("voxpipe.pipeline")


def run_voxpipe_pipeline(
    raw_video_path: str,
    job_id: Optional[str] = None,
    transcript_cache_json: Optional[str] = None,
) -> dict:
    """Executes the full automated Voxpipe production pipeline."""
    video_p = Path(raw_video_path)
    if not video_p.is_absolute():
        video_p = (WORKSPACE_ROOT / video_p).resolve()

    if not video_p.exists():
        raise FileNotFoundError(f"Raw video not found: {video_p}")

    if not job_id:
        job_id = f"voxpipe_{video_p.stem}_{int(time.time())}"

    job_dir = get_job_deliverable_dir(job_id)
    logger.info(f"=== Starting Voxpipe Production for Job: {job_id} ===")

    # 1. Transcription
    if transcript_cache_json:
        cache_p = Path(transcript_cache_json)
        if not cache_p.is_absolute():
            cache_p = (WORKSPACE_ROOT / cache_p).resolve()
    else:
        cache_p = job_dir / "transcript.json"

    transcript_data = transcribe_video_whisper(video_p, cache_json=cache_p)

    # 2. Planning
    plan = plan_beats_from_transcript(transcript_data, str(video_p), job_id)
    plan_file = job_dir / "EditPlan.json"
    with open(plan_file, "w", encoding="utf-8") as f:
        json.dump(plan.model_dump(), f, indent=2, ensure_ascii=False)
    logger.info(f"Saved EditPlan.json to {plan_file}")

    # 3. Asset Resolution
    resolved_plan = resolve_assets_for_plan(plan)

    # 4. Master Synthesis
    output_mp4 = synthesize_master_video(resolved_plan)

    # 5. Objective QC Verification
    qc_report = verify_rendered_master(output_mp4, resolved_plan.duration, job_dir)
    qc_file = job_dir / "qc_report.json"
    with open(qc_file, "w", encoding="utf-8") as f:
        json.dump(qc_report.to_dict(), f, indent=2)

    logger.info(f"=== Voxpipe Production Complete! QC Score: {qc_report.score}/100, Passed: {qc_report.passed} ===")

    return {
        "job_id": job_id,
        "output_video": str(output_mp4),
        "plan_file": str(plan_file),
        "qc_report": qc_report.to_dict(),
    }

from __future__ import annotations

import argparse
import json
import logging
import sys

from app.voxpipe.pipeline import run_voxpipe_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def main():
    parser = argparse.ArgumentParser(description="Voxpipe Automated Video Production Engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run full production pipeline on raw video")
    run_parser.add_argument("video", help="Path to raw video (.mp4)")
    run_parser.add_argument("--job-id", help="Optional custom job ID")
    run_parser.add_argument("--transcript", help="Optional cached transcript JSON path")

    args = parser.parse_args()

    if args.command == "run":
        res = run_voxpipe_pipeline(
            raw_video_path=args.video,
            job_id=args.job_id,
            transcript_cache_json=args.transcript,
        )
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()

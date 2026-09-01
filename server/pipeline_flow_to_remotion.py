"""
End-to-End Google Flow AI Video Generation & Remotion Multi-Layer Production Synthesizer
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from imageio_ffmpeg import get_ffmpeg_exe
from app.editor.viral_verification_gatekeeper import ViralVerificationGatekeeper
from server.google_flow_client import GoogleFlowClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FlowToRemotionPipeline")

FLOW_VIDEOS_DIR = WORKSPACE / "renderer" / "public" / "flow_videos"
DELIVERABLE_DIR = WORKSPACE / "storage" / "deliverables" / "flow-animated-master"
FINAL_MASTER = DELIVERABLE_DIR / "flow-master.mp4"
DELIVERABLE_COPY = WORKSPACE / "storage" / "deliverables" / "0824-varun-mayya-style" / "edited.mp4"
VIRAL_SFX_DIR = WORKSPACE / "storage" / "assets" / "viral_sfx_library"
PROCEDURAL_SFX_DIR = WORKSPACE / "storage" / "deliverables" / "0824-certified-master" / "assets" / "sfx"

FLOW_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
DELIVERABLE_DIR.mkdir(parents=True, exist_ok=True)

FFMPEG = get_ffmpeg_exe()

# Scene definitions with exact frame timings across the 36.46s (1094 frames @ 30fps)
SCENE_PROMPTS = [
    {
        "id": "scene01_hook",
        "prompt": "Cinematic 3D animation of a vintage human anatomical head with glowing electrical neural circuits and floating Indian rupee banknotes, 4k 60fps, dramatic camera push in",
        "startFrame": 0,
        "durationInFrames": 88,
    },
    {
        "id": "scene02_fear",
        "prompt": "Cinematic 3D shot of a nervous 1950s businessman walking in heavy rain holding an umbrella protecting a small 1000 rupee note, dramatic green safety shield aura, 4k 60fps",
        "startFrame": 88,
        "durationInFrames": 74,
    },
    {
        "id": "scene03_greed",
        "prompt": "Cinematic explosion of 10000 rupee cash stacks and gold coins raining down on a vintage Wall Street trading exchange desk, 3D slow motion 60fps",
        "startFrame": 162,
        "durationInFrames": 55,
    },
    {
        "id": "scene04_ego",
        "prompt": "Cinematic 3D animation of a proud smug businessman with a glowing gold crown above his head surrounded by swirling stock ticker tape ribbons, 4k 60fps",
        "startFrame": 217,
        "durationInFrames": 98,
    },
    {
        "id": "scene05_trap",
        "prompt": "Cinematic 3D camera pan across an ancient gold mouse trap overflowing with dollar bills and currency, glowing red warning laser grid, 4k 60fps",
        "startFrame": 315,
        "durationInFrames": 90,
    },
    {
        "id": "scene06_streak",
        "prompt": "Cinematic 3D macro shot of a magnifying glass moving across glowing green upward stock candlestick charts with multiplying golden coins, 4k 60fps",
        "startFrame": 405,
        "durationInFrames": 90,
    },
    {
        "id": "scene07_leverage",
        "prompt": "Cinematic 3D physics simulation of a giant heavy 500X iron anvil weight slamming onto a balance scale lifting a tiny gold coin into the air, 4k 60fps",
        "startFrame": 495,
        "durationInFrames": 90,
    },
    {
        "id": "scene08_loss",
        "prompt": "Cinematic 3D stock market crash with jagged red candlestick chart plunging through shattered glass floor into deep dark abyss, 4k 60fps",
        "startFrame": 585,
        "durationInFrames": 90,
    },
    {
        "id": "scene09_revenge",
        "prompt": "Cinematic 3D shot of an aggressive trader slamming fists on desk with fiery red candlestick charts swirling in background, 4k 60fps",
        "startFrame": 675,
        "durationInFrames": 90,
    },
    {
        "id": "scene10_market",
        "prompt": "Cinematic 3D vintage trading board with a giant red paint X crossing out the text THE MARKET, camera zoom, 4k 60fps",
        "startFrame": 765,
        "durationInFrames": 90,
    },
    {
        "id": "scene11_damage",
        "prompt": "Cinematic 3D shot of a cracked bank vault door blowing open with burned dollar ledger sheets floating in ashes, 4k 60fps",
        "startFrame": 855,
        "durationInFrames": 75,
    },
    {
        "id": "scene12_ea",
        "prompt": "Cinematic 3D futuristic robotic arm typing algorithmic trading code on glowing cyan holographic trading terminal, 4k 60fps",
        "startFrame": 930,
        "durationInFrames": 84,
    },
    {
        "id": "scene13_cta",
        "prompt": "Cinematic 3D glowing red follow button badge stamping down onto an aged world map trading desk with golden light rays, 4k 60fps",
        "startFrame": 1014,
        "durationInFrames": 80,
    },
]

def run_pipeline(generate_cloud_videos: bool = False):
    logger.info("================================================================")
    logger.info("🚀 Starting Google Flow to Remotion AI Video Production Pipeline")
    logger.info("================================================================")

    client = GoogleFlowClient()

    if generate_cloud_videos:
        logger.info(f"Submitting {len(SCENE_PROMPTS)} scene animation jobs to Google Flow...")
        for scene in SCENE_PROMPTS:
            out_file = f"{scene['id']}.mp4"
            target_path = FLOW_VIDEOS_DIR / out_file
            if not target_path.exists():
                logger.info(f"Generating video for: {scene['id']}...")
                try:
                    client.generate_and_download(
                        prompt=scene["prompt"],
                        duration=5,
                        aspect_ratio="VIDEO_ASPECT_RATIO_PORTRAIT",
                        output_filename=out_file
                    )
                except Exception as e:
                    logger.error(f"Error generating {scene['id']}: {e}")
            else:
                logger.info(f"Found existing clip for {scene['id']}, skipping generation.")
    else:
        logger.info("Cloud generation flag is false. Utilizing staged video assets and Remotion engine.")

    logger.info("Pipeline Ready for High-End Video Production!")

if __name__ == "__main__":
    run_pipeline(generate_cloud_videos=False)

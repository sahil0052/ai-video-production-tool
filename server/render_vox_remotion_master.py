"""
Remotion 3D Vox Split-Screen Master Renderer with Automated 95+ Gatekeeper Audit
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe
from app.editor.viral_verification_gatekeeper import ViralVerificationGatekeeper

FFMPEG = get_ffmpeg_exe()
WORKSPACE = Path(__file__).resolve().parent.parent
RENDERER_DIR = WORKSPACE / "renderer"
OUTPUT_DIR = WORKSPACE / "storage" / "deliverables" / "0824-vox-remotion-master"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DELIVERABLE_PATH = WORKSPACE / "storage" / "deliverables" / "0824-varun-mayya-style" / "edited.mp4"
VIRAL_SFX_DIR = WORKSPACE / "storage" / "assets" / "viral_sfx_library"
PROCEDURAL_SFX_DIR = WORKSPACE / "storage" / "deliverables" / "0824-certified-master" / "assets" / "sfx"


def render_vox_remotion_master() -> Path:
    raw_video = RENDERER_DIR / "public" / "0824.mp4"
    remotion_video_out = OUTPUT_DIR / "remotion_visual_pass.mp4"
    final_master_out = OUTPUT_DIR / "0824-vox-remotion-master.mp4"

    print("[Step 1/4] Rendering Remotion 3D Multi-Layer Composition (1080x1920 @ 30fps)...")
    cmd_remotion = [
        "npx.cmd", "remotion", "render",
        "src/index.ts",
        "VoxSplitScreenMaster",
        str(remotion_video_out),
        "--gl=angle",
        "--concurrency=4",
        "--crf=15",
    ]

    res_remotion = subprocess.run(
        cmd_remotion,
        cwd=str(RENDERER_DIR),
        capture_output=True,
        text=True,
        errors="replace"
    )

    if res_remotion.returncode != 0:
        print("Remotion Render Output:\n", res_remotion.stdout[-2000:], res_remotion.stderr[-2000:])
        raise RuntimeError("Remotion composition rendering failed.")

    print(f"[Step 1 Complete] Visual pass rendered: {remotion_video_out} ({remotion_video_out.stat().st_size / 1024 / 1024:.2f} MB)")

    print("[Step 2/4] Mixing Frame-Accurate Micro-Foley and Dialogue Audio...")
    
    # Sound FX Cues
    thud_sfx = PROCEDURAL_SFX_DIR / "stamp_thud.wav"
    whoosh_sfx = PROCEDURAL_SFX_DIR / "whoosh.wav"
    pop_sfx = PROCEDURAL_SFX_DIR / "pop.wav"
    tick_sfx = PROCEDURAL_SFX_DIR / "tick.wav"
    riser_sfx = PROCEDURAL_SFX_DIR / "riser.wav"
    drop_sfx = PROCEDURAL_SFX_DIR / "drop.wav"
    chime_sfx = PROCEDURAL_SFX_DIR / "chime.wav"
    card_slide_sfx = VIRAL_SFX_DIR / "paper_and_cards" / "card-slide-1.mp3"

    filter_complex = (
        f"[2:a]adelay=0|0,volume=0.9[sfx0];"          # Stamp Thud @ 0.0s (Hook)
        f"[3:a]adelay=1400|1400,volume=0.85[sfx1];"    # Whoosh @ 1.40s (90% Lose)
        f"[4:a]adelay=2060|2060,volume=0.8[sfx2];"     # Pop Snap @ 2.06s ("Why?")
        f"[5:a]adelay=2880|2880,volume=0.75[sfx3];"    # Data Tick @ 2.88s (Market Cross)
        f"[6:a]adelay=5580|5580,volume=0.75[sfx4];"    # Data Tick @ 5.58s (Risk)
        f"[7:a]adelay=14980|14980,volume=0.85[sfx5];"  # Riser @ 14.98s (Fast Loss)
        f"[8:a]adelay=19640|19640,volume=0.9[sfx6];"   # Alert Drop @ 19.64s (Revenge)
        f"[9:a]adelay=34520|34520,volume=0.85[sfx7];"  # Chime @ 34.52s (Follow CTA)
        f"[10:a]adelay=7440|7440,volume=0.8[sfx8];"    # Card Slide @ 7.44s (Capital Risk)
        f"[1:a][sfx0][sfx1][sfx2][sfx3][sfx4][sfx5][sfx6][sfx7][sfx8]amix=inputs=10:duration=first:dropout_transition=2[a_mixed];"
        f"[a_mixed]loudnorm=I=-14:TP=-1.0:LRA=7[a_out]"
    )

    cmd_audio = [
        FFMPEG, "-y",
        "-i", str(remotion_video_out),
        "-i", str(raw_video),
        "-i", str(thud_sfx),
        "-i", str(whoosh_sfx),
        "-i", str(pop_sfx),
        "-i", str(tick_sfx),
        "-i", str(tick_sfx),
        "-i", str(riser_sfx),
        "-i", str(drop_sfx),
        "-i", str(chime_sfx),
        "-i", str(card_slide_sfx),
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[a_out]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(final_master_out)
    ]

    res_audio = subprocess.run(cmd_audio, capture_output=True, text=True, errors="replace")
    if res_audio.returncode != 0:
        print("Audio Mix Error:\n", res_audio.stderr[-2000:])
        raise RuntimeError("Audio mix failed.")

    print(f"[Step 2 Complete] Master video synthesized: {final_master_out}")

    print("\n[Step 3/4] Running Automated 95+ Benchmark Verification Gatekeeper Audit...")
    gate = ViralVerificationGatekeeper(min_pass_score=95)

    transcript_p = WORKSPACE / "storage" / "0824_transcript.json"
    with open(transcript_p, "r", encoding="utf-8") as f:
        t_data = json.load(f)
    words = []
    for s in t_data.get("segments", []):
        words.extend(s.get("words", []))

    scenes = [
        {"name": "b01", "dur": 1.40}, {"name": "b02", "dur": 0.66},
        {"name": "b03", "dur": 0.82}, {"name": "b04", "dur": 0.86},
        {"name": "b05", "dur": 1.84}, {"name": "b06", "dur": 1.86},
        {"name": "b07", "dur": 1.76}, {"name": "b08", "dur": 2.02},
        {"name": "b09", "dur": 0.92}, {"name": "b10", "dur": 2.84},
        {"name": "b11", "dur": 2.52}, {"name": "b12", "dur": 2.14},
        {"name": "b13", "dur": 2.16}, {"name": "b14", "dur": 2.62},
        {"name": "b15", "dur": 4.08}, {"name": "b16", "dur": 3.00},
        {"name": "b17", "dur": 3.02}, {"name": "b18", "dur": 3.58}
    ]

    sfx_events = [
        {"type": "stamp", "t": 0.0}, {"type": "whoosh", "t": 1.4},
        {"type": "pop", "t": 2.06}, {"type": "tick", "t": 2.88},
        {"type": "tick", "t": 5.58}, {"type": "card_slide", "t": 7.44},
        {"type": "riser", "t": 14.98}, {"type": "drop", "t": 19.64},
        {"type": "chime", "t": 34.52}
    ]

    report = gate.audit_video(final_master_out, scenes, sfx_events, words)

    print("=" * 60)
    print(f"VERIFICATION SCORE: {report['total_score']} / 100")
    print(f"STATUS: {report['status']}")
    print("=" * 60)
    for log in report["audit_logs"]:
        print(log)

    if not report["passed"]:
        raise ValueError(f"Score {report['total_score']} < {report['min_pass_score']}! Revision required.")

    shutil.copy2(final_master_out, DELIVERABLE_PATH)
    print(f"\n[Step 4/4] SUCCESS: Certified Master copied to {DELIVERABLE_PATH} ({DELIVERABLE_PATH.stat().st_size / 1024 / 1024:.2f} MB)")
    return DELIVERABLE_PATH


if __name__ == "__main__":
    render_vox_remotion_master()

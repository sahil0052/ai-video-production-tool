"""
Remotion 3D Multi-Layer Certified Master Synthesizer for 0826 Video with 95+ Gatekeeper
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
DELIVERABLE_DIR = WORKSPACE / "storage" / "deliverables" / "0826-certified-master"
FINAL_MASTER = DELIVERABLE_DIR / "0826-vox-remotion-master.mp4"
DELIVERABLE_COPY = WORKSPACE / "storage" / "deliverables" / "0824-varun-mayya-style" / "edited.mp4"
VIRAL_SFX_DIR = WORKSPACE / "storage" / "assets" / "viral_sfx_library"
PROCEDURAL_SFX_DIR = WORKSPACE / "storage" / "deliverables" / "0824-certified-master" / "assets" / "sfx"

top_half_video = DELIVERABLE_DIR / "0826_top_half.mp4"
chunk1 = DELIVERABLE_DIR / "chunk1.mp4"
chunk2 = DELIVERABLE_DIR / "chunk2.mp4"
concat_txt = DELIVERABLE_DIR / "concat.txt"

# Step 1: Concatenate top-half chunks
print("[1/4] Concatenating 0826 Remotion top-half chunks...")
concat_txt.write_text(f"file '{chunk1.name}'\nfile '{chunk2.name}'\n", encoding="ascii")
cmd_concat = [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(top_half_video)]
subprocess.run(cmd_concat, check=True)

# Step 2: Synthesis
source_video = Path(r"D:\Downloads\0826 (1).mp4")
ass_path = DELIVERABLE_DIR / "captions.ass"
ass_filter_path = str(ass_path).replace("\\", "/").replace(":", "\\:")

# Foley Audio SFX paths
thud_sfx = PROCEDURAL_SFX_DIR / "stamp_thud.wav"
whoosh_sfx = PROCEDURAL_SFX_DIR / "whoosh.wav"
pop_sfx = PROCEDURAL_SFX_DIR / "pop.wav"
tick_sfx = PROCEDURAL_SFX_DIR / "tick.wav"
riser_sfx = PROCEDURAL_SFX_DIR / "riser.wav"
drop_sfx = PROCEDURAL_SFX_DIR / "drop.wav"
chime_sfx = PROCEDURAL_SFX_DIR / "chime.wav"
card_slide_sfx = VIRAL_SFX_DIR / "paper_and_cards" / "card-slide-1.mp3"

filter_complex = (
    # Top Half: Rich Vox Paper Collage Diorama (1080x960)
    f"[1:v]scale=1080:960,fps=30[v_top];"
    
    # Bottom Half: Presenter crop
    f"[0:v]scale=1080:1920,crop=1080:960:0:380,fps=30[v_bottom];"
    
    # Vertical Split Stack
    f"[v_top][v_bottom]vstack=inputs=2[v_split];"
    
    # Center Archival Divider
    f"[v_split]drawbox=x=0:y=956:w=1080:h=8:color=#1A1A1A@1.0:t=fill[v_divided];"
    
    # Studio Color Grade
    f"[v_divided]eq=contrast=1.08:brightness=0.01:saturation=1.12[v_graded];"
    
    # Kinetic Monospace Subtitles
    f"[v_graded]ass='{ass_filter_path}'[v_out];"
    
    # Multi-Track Frame-Accurate Foley Audio Mix
    f"[2:a]adelay=0|0,volume=0.9[sfx0];"          # Stamp Thud @ 0.00s (Hook)
    f"[3:a]adelay=1160|1160,volume=0.85[sfx1];"    # Whoosh @ 1.16s (Stupid Decisions)
    f"[4:a]adelay=2960|2960,volume=0.8[sfx2];"     # Pop Snap @ 2.96s (1k Fear)
    f"[5:a]adelay=5420|5420,volume=0.75[sfx3];"    # Data Tick @ 5.42s (10k Greed)
    f"[6:a]adelay=7240|7240,volume=0.85[sfx4];"    # Card Slide @ 7.24s (Confidence +)
    f"[7:a]adelay=10500|10500,volume=0.85[sfx5];"  # Stamp Thud @ 10.50s (Overconfidence)
    f"[8:a]adelay=16500|16500,volume=0.9[sfx6];"   # Alert Drop @ 16.50s (Position Size 10x)
    f"[9:a]adelay=19500|19500,volume=0.85[sfx7];"  # Riser @ 19.50s (Fast Loss)
    f"[10:a]adelay=22500|22500,volume=0.9[sfx8];"  # Stamp Thud @ 22.50s (Revenge)
    f"[0:a][sfx0][sfx1][sfx2][sfx3][sfx4][sfx5][sfx6][sfx7][sfx8]amix=inputs=10:duration=first:dropout_transition=2[a_mixed];"
    f"[a_mixed]loudnorm=I=-14:TP=-1.0:LRA=7[a_out]"
)

cmd = [
    FFMPEG, "-y",
    "-i", str(source_video),
    "-i", str(top_half_video),
    "-i", str(thud_sfx),
    "-i", str(whoosh_sfx),
    "-i", str(pop_sfx),
    "-i", str(tick_sfx),
    "-i", str(card_slide_sfx),
    "-i", str(thud_sfx),
    "-i", str(drop_sfx),
    "-i", str(riser_sfx),
    "-i", str(thud_sfx),
    "-filter_complex", filter_complex,
    "-map", "[v_out]",
    "-map", "[a_out]",
    "-c:v", "libx264",
    "-preset", "fast",
    "-crf", "15",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-b:a", "192k",
    "-movflags", "+faststart",
    str(FINAL_MASTER)
]

print("[2/4] Merging Remotion Rich Vox Top-Half + Presenter Bottom-Half + 10-Track Audio...")
res = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
if res.returncode != 0:
    print("Error:\n", res.stderr[-2500:])
    raise RuntimeError("Master synthesis failed.")

print("\n[3/4] Running Automated 95+ Benchmark Verification Audit...")
gate = ViralVerificationGatekeeper(min_pass_score=95)

transcript_p = WORKSPACE / "storage" / "0826_transcript.json"
with open(transcript_p, "r", encoding="utf-8") as f:
    t_data = json.load(f)
words = []
for s in t_data.get("segments", []):
    words.extend(s.get("words", []))

scenes = [
    {"name": "s01_brain", "dur": 2.96},
    {"name": "s02_fear", "dur": 2.46},
    {"name": "s03_greed", "dur": 1.82},
    {"name": "s04_confidence", "dur": 3.26},
    {"name": "s05_overconfidence", "dur": 3.00},
    {"name": "s06_winstreak", "dur": 3.00},
    {"name": "s07_positionsize", "dur": 3.00},
    {"name": "s08_fastloss", "dur": 3.00},
    {"name": "s09_revenge", "dur": 3.00},
    {"name": "s10_marketbehaviour", "dur": 3.00},
    {"name": "s11_accountdamage", "dur": 2.50},
    {"name": "s12_discipline_ea", "dur": 2.80},
    {"name": "s13_cta_follow", "dur": 2.66}
]

sfx_events = [
    {"type": "stamp", "t": 0.0}, {"type": "whoosh", "t": 1.16},
    {"type": "pop", "t": 2.96}, {"type": "tick", "t": 5.42},
    {"type": "card_slide", "t": 7.24}, {"type": "stamp", "t": 10.50},
    {"type": "drop", "t": 16.50}, {"type": "riser", "t": 19.50},
    {"type": "stamp", "t": 22.50}
]

report = gate.audit_video(FINAL_MASTER, scenes, sfx_events, words)

print("=" * 60)
print(f"VERIFICATION SCORE: {report['total_score']} / 100")
print(f"STATUS: {report['status']}")
print("=" * 60)
for log in report["audit_logs"]:
    print(log)

if not report["passed"]:
    raise ValueError(f"Score {report['total_score']} < {report['min_pass_score']}! Revision required.")

shutil.copy2(FINAL_MASTER, DELIVERABLE_COPY)
print(f"\n[4/4] SUCCESS: Certified 0826 Master Deliverable saved to {DELIVERABLE_COPY} ({DELIVERABLE_COPY.stat().st_size / 1024 / 1024:.2f} MB)")

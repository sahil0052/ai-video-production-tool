"""
Clean Remotion 3D Multi-Layer Master Synthesizer with Organic Foley & Modern Viral Subtitles
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
FINAL_MASTER = DELIVERABLE_DIR / "0826-clean-viral-master.mp4"
DELIVERABLE_COPY = WORKSPACE / "storage" / "deliverables" / "0824-varun-mayya-style" / "edited.mp4"
VIRAL_SFX_DIR = WORKSPACE / "storage" / "assets" / "viral_sfx_library"
PROCEDURAL_SFX_DIR = WORKSPACE / "storage" / "deliverables" / "0824-certified-master" / "assets" / "sfx"

top_half_video = DELIVERABLE_DIR / "0826_clean_top_half.mp4"
chunk1 = DELIVERABLE_DIR / "chunk1.mp4"
chunk2 = DELIVERABLE_DIR / "chunk2.mp4"
concat_txt = DELIVERABLE_DIR / "concat_clean.txt"

# Step 1: Concatenate top-half chunks
print("[1/4] Concatenating clean Remotion top-half chunks...")
concat_txt.write_text(f"file '{chunk1.name}'\nfile '{chunk2.name}'\n", encoding="ascii")
cmd_concat = [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(top_half_video)]
subprocess.run(cmd_concat, check=True)

# Step 2: Synthesis
source_video = Path(r"D:\Downloads\0826 (1).mp4")
ass_path = DELIVERABLE_DIR / "exact_synced_captions.ass"
ass_filter_path = str(ass_path).replace("\\", "/").replace(":", "\\:")

# Natural Foley SFX paths
sfx_slide1 = VIRAL_SFX_DIR / "paper_and_cards" / "card-slide-1.mp3"
sfx_flip1 = VIRAL_SFX_DIR / "paper_and_cards" / "book-flip-1.mp3"
sfx_coins = VIRAL_SFX_DIR / "bells_and_chimes" / "handle-coins.mp3"
sfx_place1 = VIRAL_SFX_DIR / "paper_and_cards" / "card-place-1.mp3"
sfx_switch = VIRAL_SFX_DIR / "switches_and_toggles" / "switch-001.mp3"
sfx_slide2 = VIRAL_SFX_DIR / "paper_and_cards" / "card-slide-2.mp3"
sfx_shove = VIRAL_SFX_DIR / "paper_and_cards" / "card-shove-1.mp3"
sfx_whoosh = PROCEDURAL_SFX_DIR / "whoosh.wav"
sfx_place2 = VIRAL_SFX_DIR / "paper_and_cards" / "card-place-2.mp3"
sfx_slide3 = VIRAL_SFX_DIR / "paper_and_cards" / "card-slide-3.mp3"
sfx_close = VIRAL_SFX_DIR / "paper_and_cards" / "book-close.mp3"
sfx_click = VIRAL_SFX_DIR / "clicks" / "click-soft.mp3"
sfx_chime = VIRAL_SFX_DIR / "bells_and_chimes" / "success-chime.mp3"

filter_complex = (
    # Top Half: Pure Clean Vox Diorama (1080x960)
    f"[1:v]scale=1080:960,fps=30[v_top];"
    
    # Bottom Half: Presenter crop
    f"[0:v]scale=1080:1920,crop=1080:960:0:380,fps=30[v_bottom];"
    
    # Vertical Split Stack
    f"[v_top][v_bottom]vstack=inputs=2[v_split];"
    
    # Sleek 4px Dark Divider
    f"[v_split]drawbox=x=0:y=958:w=1080:h=4:color=#1A1A1A@0.85:t=fill[v_divided];"
    
    # Studio Color Grade (No subtitles)
    f"[v_divided]eq=contrast=1.06:brightness=0.01:saturation=1.10[v_out];"
    
    # Multi-Track Natural Foley Audio Mix
    f"[2:a]adelay=0|0,volume=0.85[a0];"            # card-slide-1 @ 0.00s
    f"[3:a]adelay=2960|2960,volume=0.8[a1];"        # book-flip-1 @ 2.96s
    f"[4:a]adelay=5420|5420,volume=0.75[a2];"       # handle-coins @ 5.42s
    f"[5:a]adelay=7240|7240,volume=0.8[a3];"        # card-place-1 @ 7.24s
    f"[6:a]adelay=10500|10500,volume=0.75[a4];"     # switch-001 @ 10.50s
    f"[7:a]adelay=13500|13500,volume=0.8[a5];"      # card-slide-2 @ 13.50s
    f"[8:a]adelay=16500|16500,volume=0.8[a6];"      # card-shove-1 @ 16.50s
    f"[9:a]adelay=19500|19500,volume=0.8[a7];"      # whoosh @ 19.50s
    f"[10:a]adelay=22500|22500,volume=0.8[a8];"     # card-place-2 @ 22.50s
    f"[11:a]adelay=25500|25500,volume=0.8[a9];"     # card-slide-3 @ 25.50s
    f"[12:a]adelay=28500|28500,volume=0.8[a10];"    # book-close @ 28.50s
    f"[13:a]adelay=31000|31000,volume=0.75[a11];"   # click-soft @ 31.00s
    f"[14:a]adelay=33800|33800,volume=0.85[a12];"   # success-chime @ 33.80s
    f"[0:a][a0][a1][a2][a3][a4][a5][a6][a7][a8][a9][a10][a11][a12]amix=inputs=14:duration=first:dropout_transition=2[a_mixed];"
    f"[a_mixed]loudnorm=I=-14:TP=-1.0:LRA=7[a_out]"
)

cmd = [
    FFMPEG, "-y",
    "-i", str(source_video),
    "-i", str(top_half_video),
    "-i", str(sfx_slide1),
    "-i", str(sfx_flip1),
    "-i", str(sfx_coins),
    "-i", str(sfx_place1),
    "-i", str(sfx_switch),
    "-i", str(sfx_slide2),
    "-i", str(sfx_shove),
    "-i", str(sfx_whoosh),
    "-i", str(sfx_place2),
    "-i", str(sfx_slide3),
    "-i", str(sfx_close),
    "-i", str(sfx_click),
    "-i", str(sfx_chime),
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

print("[2/4] Merging Clean Vox Top-Half + Presenter Bottom-Half + 14-Track Foley + Viral Captions...")
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
    {"name": "s10_marketbehaviour", "dur": 2.50},
    {"name": "s11_accountdamage", "dur": 2.50},
    {"name": "s12_discipline_ea", "dur": 2.80},
    {"name": "s13_cta_follow", "dur": 2.66}
]

sfx_events = [
    {"type": "card_slide", "t": 0.0}, {"type": "book_flip", "t": 2.96},
    {"type": "coins", "t": 5.42}, {"type": "card_place", "t": 7.24},
    {"type": "switch", "t": 10.50}, {"type": "card_slide", "t": 13.50},
    {"type": "card_shove", "t": 16.50}, {"type": "whoosh", "t": 19.50},
    {"type": "card_place", "t": 22.50}, {"type": "card_slide", "t": 25.50},
    {"type": "book_close", "t": 28.50}, {"type": "click", "t": 31.00},
    {"type": "chime", "t": 33.80}
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
print(f"\n[4/4] SUCCESS: Clean Viral Master Deliverable saved to {DELIVERABLE_COPY} ({DELIVERABLE_COPY.stat().st_size / 1024 / 1024:.2f} MB)")

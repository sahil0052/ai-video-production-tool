import logging
import os
import subprocess
import shutil
from pathlib import Path
from imageio_ffmpeg import get_ffmpeg_exe

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ZeroLatencyLipSyncMaster")

FFMPEG = get_ffmpeg_exe()
WORKSPACE = Path(__file__).resolve().parent.parent
DELIVERABLE_DIR = WORKSPACE / "storage" / "deliverables" / "0826_3_bankrun_master"
DELIVERABLE_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_VIDEO = Path(r"D:\Downloads\0826 (3).mp4")
OUTPUT_VIDEO = DELIVERABLE_DIR / "edited.mp4"
DELIVERABLE_COPY = WORKSPACE / "storage" / "deliverables" / "0824-varun-mayya-style" / "edited.mp4"
FLOW_DIR = WORKSPACE / "renderer" / "public" / "flow_videos"
VIRAL_SFX_DIR = WORKSPACE / "storage" / "assets" / "viral_sfx_library"
PROCEDURAL_SFX_DIR = WORKSPACE / "storage" / "deliverables" / "0824-certified-master" / "assets" / "sfx"

# 1. Build Top-Half Continuous 55.10s 1080x960 Flow Video Track
# Using seamless segment concat so no keyframe drift exists in top track
top_segments_dir = DELIVERABLE_DIR / "top_segments"
top_segments_dir.mkdir(parents=True, exist_ok=True)

TOP_BEATS = [
  # 01: [00.00 - 02.18s] (2.18s): flow_passbook_10lakh
  {"dur": 2.18, "flow": FLOW_DIR / "flow_passbook_10lakh.mp4"},
  # 02: [02.18 - 04.70s] (2.52s): flow_crowd_running_counter
  {"dur": 2.52, "flow": FLOW_DIR / "flow_crowd_running_counter.mp4"},
  # 03: [04.70 - 07.88s] (3.18s): black placeholder (covered by full explainer/character)
  {"dur": 3.18, "flow": None},
  # 04: [07.88 - 10.16s] (2.28s): flow_padlock_safe_loan
  {"dur": 2.28, "flow": FLOW_DIR / "flow_padlock_safe_loan.mp4"},
  # 05: [10.16 - 12.48s] (2.32s): flow_circulation_diagram
  {"dur": 2.32, "flow": FLOW_DIR / "flow_circulation_diagram.mp4"},
  # 06: [12.48 - 16.90s] (4.42s): black placeholder (covered by full explainer/character)
  {"dur": 4.42, "flow": None},
  # 07: [16.90 - 20.82s] (3.92s): flow_hundred_depositors
  {"dur": 3.92, "flow": FLOW_DIR / "flow_hundred_depositors.mp4"},
  # 08: [20.82 - 22.66s] (1.84s): flow_ledger_one_crore
  {"dur": 1.84, "flow": FLOW_DIR / "flow_ledger_one_crore.mp4"},
  # 09: [22.66 - 31.70s] (9.04s): black placeholder (covered by character/mob queue)
  {"dur": 9.04, "flow": None},
  # 10: [31.70 - 35.58s] (3.88s): flow_panicked_banker
  {"dur": 3.88, "flow": FLOW_DIR / "flow_panicked_banker.mp4"},
  # 11: [35.58 - 41.14s] (5.56s): black placeholder (covered by full bankrun/dominoes)
  {"dur": 5.56, "flow": None},
  # 12: [41.14 - 45.18s] (4.04s): flow_panic_contagion_map
  {"dur": 4.04, "flow": FLOW_DIR / "flow_panic_contagion_map.mp4"},
  # 13: [45.18 - 48.48s] (3.30s): black placeholder (covered by character)
  {"dur": 3.30, "flow": None},
  # 14: [48.48 - 51.46s] (2.98s): flow_trust_shield
  {"dur": 2.98, "flow": FLOW_DIR / "flow_trust_shield.mp4"},
  # 15: [51.46 - 55.10s] (3.64s): flow_follow_trading
  {"dur": 3.64, "flow": FLOW_DIR / "flow_follow_trading.mp4"},
]

top_seg_files = []
for idx, b in enumerate(TOP_BEATS):
    p = top_segments_dir / f"top_seg_{idx:02d}.mp4"
    top_seg_files.append(p)
    dur = b["dur"]
    flow_v = b["flow"]
    
    if flow_v and flow_v.exists():
        fc = f"[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,fps=30,setpts=PTS-STARTPTS[out]"
        cmd = [FFMPEG, "-y", "-stream_loop", "-1", "-t", str(dur), "-i", str(flow_v), "-filter_complex", fc, "-map", "[out]", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p", str(p)]
    else:
        # Color black
        fc = f"color=c=black:s=1080x960:d={dur}:r=30[out]"
        cmd = [FFMPEG, "-y", "-filter_complex", fc, "-map", "[out]", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p", str(p)]
    
    subprocess.run(cmd, check=True, capture_output=True)

concat_top_txt = top_segments_dir / "concat_top.txt"
concat_top_txt.write_text("\n".join([f"file '{s.name}'" for s in top_seg_files]) + "\n", encoding="ascii")
top_track_video = DELIVERABLE_DIR / "top_flow_track.mp4"
subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_top_txt), "-c", "copy", str(top_track_video)], check=True)
logger.info(f"Rendered Top Flow Track: {top_track_video}")

# 2. Render Full-Explainer Google Flow AI Video Inserts (1080x1920)
flow_exp_vault = FLOW_DIR / "flow_vault_reality.mp4"
flow_exp_scale = FLOW_DIR / "flow_liquidity_scale.mp4"
flow_exp_crowd = FLOW_DIR / "flow_crowd_queue.mp4"
flow_exp_bankrun = FLOW_DIR / "flow_bankrun_panic.mp4"
flow_exp_domino = FLOW_DIR / "flow_domino_toppling.mp4"

# 3. Single-Pass Sample-Accurate Master Assembly
logger.info("Executing 100% Zero-Latency Continuous Timeline Synthesis...")

sfx_slide1 = VIRAL_SFX_DIR / "paper_and_cards" / "card-slide-1.mp3"
sfx_switch1 = VIRAL_SFX_DIR / "switches_and_toggles" / "switch-001.mp3"
sfx_flip1 = VIRAL_SFX_DIR / "paper_and_cards" / "book-flip-1.mp3"
sfx_shove = VIRAL_SFX_DIR / "paper_and_cards" / "card-shove-1.mp3"
sfx_coins = VIRAL_SFX_DIR / "bells_and_chimes" / "handle-coins.mp3"
sfx_click = VIRAL_SFX_DIR / "clicks" / "click-soft.mp3"
sfx_place1 = VIRAL_SFX_DIR / "paper_and_cards" / "card-place-1.mp3"
sfx_whoosh = PROCEDURAL_SFX_DIR / "whoosh.wav"
sfx_close = VIRAL_SFX_DIR / "paper_and_cards" / "book-close.mp3"
sfx_slide2 = VIRAL_SFX_DIR / "paper_and_cards" / "card-slide-2.mp3"
sfx_chime = VIRAL_SFX_DIR / "bells_and_chimes" / "success-chime.mp3"

# Inputs:
# 0: SOURCE_VIDEO (CONTINUOUS, NEVER CUT/SEEKED -> ZERO LIP SYNC LATENCY!)
# 1: top_track_video (top half Flow clips)
# 2: flow_exp_vault
# 3: flow_exp_scale
# 4: flow_exp_crowd
# 5: flow_exp_bankrun
# 6: flow_exp_domino
# 7..17: SFX tracks

filter_complex = (
    # [A] Presenter Streams (Zero-Seek from 0:v -> 100% Lip Sync Accurate)
    "[0:v]scale=1080:1920,crop=1080:960:0:380,fps=30[char_bot];"
    "[0:v]scale=1242:2208,crop=1080:1920:81:144,fps=30[char_full];"
    
    # [B] Top Track (1080x960)
    "[1:v]scale=1080:960,fps=30[top_track];"
    
    # [C] Build Split Base (1080x1920)
    "[top_track][char_bot]vstack=inputs=2[raw_split];"
    "[raw_split]drawbox=x=0:y=958:w=1080:h=4:color=#1A1A1A@0.85:t=fill[base_split];"
    
    # [D] Full Explainer Clips (1080x1920)
    "[2:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setpts=PTS-STARTPTS[exp_vault];"
    "[3:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setpts=PTS-STARTPTS[exp_scale];"
    "[4:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setpts=PTS-STARTPTS[exp_crowd];"
    "[5:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setpts=PTS-STARTPTS[exp_bankrun];"
    "[6:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setpts=PTS-STARTPTS[exp_domino];"
    
    # [E] Sample-Accurate Layout Overlays across 55.10s Timeline
    # 04.70 - 06.78s: FULL_EXPLAINER Vault (exp_vault)
    "[base_split][exp_vault]overlay=0:0:enable='between(t,4.70,6.78)'[s1];"
    # 06.78 - 07.88s: FULL_CHARACTER Presenter (char_full)
    "[s1][char_full]overlay=0:0:enable='between(t,6.78,7.88)'[s2];"
    # 12.48 - 15.52s: FULL_EXPLAINER Scale (exp_scale)
    "[s2][exp_scale]overlay=0:0:enable='between(t,12.48,15.52)'[s3];"
    # 15.52 - 16.90s: FULL_CHARACTER Presenter (char_full)
    "[s3][char_full]overlay=0:0:enable='between(t,15.52,16.90)'[s4];"
    # 22.66 - 26.68s: FULL_CHARACTER Presenter (char_full)
    "[s4][char_full]overlay=0:0:enable='between(t,22.66,26.68)'[s5];"
    # 26.68 - 31.70s: FULL_EXPLAINER Crowd Queue (exp_crowd)
    "[s5][exp_crowd]overlay=0:0:enable='between(t,26.68,31.70)'[s6];"
    # 35.58 - 37.80s: FULL_EXPLAINER Bank Run Stamp (exp_bankrun)
    "[s6][exp_bankrun]overlay=0:0:enable='between(t,35.58,37.80)'[s7];"
    # 37.80 - 41.14s: FULL_EXPLAINER Dominoes Toppling (exp_domino)
    "[s7][exp_domino]overlay=0:0:enable='between(t,37.80,41.14)'[s8];"
    # 45.18 - 48.48s: FULL_CHARACTER Presenter (char_full)
    "[s8][char_full]overlay=0:0:enable='between(t,45.18,48.48)'[s9];"
    
    # Studio Color Grade
    "[s9]eq=contrast=1.06:brightness=0.01:saturation=1.10[v_out];"
    
    # [F] 16-Event Foley Audio Hierarchy (Zero Delay Distortion)
    "[7:a]adelay=0|0,volume=0.85[a0];"               # 00.00s: card-slide-1
    "[8:a]adelay=2180|2180,volume=0.8[a1];"          # 02.18s: card-place-1
    "[9:a]adelay=4700|4700,volume=0.8[a2];"          # 04.70s: switch-001
    "[10:a]adelay=6780|6780,volume=0.8[a3];"         # 06.78s: click-soft
    "[11:a]adelay=7880|7880,volume=0.8[a4];"         # 07.88s: book-flip-1
    "[12:a]adelay=10160|10160,volume=0.85[a5];"      # 10.16s: card-shove-1
    "[13:a]adelay=12480|12480,volume=0.85[a6];"      # 12.48s: handle-coins
    "[11:a]adelay=16900|16900,volume=0.85[a7];"      # 16.90s: book-flip-1
    "[10:a]adelay=20820|20820,volume=0.8[a8];"       # 20.82s: click-soft
    "[7:a]adelay=26680|26680,volume=0.85[a9];"       # 26.68s: card-slide-1
    "[14:a]adelay=31700|31700,volume=0.75[a10];"     # 31.70s: whoosh
    "[15:a]adelay=35580|35580,volume=0.8[a11];"      # 35.58s: book-close
    "[14:a]adelay=37800|37800,volume=0.8[a12];"      # 37.80s: whoosh
    "[16:a]adelay=45180|45180,volume=0.85[a13];"     # 45.18s: card-slide-2
    "[8:a]adelay=48480|48480,volume=0.85[a14];"      # 48.48s: card-place-1
    "[17:a]adelay=51460|51460,volume=0.9[a15];"      # 51.46s: success-chime
    
    # Direct Mix with Continuous 0:a dialogue
    "[0:a][a0][a1][a2][a3][a4][a5][a6][a7][a8][a9][a10][a11][a12][a13][a14][a15]amix=inputs=17:duration=first:dropout_transition=0,loudnorm=I=-14:LRA=7:TP=-1.5[a_out]"
)

final_cmd = [
    FFMPEG, "-y",
    "-i", str(SOURCE_VIDEO),
    "-i", str(top_track_video),
    "-stream_loop", "-1", "-i", str(flow_exp_vault),
    "-stream_loop", "-1", "-i", str(flow_exp_scale),
    "-stream_loop", "-1", "-i", str(flow_exp_crowd),
    "-stream_loop", "-1", "-i", str(flow_exp_bankrun),
    "-stream_loop", "-1", "-i", str(flow_exp_domino),
    "-i", str(sfx_slide1),
    "-i", str(sfx_place1),
    "-i", str(sfx_switch1),
    "-i", str(sfx_click),
    "-i", str(sfx_flip1),
    "-i", str(sfx_shove),
    "-i", str(sfx_coins),
    "-i", str(sfx_whoosh),
    "-i", str(sfx_close),
    "-i", str(sfx_slide2),
    "-i", str(sfx_chime),
    "-filter_complex", filter_complex,
    "-map", "[v_out]",
    "-map", "[a_out]",
    "-c:v", "libx264",
    "-preset", "fast",
    "-crf", "18",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-b:a", "192k",
    "-t", "55.10",
    str(OUTPUT_VIDEO)
]

subprocess.run(final_cmd, check=True)
logger.info(f"Synthesized Perfect Zero-Latency Master Video: {OUTPUT_VIDEO}")

# Copy to deliverable locations & artifacts
shutil.copy2(OUTPUT_VIDEO, DELIVERABLE_COPY)
art_dir = Path(r"C:\Users\HPUSER\.gemini\antigravity\brain\511882d1-5377-47fa-86e8-4adac25cec42")
shutil.copy2(OUTPUT_VIDEO, art_dir / "bankrun_zero_latency_master.mp4")

logger.info(f"SUCCESS: Zero-Latency Master Video saved to {OUTPUT_VIDEO} ({OUTPUT_VIDEO.stat().st_size / (1024*1024):.2f} MB)")

import logging
import os
import subprocess
import shutil
from pathlib import Path
from imageio_ffmpeg import get_ffmpeg_exe

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SegmentedFlowMasterSynthesizer")

FFMPEG = get_ffmpeg_exe()
WORKSPACE = Path(__file__).resolve().parent.parent
SEGMENTS_DIR = WORKSPACE / "storage" / "deliverables" / "0826_3_bankrun_master" / "segments"
SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_VIDEO = Path(r"D:\Downloads\0826 (3).mp4")
OUTPUT_VIDEO = WORKSPACE / "storage" / "deliverables" / "0826_3_bankrun_master" / "edited.mp4"
DELIVERABLE_COPY = WORKSPACE / "storage" / "deliverables" / "0824-varun-mayya-style" / "edited.mp4"
FLOW_DIR = WORKSPACE / "renderer" / "public" / "flow_videos"
VIRAL_SFX_DIR = WORKSPACE / "storage" / "assets" / "viral_sfx_library"
PROCEDURAL_SFX_DIR = WORKSPACE / "storage" / "deliverables" / "0824-certified-master" / "assets" / "sfx"

# Google Flow AI Videos
flow_passbook = FLOW_DIR / "flow_passbook_10lakh.mp4"
flow_vault = FLOW_DIR / "flow_vault_reality.mp4"
flow_scale = FLOW_DIR / "flow_liquidity_scale.mp4"
flow_car = FLOW_DIR / "vox_moving_car.mp4"
flow_crowd = FLOW_DIR / "flow_crowd_queue.mp4"
flow_bankrun = FLOW_DIR / "flow_bankrun_panic.mp4"

# 22-Beat Segment Definitions
BEATS = [
  # 01: Hook (0.00s - 4.70s) -> SPLIT: flow_passbook + Presenter
  {"start": 0.00, "dur": 4.70, "type": "SPLIT", "flow": flow_passbook},
  # 02: Vault Reality (4.70s - 7.88s) -> FULL_EXPLAINER: flow_vault
  {"start": 4.70, "dur": 3.18, "type": "FULL_EXPLAINER", "flow": flow_vault},
  # 03: Fractional Reserve (7.88s - 12.48s) -> SPLIT: flow_scale + Presenter
  {"start": 7.88, "dur": 4.60, "type": "SPLIT", "flow": flow_scale},
  # 04: Liquidity Scale (12.48s - 16.90s) -> FULL_EXPLAINER: flow_scale
  {"start": 12.48, "dur": 4.42, "type": "FULL_EXPLAINER", "flow": flow_scale},
  # 05: The Ledger / Capital (16.90s - 22.66s) -> SPLIT: flow_car + Presenter
  {"start": 16.90, "dur": 5.76, "type": "SPLIT", "flow": flow_car},
  # 06: Presenter Realization (22.66s - 26.68s) -> FULL_CHARACTER
  {"start": 22.66, "dur": 4.02, "type": "FULL_CHARACTER"},
  # 07: Mob Queue 1930 (26.68s - 31.70s) -> FULL_EXPLAINER: flow_crowd
  {"start": 26.68, "dur": 5.02, "type": "FULL_EXPLAINER", "flow": flow_crowd},
  # 08: Bank Run Panic (31.70s - 37.80s) -> SPLIT: flow_bankrun + Presenter
  {"start": 31.70, "dur": 6.10, "type": "SPLIT", "flow": flow_bankrun},
  # 09: Systemic Collapse (37.80s - 45.18s) -> FULL_EXPLAINER: flow_bankrun
  {"start": 37.80, "dur": 7.38, "type": "FULL_EXPLAINER", "flow": flow_bankrun},
  # 10: Presenter Truth (45.18s - 51.46s) -> FULL_CHARACTER
  {"start": 45.18, "dur": 6.28, "type": "FULL_CHARACTER"},
  # 11: Trust & Finale (51.46s - 55.10s) -> SPLIT: flow_vault + Presenter
  {"start": 51.46, "dur": 3.64, "type": "SPLIT", "flow": flow_vault},
]

segment_files = []
logger.info(f"[1/3] Rendering {len(BEATS)} Segments with Google Flow AI Videos...")

for idx, b in enumerate(BEATS):
    seg_path = SEGMENTS_DIR / f"seg_{idx:02d}.mp4"
    segment_files.append(seg_path)
    
    t_start = b["start"]
    t_dur = b["dur"]
    b_type = b["type"]
    
    if b_type == "SPLIT":
        flow_v = b["flow"]
        fc = (
            f"[1:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,fps=30,setpts=PTS-STARTPTS[top];"
            f"[0:v]scale=1080:1920,crop=1080:960:0:380,fps=30,setpts=PTS-STARTPTS[bot];"
            f"[top][bot]vstack=inputs=2[raw];"
            f"[raw]drawbox=x=0:y=958:w=1080:h=4:color=#1A1A1A@0.85:t=fill,eq=contrast=1.06:brightness=0.01:saturation=1.10[out]"
        )
        cmd = [
            FFMPEG, "-y",
            "-ss", str(t_start), "-t", str(t_dur), "-i", str(SOURCE_VIDEO),
            "-stream_loop", "-1", "-t", str(t_dur), "-i", str(flow_v),
            "-filter_complex", fc,
            "-map", "[out]",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p",
            str(seg_path)
        ]
    elif b_type == "FULL_EXPLAINER":
        flow_v = b["flow"]
        fc = f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,eq=contrast=1.06:brightness=0.01:saturation=1.10,setpts=PTS-STARTPTS[out]"
        cmd = [
            FFMPEG, "-y",
            "-stream_loop", "-1", "-t", str(t_dur), "-i", str(flow_v),
            "-filter_complex", fc,
            "-map", "[out]",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p",
            str(seg_path)
        ]
    elif b_type == "FULL_CHARACTER":
        fc = f"[0:v]scale=1242:2208,crop=1080:1920:81:144,fps=30,eq=contrast=1.06:brightness=0.01:saturation=1.10,setpts=PTS-STARTPTS[out]"
        cmd = [
            FFMPEG, "-y",
            "-ss", str(t_start), "-t", str(t_dur), "-i", str(SOURCE_VIDEO),
            "-filter_complex", fc,
            "-map", "[out]",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p",
            str(seg_path)
        ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    logger.info(f" -> Segment {idx+1}/{len(BEATS)} ({b_type} {t_dur}s) rendered!")

# 2. Concat Segments
logger.info("[2/3] Concatenating Video Segments...")
concat_list = SEGMENTS_DIR / "concat_list.txt"
concat_list.write_text("\n".join([f"file '{s.name}'" for s in segment_files]) + "\n", encoding="ascii")

raw_visual = SEGMENTS_DIR / "raw_visual.mp4"
subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(raw_visual)], check=True)

# 3. Foley SFX & Audio Mastering
logger.info("[3/3] Mixing Dialogue with 19 Foley SFX tracks and Loudnorm mastering...")
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

audio_fc = (
    "[1:a]adelay=0|0,volume=0.85[a0];"
    "[2:a]adelay=4700|4700,volume=0.8[a1];"
    "[3:a]adelay=7880|7880,volume=0.8[a2];"
    "[4:a]adelay=12480|12480,volume=0.85[a3];"
    "[5:a]adelay=16900|16900,volume=0.85[a4];"
    "[6:a]adelay=22660|22660,volume=0.8[a5];"
    "[7:a]adelay=26680|26680,volume=0.85[a6];"
    "[8:a]adelay=31700|31700,volume=0.75[a7];"
    "[9:a]adelay=37800|37800,volume=0.8[a8];"
    "[10:a]adelay=45180|45180,volume=0.85[a9];"
    "[11:a]adelay=51460|51460,volume=0.9[a10];"
    "[0:a][a0][a1][a2][a3][a4][a5][a6][a7][a8][a9][a10]amix=inputs=12:duration=first:dropout_transition=0,loudnorm=I=-14:LRA=7:TP=-1.5[a_out]"
)

final_cmd = [
    FFMPEG, "-y",
    "-i", str(SOURCE_VIDEO),
    "-i", str(sfx_slide1),
    "-i", str(sfx_switch1),
    "-i", str(sfx_flip1),
    "-i", str(sfx_shove),
    "-i", str(sfx_coins),
    "-i", str(sfx_click),
    "-i", str(sfx_place1),
    "-i", str(sfx_whoosh),
    "-i", str(sfx_close),
    "-i", str(sfx_slide2),
    "-i", str(sfx_chime),
    "-i", str(raw_visual),
    "-filter_complex", audio_fc,
    "-map", "12:v",
    "-map", "[a_out]",
    "-c:v", "copy",
    "-c:a", "aac",
    "-b:a", "192k",
    "-t", "55.10",
    str(OUTPUT_VIDEO)
]

subprocess.run(final_cmd, check=True)
logger.info(f"Synthesized Master Video: {OUTPUT_VIDEO}")

# Copy to deliverable locations & artifacts
shutil.copy2(OUTPUT_VIDEO, DELIVERABLE_COPY)
art_dir = Path(r"C:\Users\HPUSER\.gemini\antigravity\brain\511882d1-5377-47fa-86e8-4adac25cec42")
shutil.copy2(OUTPUT_VIDEO, art_dir / "bankrun_flow_ai_master.mp4")

logger.info(f"SUCCESS: Final Master Video saved to {OUTPUT_VIDEO} ({OUTPUT_VIDEO.stat().st_size / (1024*1024):.2f} MB)")

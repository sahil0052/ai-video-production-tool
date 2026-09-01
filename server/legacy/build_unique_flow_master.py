import logging
import os
import subprocess
import shutil
from pathlib import Path
from imageio_ffmpeg import get_ffmpeg_exe

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("UniqueFlowMasterSynthesizer")

FFMPEG = get_ffmpeg_exe()
WORKSPACE = Path(__file__).resolve().parent.parent
SEGMENTS_DIR = WORKSPACE / "storage" / "deliverables" / "0826_3_bankrun_master" / "unique_segments"
SEGMENTS_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_VIDEO = Path(r"D:\Downloads\0826 (3).mp4")
OUTPUT_VIDEO = WORKSPACE / "storage" / "deliverables" / "0826_3_bankrun_master" / "edited.mp4"
DELIVERABLE_COPY = WORKSPACE / "storage" / "deliverables" / "0824-varun-mayya-style" / "edited.mp4"
FLOW_DIR = WORKSPACE / "renderer" / "public" / "flow_videos"
VIRAL_SFX_DIR = WORKSPACE / "storage" / "assets" / "viral_sfx_library"
PROCEDURAL_SFX_DIR = WORKSPACE / "storage" / "deliverables" / "0824-certified-master" / "assets" / "sfx"

# 1-to-1 Unique Semantic Scene Definitions across 55.10s
SCENES = [
  # 01: [00.00 - 02.18s] (2.18s) -> SPLIT: flow_passbook_10lakh (Passbook ₹10 Lakh)
  {"start": 0.00, "dur": 2.18, "type": "SPLIT", "flow": FLOW_DIR / "flow_passbook_10lakh.mp4"},
  # 02: [02.18 - 04.70s] (2.52s) -> SPLIT: flow_crowd_running_counter (Depositors rush to counter)
  {"start": 2.18, "dur": 2.52, "type": "SPLIT", "flow": FLOW_DIR / "flow_crowd_running_counter.mp4"},
  # 03: [04.70 - 06.78s] (2.08s) -> FULL_EXPLAINER: flow_vault_reality (Empty Vault - ONLY ONCE!)
  {"start": 4.70, "dur": 2.08, "type": "FULL_EXPLAINER", "flow": FLOW_DIR / "flow_vault_reality.mp4"},
  # 04: [06.78 - 07.88s] (1.10s) -> FULL_CHARACTER: Presenter Punch (The Twist)
  {"start": 6.78, "dur": 1.10, "type": "FULL_CHARACTER"},
  # 05: [07.88 - 10.16s] (2.28s) -> SPLIT: flow_padlock_safe_loan (Locker turns into loan files)
  {"start": 7.88, "dur": 2.28, "type": "SPLIT", "flow": FLOW_DIR / "flow_padlock_safe_loan.mp4"},
  # 06: [10.16 - 12.48s] (2.32s) -> SPLIT: flow_circulation_diagram (Money circulation loop)
  {"start": 10.16, "dur": 2.32, "type": "SPLIT", "flow": FLOW_DIR / "flow_circulation_diagram.mp4"},
  # 07: [12.48 - 15.52s] (3.04s) -> FULL_EXPLAINER: flow_liquidity_scale (Balance Scale Overload - ONLY ONCE!)
  {"start": 12.48, "dur": 3.04, "type": "FULL_EXPLAINER", "flow": FLOW_DIR / "flow_liquidity_scale.mp4"},
  # 08: [15.52 - 16.90s] (1.38s) -> FULL_CHARACTER: Presenter Reaction
  {"start": 15.52, "dur": 1.38, "type": "FULL_CHARACTER"},
  # 09: [16.90 - 20.82s] (3.92s) -> SPLIT: flow_hundred_depositors (100 Depositors Grid)
  {"start": 16.90, "dur": 3.92, "type": "SPLIT", "flow": FLOW_DIR / "flow_hundred_depositors.mp4"},
  # 10: [20.82 - 22.66s] (1.84s) -> SPLIT: flow_ledger_one_crore (Ledger Total 1 Crore)
  {"start": 20.82, "dur": 1.84, "type": "SPLIT", "flow": FLOW_DIR / "flow_ledger_one_crore.mp4"},
  # 11: [22.66 - 26.68s] (4.02s) -> FULL_CHARACTER: Presenter (The Demand)
  {"start": 22.66, "dur": 4.02, "type": "FULL_CHARACTER"},
  # 12: [26.68 - 31.70s] (5.02s) -> FULL_EXPLAINER: flow_crowd_queue (1930s Mob Queue Demanding Cash)
  {"start": 26.68, "dur": 5.02, "type": "FULL_EXPLAINER", "flow": FLOW_DIR / "flow_crowd_queue.mp4"},
  # 13: [31.70 - 35.58s] (3.88s) -> SPLIT: flow_panicked_banker (Sweating Bank Manager Empty Drawer)
  {"start": 31.70, "dur": 3.88, "type": "SPLIT", "flow": FLOW_DIR / "flow_panicked_banker.mp4"},
  # 14: [35.58 - 37.80s] (2.22s) -> FULL_EXPLAINER: flow_bankrun_panic (BANK RUN Headline Stamp)
  {"start": 35.58, "dur": 2.22, "type": "FULL_EXPLAINER", "flow": FLOW_DIR / "flow_bankrun_panic.mp4"},
  # 15: [37.80 - 41.14s] (3.34s) -> FULL_EXPLAINER: flow_domino_toppling (Bank Dominoes Falling)
  {"start": 37.80, "dur": 3.34, "type": "FULL_EXPLAINER", "flow": FLOW_DIR / "flow_domino_toppling.mp4"},
  # 16: [41.14 - 45.18s] (4.04s) -> SPLIT: flow_panic_contagion_map (Panic Spreading Across Network)
  {"start": 41.14, "dur": 4.04, "type": "SPLIT", "flow": FLOW_DIR / "flow_panic_contagion_map.mp4"},
  # 17: [45.18 - 48.48s] (3.30s) -> FULL_CHARACTER: Presenter (Problem of TRUST)
  {"start": 45.18, "dur": 3.30, "type": "FULL_CHARACTER"},
  # 18: [48.48 - 51.46s] (2.98s) -> SPLIT: flow_trust_shield (Trust & Liquidity Golden Shield)
  {"start": 48.48, "dur": 2.98, "type": "SPLIT", "flow": FLOW_DIR / "flow_trust_shield.mp4"},
  # 19: [51.46 - 55.10s] (3.64s) -> SPLIT: flow_follow_trading (Ascending Candlestick & Follow CTA)
  {"start": 51.46, "dur": 3.64, "type": "SPLIT", "flow": FLOW_DIR / "flow_follow_trading.mp4"},
]

segment_files = []
logger.info(f"[1/3] Rendering {len(SCENES)} 100% Unique Segments with Google Flow AI Videos...")

for idx, b in enumerate(SCENES):
    seg_path = SEGMENTS_DIR / f"unique_seg_{idx:02d}.mp4"
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
    logger.info(f" -> Segment {idx+1}/{len(SCENES)} ({b_type} {t_dur:.2f}s) rendered!")

# 2. Concat Segments
logger.info("[2/3] Concatenating 100% Unique Video Segments...")
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
    "[1:a]adelay=0|0,volume=0.85[a0];"               # 00.00s: card-slide-1
    "[2:a]adelay=2180|2180,volume=0.8[a1];"          # 02.18s: card-place-1
    "[3:a]adelay=4700|4700,volume=0.8[a2];"          # 04.70s: switch-001
    "[4:a]adelay=6780|6780,volume=0.8[a3];"          # 06.78s: click-soft
    "[5:a]adelay=7880|7880,volume=0.8[a4];"          # 07.88s: book-flip-1
    "[6:a]adelay=10160|10160,volume=0.85[a5];"       # 10.16s: card-shove-1
    "[7:a]adelay=12480|12480,volume=0.85[a6];"       # 12.48s: handle-coins
    "[8:a]adelay=16900|16900,volume=0.85[a7];"       # 16.90s: book-flip-1
    "[9:a]adelay=20820|20820,volume=0.8[a8];"        # 20.82s: click-soft
    "[10:a]adelay=26680|26680,volume=0.85[a9];"      # 26.68s: card-slide-1
    "[11:a]adelay=31700|31700,volume=0.75[a10];"     # 31.70s: whoosh
    "[12:a]adelay=35580|35580,volume=0.8[a11];"      # 35.58s: book-close
    "[13:a]adelay=37800|37800,volume=0.8[a12];"      # 37.80s: whoosh
    "[14:a]adelay=45180|45180,volume=0.85[a13];"     # 45.18s: card-slide-2
    "[15:a]adelay=48480|48480,volume=0.85[a14];"     # 48.48s: card-place-1
    "[16:a]adelay=51460|51460,volume=0.9[a15];"      # 51.46s: success-chime
    "[0:a][a0][a1][a2][a3][a4][a5][a6][a7][a8][a9][a10][a11][a12][a13][a14][a15]amix=inputs=17:duration=first:dropout_transition=0,loudnorm=I=-14:LRA=7:TP=-1.5[a_out]"
)

final_cmd = [
    FFMPEG, "-y",
    "-i", str(SOURCE_VIDEO),
    "-i", str(sfx_slide1),
    "-i", str(sfx_place1),
    "-i", str(sfx_switch1),
    "-i", str(sfx_click),
    "-i", str(sfx_flip1),
    "-i", str(sfx_shove),
    "-i", str(sfx_coins),
    "-i", str(sfx_flip1),
    "-i", str(sfx_click),
    "-i", str(sfx_slide1),
    "-i", str(sfx_whoosh),
    "-i", str(sfx_close),
    "-i", str(sfx_whoosh),
    "-i", str(sfx_slide2),
    "-i", str(sfx_place1),
    "-i", str(sfx_chime),
    "-i", str(raw_visual),
    "-filter_complex", audio_fc,
    "-map", "17:v",
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
shutil.copy2(OUTPUT_VIDEO, art_dir / "bankrun_unique_flow_master.mp4")

logger.info(f"SUCCESS: 100% Unique Master Video saved to {OUTPUT_VIDEO} ({OUTPUT_VIDEO.stat().st_size / (1024*1024):.2f} MB)")

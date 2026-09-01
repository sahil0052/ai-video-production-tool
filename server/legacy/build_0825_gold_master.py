import logging
import os
import subprocess
import shutil
from pathlib import Path
from imageio_ffmpeg import get_ffmpeg_exe

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("GoldZeroLatencyMasterSynthesizer")

FFMPEG = get_ffmpeg_exe()
WORKSPACE = Path(__file__).resolve().parent.parent
DELIVERABLE_DIR = WORKSPACE / "storage" / "deliverables" / "0825_master"
DELIVERABLE_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_VIDEO = Path(r"D:\Downloads\0825.mp4")
OUTPUT_VIDEO = DELIVERABLE_DIR / "edited.mp4"
DELIVERABLE_COPY = WORKSPACE / "storage" / "deliverables" / "0824-varun-mayya-style" / "edited.mp4"
FLOW_DIR = WORKSPACE / "renderer" / "public" / "flow_videos"
VIRAL_SFX_DIR = WORKSPACE / "storage" / "assets" / "viral_sfx_library"
PROCEDURAL_SFX_DIR = WORKSPACE / "storage" / "deliverables" / "0824-certified-master" / "assets" / "sfx"

# 1. Build Top-Half Continuous 51.85s 1080x960 Flow Video Track
top_segments_dir = DELIVERABLE_DIR / "top_segments"
top_segments_dir.mkdir(parents=True, exist_ok=True)

TOP_BEATS = [
  # 01: [00.00 - 04.16s] (4.16s): gold01_ticker_seconds.mp4
  {"dur": 4.16, "flow": FLOW_DIR / "gold01_ticker_seconds.mp4"},
  # 02: [04.16 - 06.98s] (2.82s): black placeholder (covered by full character presenter)
  {"dur": 2.82, "flow": None},
  # 03: [06.98 - 09.38s] (2.40s): gold02_buyers_sellers_scale.mp4
  {"dur": 2.40, "flow": FLOW_DIR / "gold02_buyers_sellers_scale.mp4"},
  # 04: [09.38 - 11.70s] (2.32s): gold03_buyers_bidding_green.mp4
  {"dur": 2.32, "flow": FLOW_DIR / "gold03_buyers_bidding_green.mp4"},
  # 05: [11.70 - 13.60s] (1.90s): gold04_seller_price_tag.mp4
  {"dur": 1.90, "flow": FLOW_DIR / "gold04_seller_price_tag.mp4"},
  # 06: [13.60 - 15.04s] (1.44s): gold05_market_price_breakout.mp4
  {"dur": 1.44, "flow": FLOW_DIR / "gold05_market_price_breakout.mp4"},
  # 07: [15.04 - 16.18s] (1.14s): gold06_vintage_gold_shop.mp4
  {"dur": 1.14, "flow": FLOW_DIR / "gold06_vintage_gold_shop.mp4"},
  # 08: [16.18 - 18.36s] (2.18s): gold07_buyer_offer_7000.mp4
  {"dur": 2.18, "flow": FLOW_DIR / "gold07_buyer_offer_7000.mp4"},
  # 09: [18.36 - 19.44s] (1.08s): black placeholder (covered by full character presenter)
  {"dur": 1.08, "flow": None},
  # 10: [19.44 - 22.02s] (2.58s): gold08_bid_jumps_7050.mp4
  {"dur": 2.58, "flow": FLOW_DIR / "gold08_bid_jumps_7050.mp4"},
  # 11: [22.02 - 23.90s] (1.88s): gold09_seller_ask_increase.mp4
  {"dur": 1.88, "flow": FLOW_DIR / "gold09_seller_ask_increase.mp4"},
  # 12: [23.90 - 28.22s] (4.32s): black placeholder (covered by full explainer global network)
  {"dur": 4.32, "flow": None},
  # 13: [28.22 - 32.92s] (4.70s): gold11_institutional_trading.mp4
  {"dur": 4.70, "flow": FLOW_DIR / "gold11_institutional_trading.mp4"},
  # 14: [32.92 - 38.22s] (5.30s): black placeholder (covered by full explainer breaking news)
  {"dur": 5.30, "flow": None},
  # 15: [38.22 - 40.96s] (2.74s): black placeholder (covered by full character presenter)
  {"dur": 2.74, "flow": None},
  # 16: [40.96 - 47.14s] (6.18s): gold13_ai_trading_terminal.mp4
  {"dur": 6.18, "flow": FLOW_DIR / "gold13_ai_trading_terminal.mp4"},
  # 17: [47.14 - 51.85s] (4.71s): gold14_forex_follow_cta.mp4
  {"dur": 4.71, "flow": FLOW_DIR / "gold14_forex_follow_cta.mp4"},
]

top_seg_files = []
for idx, b in enumerate(TOP_BEATS):
    p = top_segments_dir / f"gold_top_{idx:02d}.mp4"
    top_seg_files.append(p)
    dur = b["dur"]
    flow_v = b["flow"]
    
    if flow_v and flow_v.exists():
        fc = f"[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960,fps=30,setpts=PTS-STARTPTS[out]"
        cmd = [FFMPEG, "-y", "-stream_loop", "-1", "-t", str(dur), "-i", str(flow_v), "-filter_complex", fc, "-map", "[out]", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p", str(p)]
    else:
        fc = f"color=c=black:s=1080x960:d={dur}:r=30[out]"
        cmd = [FFMPEG, "-y", "-filter_complex", fc, "-map", "[out]", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18", "-pix_fmt", "yuv420p", str(p)]
    
    subprocess.run(cmd, check=True, capture_output=True)

concat_top_txt = top_segments_dir / "concat_top.txt"
concat_top_txt.write_text("\n".join([f"file '{s.name}'" for s in top_seg_files]) + "\n", encoding="ascii")
top_track_video = DELIVERABLE_DIR / "top_flow_track.mp4"
subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_top_txt), "-c", "copy", str(top_track_video)], check=True)
logger.info(f"Rendered Gold Top Flow Track: {top_track_video}")

# 2. Full Explainer Videos
flow_exp_global = FLOW_DIR / "gold10_global_network.mp4"
flow_exp_news = FLOW_DIR / "gold12_breaking_news.mp4"

# 3. SFX Assets
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

# 4. Master Filter Complex (Continuous 0:v and 0:a -> 100% Zero Latency Lip Sync)
filter_complex = (
    # Presenter Streams
    "[0:v]scale=1080:1920,crop=1080:960:0:380,fps=30[char_bot];"
    "[0:v]scale=1242:2208,crop=1080:1920:81:144,fps=30[char_full];"
    
    # Top Track
    "[1:v]scale=1080:960,fps=30[top_track];"
    
    # Split Base
    "[top_track][char_bot]vstack=inputs=2[raw_split];"
    "[raw_split]drawbox=x=0:y=958:w=1080:h=4:color=#1A1A1A@0.85:t=fill[base_split];"
    
    # Full Explainer Clips
    "[2:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setpts=PTS-STARTPTS[exp_global];"
    "[3:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setpts=PTS-STARTPTS[exp_news];"
    
    # Layout State Transitions across 51.85s Timeline
    # 04.16 - 06.98s: FULL_CHARACTER Presenter (The Question)
    "[base_split][char_full]overlay=0:0:enable='between(t,4.16,6.98)'[s1];"
    # 18.36 - 19.44s: FULL_CHARACTER Presenter (Price wahi)
    "[s1][char_full]overlay=0:0:enable='between(t,18.36,19.44)'[s2];"
    # 23.90 - 28.22s: FULL_EXPLAINER Global Network (exp_global)
    "[s2][exp_global]overlay=0:0:enable='between(t,23.90,28.22)'[s3];"
    # 32.92 - 38.22s: FULL_EXPLAINER Breaking News (exp_news)
    "[s3][exp_news]overlay=0:0:enable='between(t,32.92,38.22)'[s4];"
    # 38.22 - 40.96s: FULL_CHARACTER Presenter (Sudden Volatility)
    "[s4][char_full]overlay=0:0:enable='between(t,38.22,40.96)'[s5];"
    
    # Studio Color Grade
    "[s5]eq=contrast=1.06:brightness=0.01:saturation=1.10[v_out];"
    
    # 16-Event Foley SFX Track Mixing
    "[4:a]adelay=0|0,volume=0.85[a0];"               # 00.00s: card-slide-1
    "[5:a]adelay=4160|4160,volume=0.8[a1];"          # 04.16s: click-soft
    "[6:a]adelay=6980|6980,volume=0.8[a2];"          # 06.98s: switch-001
    "[7:a]adelay=9380|9380,volume=0.85[a3];"         # 09.38s: card-shove-1
    "[8:a]adelay=11700|11700,volume=0.8[a4];"        # 11.70s: book-flip-1
    "[9:a]adelay=13600|13600,volume=0.8[a5];"        # 13.60s: whoosh
    "[10:a]adelay=15040|15040,volume=0.85[a6];"      # 15.04s: handle-coins
    "[11:a]adelay=16180|16180,volume=0.85[a7];"      # 16.18s: card-place-1
    "[5:a]adelay=18360|18360,volume=0.8[a8];"        # 18.36s: click-soft
    "[7:a]adelay=19440|19440,volume=0.85[a9];"       # 19.44s: card-shove-1
    "[8:a]adelay=22020|22020,volume=0.8[a10];"       # 22.02s: book-flip-1
    "[9:a]adelay=23900|23900,volume=0.85[a11];"      # 23.90s: whoosh
    "[10:a]adelay=28220|28220,volume=0.85[a12];"     # 28.22s: handle-coins
    "[12:a]adelay=32920|32920,volume=0.8[a13];"      # 32.92s: book-close
    "[5:a]adelay=38220|38220,volume=0.8[a14];"       # 38.22s: click-soft
    "[13:a]adelay=40960|40960,volume=0.85[a15];"     # 40.96s: card-slide-2
    "[14:a]adelay=47140|47140,volume=0.9[a16];"      # 47.14s: success-chime
    
    # Broadcast Dialogue Mix with -14.0 LUFS Loudnorm
    "[0:a][a0][a1][a2][a3][a4][a5][a6][a7][a8][a9][a10][a11][a12][a13][a14][a15][a16]amix=inputs=18:duration=first:dropout_transition=0,loudnorm=I=-14:LRA=7:TP=-1.5[a_out]"
)

final_cmd = [
    FFMPEG, "-y",
    "-i", str(SOURCE_VIDEO),
    "-i", str(top_track_video),
    "-stream_loop", "-1", "-i", str(flow_exp_global),
    "-stream_loop", "-1", "-i", str(flow_exp_news),
    "-i", str(sfx_slide1),
    "-i", str(sfx_click),
    "-i", str(sfx_switch1),
    "-i", str(sfx_shove),
    "-i", str(sfx_flip1),
    "-i", str(sfx_whoosh),
    "-i", str(sfx_coins),
    "-i", str(sfx_place1),
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
    "-t", "51.85",
    str(OUTPUT_VIDEO)
]

subprocess.run(final_cmd, check=True)
logger.info(f"Synthesized Gold Master Video: {OUTPUT_VIDEO}")

# Copy to deliverable locations & artifacts
shutil.copy2(OUTPUT_VIDEO, DELIVERABLE_COPY)
art_dir = Path(r"C:\Users\HPUSER\.gemini\antigravity\brain\511882d1-5377-47fa-86e8-4adac25cec42")
shutil.copy2(OUTPUT_VIDEO, art_dir / "gold_zero_latency_master.mp4")

logger.info(f"SUCCESS: Gold Master Video saved to {OUTPUT_VIDEO} ({OUTPUT_VIDEO.stat().st_size / (1024*1024):.2f} MB)")

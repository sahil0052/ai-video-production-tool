import subprocess, os, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import cv2, numpy as np
from imageio_ffmpeg import get_ffmpeg_exe

ffmpeg = get_ffmpeg_exe()
base_dir = Path(r"c:\websites\ai video production tool")
work_dir = base_dir / "storage" / "deliverables" / "voxpipe_0831_1_nishahomes"
work_dir.mkdir(parents=True, exist_ok=True)
art_dir = Path(r"C:\Users\HPUSER\.gemini\antigravity\brain\511882d1-5377-47fa-86e8-4adac25cec42")
logo_path = base_dir / "storage" / "assets" / "logos" / "nisha_homes_logo.png"
raw_video_path = Path(r"D:\Downloads\0831 (1).mp4")
master_audio_path = work_dir / "master_audio_track.wav"
output_master = work_dir / "edited.mp4"

print("--- STEP 1: PREPARING AUDIO (-14.0 LUFS) ---")
cmd_audio = [
    ffmpeg, "-y",
    "-i", str(raw_video_path),
    "-vn",
    "-af", "acompressor=threshold=-20dB:ratio=3.5:attack=15:release=150,volume=1.0,loudnorm=I=-14.0:TP=-1.5:LRA=7.0",
    "-ar", "48000",
    str(master_audio_path)
]
subprocess.run(cmd_audio, check=True)
print("Master Audio Ready:", master_audio_path)

# Load the 8 bespoke visual assets
img_price_trap = Image.open(art_dir / "nisha_v2_price_trap_169_1788178051992.jpg").convert("RGB")
img_location_916 = Image.open(art_dir / "nisha_v2_location_ncr_916_1788178074975.jpg").convert("RGB")
img_clubhouse_916 = Image.open(art_dir / "nisha_v2_resort_clubhouse_916_1788178095650.jpg").convert("RGB")
img_key_916 = Image.open(art_dir / "nisha_v2_golden_possession_916_1788178114840.jpg").convert("RGB")
img_ready_interior = Image.open(art_dir / "nisha_v2_ready_interior_169_1788178134328.jpg").convert("RGB")
img_advisory_table = Image.open(art_dir / "nisha_v2_advisory_table_169_1788178157666.jpg").convert("RGB")
img_ncr_skyline = Image.open(art_dir / "nisha_v2_ncr_skyline_hubs_916_1788178183076.jpg").convert("RGB")
img_end_backdrop = Image.open(art_dir / "nisha_v2_luxury_end_backdrop_916_1788178207657.jpg").convert("RGB")
logo_img = Image.open(logo_path).convert("RGBA")

print("All 8 bespoke visual assets loaded successfully!")

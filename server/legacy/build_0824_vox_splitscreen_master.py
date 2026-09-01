"""
Vox Split-Screen Production Master Builder (Top: Vox Diorama | Bottom: Raw Presenter)
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import wave
from pathlib import Path
from typing import Any

import cv2
from imageio_ffmpeg import get_ffmpeg_exe
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FFMPEG = get_ffmpeg_exe()
WORKSPACE = Path(__file__).resolve().parent.parent
OUTPUT_DIR = WORKSPACE / "storage" / "deliverables" / "0824-vox-splitscreen-master"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR = OUTPUT_DIR / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
VOX_IMAGES_DIR = WORKSPACE / "storage" / "assets" / "vox_scenes"
SFX_DIR = ASSETS_DIR / "sfx"
SFX_DIR.mkdir(parents=True, exist_ok=True)
VOX_CLIPS_DIR = ASSETS_DIR / "vox_clips"
VOX_CLIPS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# 1. PROCEDURAL SOUND EFFECTS GENERATOR (TACTILE PAPER & UI CUES)
# ============================================================================

def make_wav(path: Path, samples: np.ndarray, sr: int = 48000) -> None:
    samples = np.clip(samples, -1.0, 1.0)
    data = (samples * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        wav.writeframes(data.tobytes())


def generate_vox_sfx_suite() -> dict[str, Path]:
    sr = 48000
    sfx = {}

    # 1. Paper Stamp / Thud (0.0s)
    t = np.linspace(0, 0.6, int(sr * 0.6), False)
    thud = np.sin(2 * np.pi * (80 * np.exp(-t * 8) + 40) * t) * np.exp(-t * 10)
    crunch = np.random.uniform(-0.5, 0.5, len(t)) * np.exp(-t * 25)
    sfx["stamp_thud"] = SFX_DIR / "stamp_thud.wav"
    make_wav(sfx["stamp_thud"], thud * 0.8 + crunch * 0.35)

    # 2. Paper Thwip / Fast Air Whoosh (Transitions)
    t = np.linspace(0, 0.24, int(sr * 0.24), False)
    noise = np.random.uniform(-1, 1, len(t))
    env = np.sin(np.pi * t / 0.24) ** 2
    sfx["paper_whoosh"] = SFX_DIR / "paper_whoosh.wav"
    make_wav(sfx["paper_whoosh"], noise * env * 0.45)

    # 3. Mechanical Paper Pop / Snap ("Lekin Kyun?")
    t = np.linspace(0, 0.12, int(sr * 0.12), False)
    pop = np.sin(2 * np.pi * 1500 * t) * np.exp(-t * 45)
    sfx["paper_pop"] = SFX_DIR / "paper_pop.wav"
    make_wav(sfx["paper_pop"], pop * 0.7)

    # 4. Data / Stamp Tick (Predefined rules & capital)
    t = np.linspace(0, 0.05, int(sr * 0.05), False)
    tick = np.sin(2 * np.pi * 2600 * t) * np.exp(-t * 85)
    sfx["tick"] = SFX_DIR / "tick.wav"
    make_wav(sfx["tick"], tick * 0.6)

    # 5. Reverse Tension Riser (Leverage & Revenge)
    t = np.linspace(0, 0.8, int(sr * 0.8), False)
    rise_freq = 80 + 380 * (t / 0.8) ** 2.2
    rise = np.sin(2 * np.pi * rise_freq * t) * (t / 0.8) * 0.45
    sfx["riser"] = SFX_DIR / "riser.wav"
    make_wav(sfx["riser"], rise)

    # 6. Low Alert Drop (Drawdown spiral)
    t = np.linspace(0, 0.7, int(sr * 0.7), False)
    drop = np.sin(2 * np.pi * (160 * np.exp(-t * 4) + 40) * t) * np.exp(-t * 5) * 0.7
    sfx["alert_drop"] = SFX_DIR / "alert_drop.wav"
    make_wav(sfx["alert_drop"], drop)

    # 7. Follow Stamp Chime
    t = np.linspace(0, 0.5, int(sr * 0.5), False)
    c1 = np.sin(2 * np.pi * 1046.5 * t) * np.exp(-t * 6)
    c2 = np.sin(2 * np.pi * 1318.5 * t) * np.exp(-t * 6)
    sfx["chime"] = SFX_DIR / "chime.wav"
    make_wav(sfx["chime"], (c1 + c2) * 0.35)

    return sfx


# ============================================================================
# 2. PROCEDURAL 3D CAMERA MOTION FOR VOX SCENES (1080x960 CLIPS)
# ============================================================================

def create_vox_camera_motion_clip(
    image_path: Path,
    output_clip_path: Path,
    duration_sec: float,
    motion_type: str = "push_in",
    fps: int = 30
) -> None:
    """Animates a static Vox diorama image with dynamic 3D camera pan/zoom."""
    src_img = cv2.imread(str(image_path))
    if src_img is None:
        raise FileNotFoundError(image_path)

    orig_h, orig_w, _ = src_img.shape
    target_w, target_h = 1080, 960
    num_frames = int(duration_sec * fps)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_clip_path), fourcc, fps, (target_w, target_h))

    for f in range(num_frames):
        prog = f / max(1, num_frames - 1)
        
        # Smooth Bezier Easing
        ease = prog * prog * (3.0 - 2.0 * prog)

        if motion_type == "push_in":
            # Camera pushes in from 1.0x to 1.15x
            scale = 1.0 + 0.15 * ease
            cw, ch = int(orig_w / scale), int(orig_h / scale)
            x1 = int((orig_w - cw) / 2)
            y1 = int((orig_h - ch) / 2)
        elif motion_type == "pan_left":
            # Camera tracks laterally across the ledger
            scale = 1.08
            cw, ch = int(orig_w / scale), int(orig_h / scale)
            max_shift = orig_w - cw
            x1 = int(max_shift * (0.2 + 0.6 * ease))
            y1 = int((orig_h - ch) / 2)
        elif motion_type == "dive_down":
            # Camera cranes downward
            scale = 1.10
            cw, ch = int(orig_w / scale), int(orig_h / scale)
            max_shift = orig_h - ch
            x1 = int((orig_w - cw) / 2)
            y1 = int(max_shift * (0.1 + 0.7 * ease))
        else:
            scale = 1.05
            cw, ch = int(orig_w / scale), int(orig_h / scale)
            x1 = int((orig_w - cw) / 2)
            y1 = int((orig_h - ch) / 2)

        cropped = src_img[y1 : y1 + ch, x1 : x1 + cw]
        resized = cv2.resize(cropped, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
        out.write(resized)

    out.release()


# ============================================================================
# 3. KINETIC MONOSPACE SUBTITLES (LOWER-THIRD OF BOTTOM PRESENTER)
# ============================================================================

def build_vox_subtitles(ass_path: Path) -> None:
    sub_cues = [
        (0.00, 2.06, "Forex mein 90% TRADERS lose karte hain"),
        (2.06, 2.88, "Lekin KYUN?"),
        (2.88, 3.74, "Problem MARKET nahi..."),
        (3.74, 5.58, "Aksar trader ki apni MISTAKES hoti hain"),
        (5.58, 7.44, "Sabse pehli mistake hai RISK MANAGEMENT"),
        (7.44, 11.22, "Profit ke chakkar mein EK HI TRADE mein sara capital risk kar dete hain"),
        (11.22, 12.14, "Doosri hai LEVERAGE"),
        (12.14, 14.98, "Chhote capital se BADI POSITION control karna tempting lagta hai"),
        (14.98, 17.50, "Lekin market opposite jaaye toh LOSS FAST badhta hai"),
        (17.50, 19.64, "Teesri aur sabse common problem: EMOTIONS"),
        (19.64, 24.42, "Loss ke baad REVENGE TRADING aur overconfidence strategy destroy kar dete hain"),
        (24.42, 28.50, "Aur bina TESTED STRATEGY ke trading start karna major mistake hai"),
        (28.50, 34.52, "Isi liye traders EA USE karte hain jo predefined rules follow karta hai"),
        (34.52, 38.10, "Aise Forex aur EA concepts simple language mein samajhne hain toh FOLLOW KAR LO!")
    ]

    def fmt_time(sec: float) -> str:
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = sec % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Consolas,42,&H00FFFFFF,&H000000FF,&H000B1012,&HE00B1012,1,0,0,0,100,100,1,0,3,14,0,2,40,40,140,1",
        "Style: HighlightCyan,Consolas,44,&H0000E5FF,&H000000FF,&H000B1012,&HE00B1012,1,0,0,0,100,100,1,0,3,16,0,2,40,40,140,1",
        "Style: HighlightRed,Consolas,44,&H001F2ED6,&H000000FF,&H000B1012,&HE00B1012,1,0,0,0,100,100,1,0,3,16,0,2,40,40,140,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for start, end, text in sub_cues:
        words = text.split()
        page_size = 4
        num_pages = math.ceil(len(words) / page_size)
        dur = end - start
        page_dur = dur / max(1, num_pages)

        for p in range(num_pages):
            p_words = words[p * page_size : (p + 1) * page_size]
            p_text = " ".join(p_words)
            p_start = start + p * page_dur
            p_end = min(end, p_start + page_dur)

            if any(k in p_text.upper() for k in ["90%", "LOSE", "LEVERAGE", "REVENGE", "EA USE", "FOLLOW"]):
                style = "HighlightCyan"
            elif any(k in p_text.upper() for k in ["KYUN", "RISK", "MISTAKE", "CAPITAL", "EMOTIONS", "TESTED"]):
                style = "HighlightRed"
            else:
                style = "Default"

            lines.append(f"Dialogue: 0,{fmt_time(p_start)},{fmt_time(p_end)},{style},,0,0,0,,{p_text}")

    ass_path.write_text("\n".join(lines), encoding="utf-8")


# ============================================================================
# 4. MASTER SPLIT-SCREEN ASSEMBLY (TOP: VOX | BOTTOM: PRESENTER)
# ============================================================================

def build_split_screen_master() -> None:
    source_video = Path(r"D:\Downloads\0824.mp4")
    master_output = OUTPUT_DIR / "0824-vox-splitscreen-master.mp4"
    deliverable_copy = WORKSPACE / "storage" / "deliverables" / "0824-varun-mayya-style" / "edited.mp4"

    print("[Build] 1. Synthesizing Tactile Sound Effects Suite...")
    sfx = generate_vox_sfx_suite()

    # Define Scene Windows & Animated Camera Moves
    scenes = [
        ("scene1_hook.jpg", 5.58, "push_in"),
        ("scene2_risk.jpg", 5.64, "pan_left"),
        ("scene3_leverage.jpg", 6.28, "dive_down"),
        ("scene4_emotions.jpg", 11.00, "push_in"),
        ("scene5_ea.jpg", 6.02, "pan_left"),
        ("scene6_cta.jpg", 3.58, "push_in"),
    ]

    print("[Build] 2. Generating 6 Animated 3D Vox Camera Motion Video Clips (1080x960)...")
    vox_clip_paths = []
    for idx, (img_name, dur, motion) in enumerate(scenes):
        img_p = VOX_IMAGES_DIR / img_name
        clip_p = VOX_CLIPS_DIR / f"vox_clip_{idx+1:02d}.mp4"
        create_vox_camera_motion_clip(img_p, clip_p, duration_sec=dur, motion_type=motion)
        vox_clip_paths.append(clip_p)

    print("[Build] 3. Concatenating Top-Half Vox Diorama Stream...")
    # Concatenate all 6 vox clips into a continuous 38.1s top-half video
    concat_list_file = VOX_CLIPS_DIR / "concat_list.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for cp in vox_clip_paths:
            f.write(f"file '{str(cp).replace(os.sep, '/')}'\n")

    top_half_video = VOX_CLIPS_DIR / "vox_top_half_master.mp4"
    concat_cmd = [
        FFMPEG, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_file),
        "-c", "copy",
        str(top_half_video)
    ]
    subprocess.run(concat_cmd, check=True)

    print("[Build] 4. Building Kinetic Monospace Captions...")
    ass_path = OUTPUT_DIR / "captions.ass"
    build_vox_subtitles(ass_path)
    ass_filter_path = str(ass_path).replace("\\", "/").replace(":", "\\:")

    print("[Build] 5. Assembling Dual-Layer Split-Screen Master (1080x1920)...")
    
    # Filter Complex:
    # 0:v = Raw Presenter (D:\Downloads\0824.mp4)
    # 1:v = Top-Half Vox Master (vox_top_half_master.mp4: 1080x960)
    # 2..8 = SFX Cues
    filter_complex = (
        # Top-Half: Vox Animation (1080x960)
        f"[1:v]scale=1080:960,fps=30[v_top];"
        
        # Bottom-Half: Crop and scale presenter footage to exactly 1080x960
        f"[0:v]scale=1080:1920,crop=1080:960:0:380,fps=30[v_bottom];"
        
        # Stack vertically: Top (Y=0..960) + Bottom (Y=960..1920)
        f"[v_top][v_bottom]vstack=inputs=2[v_split];"
        
        # Draw Archival Border & Divider Line between top and bottom
        f"[v_split]drawbox=x=0:y=956:w=1080:h=8:color=#1A1A1A@1.0:t=fill[v_divided];"
        
        # Apply Studio Color Grade & Print Texture Accent
        f"[v_divided]eq=contrast=1.08:brightness=0.01:saturation=1.12[v_graded];"
        
        # Overlay Kinetic Monospace Captions on the bottom third
        f"[v_graded]ass='{ass_filter_path}'[v_out];"
        
        # Audio Mix: Presenter Dialogue (0:a) + 7 Tactile Sound Design Cues (2..8)
        f"[2:a]adelay=0|0,volume=0.85[sfx0];"         # Stamp Thud @ 0.0s
        f"[3:a]adelay=1800|1800,volume=0.7[sfx1];"   # Paper Whoosh @ 1.8s
        f"[4:a]adelay=2500|2500,volume=0.75[sfx2];"  # Pop Snap @ 2.5s ("Lekin Kyun?")
        f"[5:a]adelay=5580|5580,volume=0.7[sfx3];"   # Data Tick @ 5.58s (Risk)
        f"[6:a]adelay=11220|11220,volume=0.85[sfx4];"# Tension Riser @ 11.22s (Leverage)
        f"[7:a]adelay=19640|19640,volume=0.9[sfx5];" # Alert Drop @ 19.64s (Revenge Trading)
        f"[8:a]adelay=34520|34520,volume=0.85[sfx6];"# Chime @ 34.52s (Follow CTA)
        f"[0:a][sfx0][sfx1][sfx2][sfx3][sfx4][sfx5][sfx6]amix=inputs=8:duration=first:dropout_transition=2[a_mixed];"
        f"[a_mixed]loudnorm=I=-14:TP=-1.0:LRA=7[a_out]"
    )

    cmd = [
        FFMPEG,
        "-y",
        "-i", str(source_video),
        "-i", str(top_half_video),
        "-i", str(sfx["stamp_thud"]),
        "-i", str(sfx["paper_whoosh"]),
        "-i", str(sfx["paper_pop"]),
        "-i", str(sfx["tick"]),
        "-i", str(sfx["riser"]),
        "-i", str(sfx["alert_drop"]),
        "-i", str(sfx["chime"]),
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
        str(master_output)
    ]

    print("[Build] 6. Rendering Final Split-Screen 1080x1920 Master...")
    res = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if res.returncode != 0:
        print("Render Error:\n", res.stderr[-3000:])
        raise RuntimeError("Master rendering failed.")

    shutil.copy2(master_output, deliverable_copy)
    print(f"\nSUCCESS: Vox Split-Screen Master Render Complete!\nOutput: {master_output} ({master_output.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    build_split_screen_master()

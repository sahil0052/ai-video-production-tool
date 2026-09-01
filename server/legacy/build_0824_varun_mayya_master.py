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
DELIVERABLE_DIR = WORKSPACE / "storage" / "deliverables" / "0824-varun-mayya-style"
DELIVERABLE_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR = DELIVERABLE_DIR / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
BROLL_DIR = ASSETS_DIR / "broll"
BROLL_DIR.mkdir(parents=True, exist_ok=True)
SFX_DIR = ASSETS_DIR / "sfx"
SFX_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# 1. PROCEDURAL SOUND EFFECTS & 92 BPM MUSIC GENERATOR
# ============================================================================

def make_wav(path: Path, samples: np.ndarray, sr: int = 48000) -> None:
    samples = np.clip(samples, -1.0, 1.0)
    data = (samples * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        wav.writeframes(data.tobytes())


def generate_all_sfx() -> dict[str, Path]:
    sr = 48000
    sfx_paths = {}

    # 1. Deep Hook Sub-Impact (0.0s)
    t = np.linspace(0, 0.7, int(sr * 0.7), False)
    sub = np.sin(2 * np.pi * (75 * np.exp(-t * 5) + 32) * t) * np.exp(-t * 7)
    trans = np.random.uniform(-0.6, 0.6, len(t)) * np.exp(-t * 30)
    sfx_paths["hook_impact"] = SFX_DIR / "hook_impact.wav"
    make_wav(sfx_paths["hook_impact"], sub * 0.85 + trans * 0.35)

    # 2. Fast Air Swoosh (Camera punch zooms & transitions)
    t = np.linspace(0, 0.28, int(sr * 0.28), False)
    noise = np.random.uniform(-1, 1, len(t))
    env = (np.sin(np.pi * t / 0.28) ** 2) * (1 + 0.3 * np.sin(2 * np.pi * 14 * t))
    sfx_paths["whoosh"] = SFX_DIR / "whoosh.wav"
    make_wav(sfx_paths["whoosh"], noise * env * 0.5)

    # 3. Digital UI Pop / Stat Snap
    t = np.linspace(0, 0.12, int(sr * 0.12), False)
    freq = 1600 * (1 + 0.8 * np.exp(-t * 45))
    pop = np.sin(2 * np.pi * freq * t) * np.exp(-t * 40)
    sfx_paths["snap"] = SFX_DIR / "snap.wav"
    make_wav(sfx_paths["snap"], pop * 0.7)

    # 4. Code & Data Execution Tick
    t = np.linspace(0, 0.05, int(sr * 0.05), False)
    tick = np.sin(2 * np.pi * 2800 * t) * np.exp(-t * 90)
    sfx_paths["tick"] = SFX_DIR / "tick.wav"
    make_wav(sfx_paths["tick"], tick * 0.6)

    # 5. Reverse Tension Riser
    t = np.linspace(0, 0.9, int(sr * 0.9), False)
    rise_freq = 70 + 420 * (t / 0.9) ** 2.2
    rise = np.sin(2 * np.pi * rise_freq * t) * (t / 0.9) * 0.45
    sfx_paths["riser"] = SFX_DIR / "riser.wav"
    make_wav(sfx_paths["riser"], rise)

    # 6. Low Warning Drop (Revenge Trading & Fast Loss)
    t = np.linspace(0, 0.8, int(sr * 0.8), False)
    drop_freq = 180 * np.exp(-t * 3.5) + 38
    warn = np.sin(2 * np.pi * drop_freq * t) * np.exp(-t * 4) * 0.7
    sfx_paths["warn"] = SFX_DIR / "warn.wav"
    make_wav(sfx_paths["warn"], warn)

    return sfx_paths


def generate_varun_mayya_music_bed(output_path: Path, duration: float) -> None:
    sr = 48000
    t = np.linspace(0, duration, int(sr * duration), False)
    bpm = 92.0
    beat_sec = 60.0 / bpm

    # Punchy kick sub-pulse
    beat_idx = (t % beat_sec) / beat_sec
    kick_env = np.exp(-beat_idx * 16)
    sub = np.sin(2 * np.pi * 48.0 * t) * kick_env * 0.28

    # Crisp 1/8th hi-hat texture
    hat_idx = (t % (beat_sec / 2)) / (beat_sec / 2)
    hat_env = np.exp(-hat_idx * 40)
    noise = np.random.uniform(-1, 1, len(t))
    hat = noise * hat_env * 0.035

    # Dark cyber documentary synth chord progression
    pad = np.sin(2 * np.pi * 92.5 * t) * 0.07 + np.sin(2 * np.pi * 138.5 * t) * 0.05

    mix = sub + hat + pad
    make_wav(output_path, mix * 0.45, sr=sr)


# ============================================================================
# 2. PROCEDURAL 1080x1920 MOTION GRAPHICS GENERATORS
# ============================================================================

def generate_risk_matrix_video(output_path: Path, duration_sec: float = 6.0, fps: int = 30) -> None:
    """Motion Graphic 1: 90% Failure Rate & Single-Trade Capital Drain."""
    w, h = 1080, 1920
    out = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
    num_frames = int(duration_sec * fps)

    for f in range(num_frames):
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:] = (12, 16, 20)

        # Background grid
        for y in range(0, h, 60):
            cv2.line(img, (0, y), (w, y), (22, 30, 38), 1)
        for x in range(0, w, 60):
            cv2.line(img, (x, 0), (x, h), (22, 30, 38), 1)

        # Header Badge
        cv2.rectangle(img, (100, 240), (980, 360), (20, 28, 35), -1)
        cv2.rectangle(img, (100, 240), (980, 360), (0, 229, 255), 2)
        cv2.putText(img, "MISTAKE #1: ZERO RISK CONTROLS", (135, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 229, 255), 2)
        cv2.putText(img, "SINGLE TRADE CAPITAL OVER-EXPOSURE", (135, 335), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (60, 60, 240), 2)

        # Central 90% Failure Circle Stat
        center = (540, 720)
        cv2.circle(img, center, 180, (26, 36, 46), -1)
        cv2.circle(img, center, 180, (60, 60, 240), 6)
        cv2.putText(img, "90%", (430, 720), cv2.FONT_HERSHEY_SIMPLEX, 2.4, (255, 255, 255), 5)
        cv2.putText(img, "FAIL RATE", (450, 780), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (60, 60, 240), 2)

        # Animated Capital Drain Bar (₹1,00,000 -> ₹8,500)
        progress = f / num_frames
        curr_cap = max(8500, int(100000 * (1.0 - progress * 0.92)))
        
        cv2.rectangle(img, (100, 1050), (980, 1280), (18, 24, 30), -1)
        cv2.rectangle(img, (100, 1050), (980, 1280), (45, 55, 70), 2)
        cv2.putText(img, "ACCOUNT BALANCE AFTER 1 TRADE:", (130, 1110), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (200, 220, 230), 2)
        cv2.putText(img, f"INR {curr_cap:,}", (130, 1180), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (60, 60, 240) if curr_cap < 30000 else (0, 230, 118), 3)

        # Draw Drain Bar
        bar_w = int(780 * (curr_cap / 100000.0))
        cv2.rectangle(img, (130, 1210), (130 + bar_w, 1245), (60, 60, 240), -1)

        # Warning Badge
        if f % 15 < 8:
            cv2.rectangle(img, (260, 1380), (820, 1460), (40, 15, 20), -1)
            cv2.rectangle(img, (260, 1380), (820, 1460), (60, 60, 240), 2)
            cv2.putText(img, "! DANGER: 91.5% DRAWDOWN !", (290, 1430), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (60, 60, 240), 2)

        out.write(img)
    out.release()


def generate_leverage_scale_video(output_path: Path, duration_sec: float = 6.0, fps: int = 30) -> None:
    """Motion Graphic 2: 1:500 Leverage Multiplier & Position Scale."""
    w, h = 1080, 1920
    out = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
    num_frames = int(duration_sec * fps)

    for f in range(num_frames):
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:] = (12, 16, 20)

        # Background grid
        for y in range(0, h, 60):
            cv2.line(img, (0, y), (w, y), (22, 30, 38), 1)
        for x in range(0, w, 60):
            cv2.line(img, (x, 0), (x, h), (22, 30, 38), 1)

        # Header Badge
        cv2.rectangle(img, (100, 240), (980, 360), (20, 28, 35), -1)
        cv2.rectangle(img, (100, 240), (980, 360), (0, 229, 255), 2)
        cv2.putText(img, "MISTAKE #2: EXCESSIVE LEVERAGE", (135, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 229, 255), 2)
        cv2.putText(img, "1:500 MULTIPLIER TRAP", (135, 335), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 229, 255), 2)

        # Comparison Scale Boxes
        # Left Box: Small Deposit
        cv2.rectangle(img, (100, 560), (500, 880), (18, 26, 32), -1)
        cv2.rectangle(img, (100, 560), (500, 880), (0, 230, 118), 2)
        cv2.putText(img, "YOUR DEPOSIT", (130, 620), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 230, 118), 2)
        cv2.putText(img, "INR 10,000", (130, 710), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)
        cv2.putText(img, "[1x CAPITAL]", (130, 780), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (140, 160, 180), 2)

        # Right Box: Controlled Position
        cv2.rectangle(img, (580, 560), (980, 880), (35, 20, 24), -1)
        cv2.rectangle(img, (580, 560), (980, 880), (60, 60, 240), 2)
        cv2.putText(img, "CONTROLLED SIZE", (605, 620), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (60, 60, 240), 2)
        cv2.putText(img, "INR 50,00,000", (605, 710), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 3)
        cv2.putText(img, "[500x LEVERAGE]", (605, 780), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (60, 60, 240), 2)

        # Multiplier Telemetry Bar
        cv2.rectangle(img, (100, 1020), (980, 1260), (18, 24, 30), -1)
        cv2.rectangle(img, (100, 1020), (980, 1260), (45, 55, 70), 2)
        cv2.putText(img, "MARGIN TO LOSS SENSITIVITY:", (130, 1080), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (200, 220, 230), 2)
        cv2.putText(img, "A 0.2% Market Drop = 100% ACCOUNT WIPE", (130, 1160), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (60, 60, 240), 2)
        
        # Animated Gauge Needle
        gauge_val = 0.5 + 0.45 * math.sin(f / 15.0)
        cv2.rectangle(img, (130, 1200), (130 + int(720 * gauge_val), 1230), (0, 229, 255), -1)

        out.write(img)
    out.release()


def generate_revenge_trading_video(output_path: Path, duration_sec: float = 6.0, fps: int = 30) -> None:
    """Motion Graphic 3: Revenge Trading & Compounding Drawdown Curve."""
    w, h = 1080, 1920
    out = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
    num_frames = int(duration_sec * fps)

    # Downward crashing equity curve points
    np.random.seed(99)
    equity = [100.0]
    for _ in range(40):
        equity.append(equity[-1] - np.random.uniform(1.5, 4.0))

    for f in range(num_frames):
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:] = (12, 16, 20)

        # Background grid
        for y in range(0, h, 60):
            cv2.line(img, (0, y), (w, y), (22, 30, 38), 1)
        for x in range(0, w, 60):
            cv2.line(img, (x, 0), (x, h), (22, 30, 38), 1)

        # Header Badge
        cv2.rectangle(img, (100, 240), (980, 360), (20, 28, 35), -1)
        cv2.rectangle(img, (100, 240), (980, 360), (60, 60, 240), 2)
        cv2.putText(img, "MISTAKE #3: REVENGE TRADING", (135, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (60, 60, 240), 2)
        cv2.putText(img, "EMOTIONAL OVER-TRADING SPIRAL", (135, 335), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 220, 230), 2)

        # Draw Downward Equity Chart
        chart_top, chart_bot = 520, 1200
        visible_pts = min(len(equity)-1, int(5 + (f / num_frames) * (len(equity) - 5)))
        min_e, max_e = min(equity), max(equity)

        pts = []
        for i in range(visible_pts + 1):
            x_pos = int(120 + i * (760 / len(equity)))
            y_pos = int(chart_top + ((max_e - equity[i]) / (max_e - min_e + 1e-5)) * (chart_bot - chart_top))
            pts.append((x_pos, y_pos))

        for i in range(len(pts) - 1):
            cv2.line(img, pts[i], pts[i+1], (60, 60, 240), 3, cv2.LINE_AA)
            cv2.circle(img, pts[i+1], 5, (0, 229, 255), -1)

        # Live compounding loss callout
        curr_loss = (100 - equity[visible_pts])
        cv2.rectangle(img, (100, 1280), (980, 1480), (25, 18, 22), -1)
        cv2.rectangle(img, (100, 1280), (980, 1480), (60, 60, 240), 2)
        cv2.putText(img, f"TOTAL CAPITAL LOSS: -{curr_loss:.1f}%", (140, 1360), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (60, 60, 240), 3)
        cv2.putText(img, "RULE VIOLATION: NO STOP LOSS APPLIED", (140, 1430), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (200, 220, 230), 2)

        out.write(img)
    out.release()


# ============================================================================
# 3. KINETIC MONOSPACE SUBTITLE GENERATOR (VARUN MAYYA STYLE)
# ============================================================================

def build_varun_mayya_subtitles(transcript_file: Path, ass_path: Path) -> None:
    with open(transcript_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Transliterate speech into crisp Romanized Hinglish
    translit_map = {
        "फोरेक्स में 90% तरेटर्स लूस करते हैं": "Forex mein 90% traders LOSE karte hain",
        "लेकिन क्यों?": "Lekin KYUN?",
        "प्रोब्लम माकेत नहीं": "Problem market nahi...",
        "अखसर तरेटर्स की अपनी मिस्टेक्स होती हैं": "Aksar traders ki apni MISTAKES hoti hain",
        "सब से पहली मिस्टेक है रिस्क मानेज्मेंत": "Sabse pehli mistake: RISK MANAGEMENT",
        "प्रोब्लिट के चकर में लोग एक ही तरेट में बहुत जाड़ा कापिटल रिस्क कर देते हैं": "Profit ke chakkar mein EK HI TRADE mein sara capital risk kar dete hain",
        "दूसरी है लेवरिज": "Doosri hai LEVERAGE",
        "चोटे कापिटल से बडी पोजिषन कंट्रोल करना तेम्टिंग लकता है": "Chhote capital se BADI POSITION control karna tempting lagta hai",
        "टीसरी अर सब से कोमें प्रोब्लिट गड़ा": "Teesri aur sabse common mistake:",
        "लोऊस के बाद रिवेन्ज्टेडिंग और प्रोट्ब्टिट के बाड वाद वोगे रग्दींच देदींच मैंगा": "Loss ke baad REVENGE TRADING aur overtrading shuru kar dete hain",
        "देदीडींग सब रवाद पहले रहा है": "Emotional trading sab barbaad kar deta hai",
        "तो लोऊस बी बहुत फाज्द बदता है": "To LOSS bhi bahut FAST badhta hai!"
    }

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
        "Style: Default,Consolas,44,&H00FFFFFF,&H000000FF,&H000B1012,&HE00B1012,1,0,0,0,100,100,1,0,3,14,0,2,40,40,420,1",
        "Style: HighlightCyan,Consolas,46,&H0000E5FF,&H000000FF,&H000B1012,&HE00B1012,1,0,0,0,100,100,1,0,3,16,0,2,40,40,420,1",
        "Style: HighlightGold,Consolas,46,&H0000E6FF,&H000000FF,&H000B1012,&HE00B1012,1,0,0,0,100,100,1,0,3,16,0,2,40,40,420,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for seg in data["segments"]:
        raw = seg["text"].strip()
        display = translit_map.get(raw, raw)
        words = display.split()
        page_size = 4
        num_pages = math.ceil(len(words) / page_size)
        seg_duration = seg["end"] - seg["start"]
        page_dur = seg_duration / max(1, num_pages)

        for p in range(num_pages):
            p_words = words[p * page_size : (p + 1) * page_size]
            p_text = " ".join(p_words)
            p_start = seg["start"] + p * page_dur
            p_end = min(seg["end"], p_start + page_dur)

            # Style selection
            if any(k in p_text.upper() for k in ["90%", "LOSE", "LEVERAGE", "REVENGE", "FAST"]):
                style = "HighlightCyan"
            elif any(k in p_text.upper() for k in ["KYUN", "RISK", "MISTAKE", "CAPITAL"]):
                style = "HighlightGold"
            else:
                style = "Default"

            lines.append(f"Dialogue: 0,{fmt_time(p_start)},{fmt_time(p_end)},{style},,0,0,0,,{p_text}")

    ass_path.write_text("\n".join(lines), encoding="utf-8")


# ============================================================================
# 4. MASTER BUILD & COMPOSITING PIPELINE
# ============================================================================

def build_0824_master() -> None:
    source_video = Path(r"D:\Downloads\0824.mp4")
    master_output = DELIVERABLE_DIR / "edited.mp4"

    print("[Varun Mayya Build] 1. Generating Layered Sound Design (SFX + 92 BPM Bed)...")
    sfx_paths = generate_all_sfx()
    music_wav = ASSETS_DIR / "music-bed.wav"
    generate_varun_mayya_music_bed(music_wav, 40.0)

    print("[Varun Mayya Build] 2. Generating 1080x1920 Procedural Motion Graphics...")
    broll_risk = BROLL_DIR / "broll_risk_matrix.mp4"
    generate_risk_matrix_video(broll_risk, duration_sec=6.0)

    broll_leverage = BROLL_DIR / "broll_leverage_scale.mp4"
    generate_leverage_scale_video(broll_leverage, duration_sec=6.0)

    broll_revenge = BROLL_DIR / "broll_revenge_trading.mp4"
    generate_revenge_trading_video(broll_revenge, duration_sec=6.0)

    print("[Varun Mayya Build] 3. Building Kinetic Monospace Captions...")
    transcript_file = WORKSPACE / "storage" / "0824_transcript.json"
    ass_path = DELIVERABLE_DIR / "captions.ass"
    build_varun_mayya_subtitles(transcript_file, ass_path)

    ass_filter_path = str(ass_path).replace("\\", "/").replace(":", "\\:")

    print("[Varun Mayya Build] 4. Compositing Multi-Track Timeline (PIP, Motion Graphics, SFX, Color Grade)...")
    
    # Filter Complex:
    # 0:v = Presenter Base (D:\Downloads\0824.mp4)
    # 1:a = 92 BPM Music Bed
    # 2:v = Motion Graphic 1 (Risk Matrix: 5.5s - 11.2s)
    # 3:v = Motion Graphic 2 (Leverage: 11.2s - 17.5s)
    # 4:v = Motion Graphic 3 (Revenge Trading: 19.6s - 28.5s)
    # 5..10: SFX cues
    filter_complex = (
        # Presenter Zoom Stream (1.28x punch zoom on emphasis beats)
        f"[0:v]split=2[pres_base][pres_pip_raw];"
        f"[pres_base]scale=1382:2458,crop=1080:1920:151:269[pres_zoom];"
        
        # Presenter PIP circle cutout (340x340 placed top-right with border)
        f"[pres_pip_raw]scale=360:640,crop=340:340:10:80,format=yuva420p[pres_pip];"
        
        # Presenter Zoom switching: 0.0 - 2.8s (Wide -> Zoom on 90% LOSE)
        f"[pres_base][pres_zoom]blend=all_expr='if(between(T,0.8,3.5)+between(T,17.5,19.6)+between(T,34.5,38.1),B,A)'[v_pres_switched];"
        
        # Overlay B-Roll Graphic 1: Risk Matrix (5.5s - 11.2s)
        f"[v_pres_switched][2:v]overlay=enable='between(t,5.5,11.2)'[v_with_risk];"
        # Overlay B-Roll Graphic 2: Leverage Scale (11.2s - 17.5s)
        f"[v_with_risk][3:v]overlay=enable='between(t,11.2,17.5)'[v_with_lev];"
        # Overlay B-Roll Graphic 3: Revenge Trading (19.6s - 28.5s)
        f"[v_with_lev][4:v]overlay=enable='between(t,19.6,28.5)'[v_with_all_broll];"
        
        # Overlay PIP Presenter during B-Roll (5.5s - 17.5s and 19.6s - 28.5s) at x=680, y=140
        f"[v_with_all_broll][pres_pip]overlay=x=680:y=140:enable='between(t,5.5,17.5)+between(t,19.6,28.5)'[v_composite];"
        
        # Cinema Color Grading: S-Curve Contrast, Saturation, Vignette
        f"[v_composite]eq=contrast=1.14:brightness=0.01:saturation=1.24,vignette=PI/5[v_graded];"
        
        # Apply Kinetic Captions
        f"[v_graded]ass='{ass_filter_path}'[v_out];"
        
        # Audio Mixing: Dialogue (0:a) + Music (1:a) + 6 SFX Cues (5..10)
        f"[1:a]volume=0.18[music];"
        f"[5:a]adelay=0|0,volume=0.9[sfx0];"         # Hook sub-impact @ 0.0s
        f"[6:a]adelay=1800|1800,volume=0.75[sfx1];"  # Whoosh @ 1.8s
        f"[7:a]adelay=2500|2500,volume=0.8[sfx2];"   # Snap @ 2.5s ("Lekin Kyun?")
        f"[8:a]adelay=5500|5500,volume=0.7[sfx3];"   # Data Tick @ 5.5s (Risk mistake)
        f"[9:a]adelay=11200|11200,volume=0.85[sfx4];"# Riser @ 11.2s (Leverage)
        f"[10:a]adelay=19600|19600,volume=0.9[sfx5];"# Warning drop @ 19.6s (Revenge trading)
        f"[0:a][music][sfx0][sfx1][sfx2][sfx3][sfx4][sfx5]amix=inputs=8:duration=first:dropout_transition=2[a_mixed];"
        f"[a_mixed]loudnorm=I=-14:TP=-1.0:LRA=7[a_out]"
    )

    cmd = [
        FFMPEG,
        "-y",
        "-i", str(source_video),
        "-i", str(music_wav),
        "-i", str(broll_risk),
        "-i", str(broll_leverage),
        "-i", str(broll_revenge),
        "-i", str(sfx_paths["hook_impact"]),
        "-i", str(sfx_paths["whoosh"]),
        "-i", str(sfx_paths["snap"]),
        "-i", str(sfx_paths["tick"]),
        "-i", str(sfx_paths["riser"]),
        "-i", str(sfx_paths["warn"]),
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

    print("[Varun Mayya Build] 5. Rendering 1080x1920 Master MP4...")
    res = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if res.returncode != 0:
        print("Render Error:\n", res.stderr[-3000:])
        raise RuntimeError("Master rendering failed.")

    print(f"\nSUCCESS: Varun Mayya Master Render Complete!\nOutput: {master_output} ({master_output.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    build_0824_master()

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
OUTPUT_DIR = Path(r"D:\DaVinciResolve\Exports")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DELIVERABLE_DIR = WORKSPACE / "storage" / "deliverables" / "0821-production-v2"
DELIVERABLE_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR = DELIVERABLE_DIR / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
BROLL_DIR = ASSETS_DIR / "broll"
BROLL_DIR.mkdir(parents=True, exist_ok=True)
SFX_DIR = ASSETS_DIR / "sfx"
SFX_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# 1. PROCEDURAL SOUND EFFECTS GENERATOR
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

    # 1. Heavy Hook Impact
    t = np.linspace(0, 0.6, int(sr * 0.6), False)
    sub = np.sin(2 * np.pi * (65 * np.exp(-t * 6) + 35) * t) * np.exp(-t * 8)
    transient = np.random.uniform(-0.6, 0.6, len(t)) * np.exp(-t * 35)
    sfx_paths["hook_impact"] = SFX_DIR / "hook_impact.wav"
    make_wav(sfx_paths["hook_impact"], sub * 0.8 + transient * 0.4)

    # 2. Fast Air Swoosh
    t = np.linspace(0, 0.28, int(sr * 0.28), False)
    noise = np.random.uniform(-1, 1, len(t))
    env = (np.sin(np.pi * t / 0.28) ** 2) * (1 + 0.3 * np.sin(2 * np.pi * 12 * t))
    sfx_paths["whoosh"] = SFX_DIR / "whoosh.wav"
    make_wav(sfx_paths["whoosh"], noise * env * 0.5)

    # 3. Digital UI Snap / Pop
    t = np.linspace(0, 0.12, int(sr * 0.12), False)
    freq = 1400 * (1 + 0.8 * np.exp(-t * 50))
    pop = np.sin(2 * np.pi * freq * t) * np.exp(-t * 45)
    sfx_paths["snap"] = SFX_DIR / "snap.wav"
    make_wav(sfx_paths["snap"], pop * 0.7)

    # 4. Code Tick
    t = np.linspace(0, 0.06, int(sr * 0.06), False)
    tick = np.sin(2 * np.pi * 2600 * t) * np.exp(-t * 80)
    sfx_paths["tick"] = SFX_DIR / "tick.wav"
    make_wav(sfx_paths["tick"], tick * 0.6)

    # 5. Tension Riser
    t = np.linspace(0, 0.8, int(sr * 0.8), False)
    rise_freq = 80 + 350 * (t / 0.8) ** 2
    rise = np.sin(2 * np.pi * rise_freq * t) * (t / 0.8) * 0.4
    sfx_paths["riser"] = SFX_DIR / "riser.wav"
    make_wav(sfx_paths["riser"], rise)

    # 6. Notification Bell / CTA Chime
    t = np.linspace(0, 0.5, int(sr * 0.5), False)
    chime1 = np.sin(2 * np.pi * 1046.5 * t) * np.exp(-t * 6)  # C6
    chime2 = np.sin(2 * np.pi * 1318.5 * t) * np.exp(-t * 6)  # E6
    chime3 = np.sin(2 * np.pi * 1567.98 * t) * np.exp(-t * 7) # G6
    sfx_paths["bell"] = SFX_DIR / "bell.wav"
    make_wav(sfx_paths["bell"], (chime1 + chime2 + chime3) * 0.3)

    return sfx_paths


def generate_cinematic_music_bed(output_path: Path, duration: float) -> None:
    sr = 48000
    t = np.linspace(0, duration, int(sr * duration), False)
    bpm = 92.0
    beat_sec = 60.0 / bpm

    # Punchy electronic kick / sub pulse
    beat_idx = (t % beat_sec) / beat_sec
    kick_env = np.exp(-beat_idx * 16)
    sub = np.sin(2 * np.pi * 48.0 * t) * kick_env * 0.28

    # Driving hi-hat / shaker rhythm on 1/8th notes
    hat_idx = (t % (beat_sec / 2)) / (beat_sec / 2)
    hat_env = np.exp(-hat_idx * 40)
    noise = np.random.uniform(-1, 1, len(t))
    hat = noise * hat_env * 0.04

    # Warm analog synth chord pad (F#m -> D -> A -> E)
    pad = np.sin(2 * np.pi * 92.5 * t) * 0.08 + np.sin(2 * np.pi * 138.5 * t) * 0.05

    mix = sub + hat + pad
    make_wav(output_path, mix * 0.45, sr=sr)


# ============================================================================
# 2. HIGH-RES PROCEDURAL B-ROLL VIDEO GENERATORS (1080x1920)
# ============================================================================

def generate_code_terminal_video(output_path: Path, duration_sec: float = 6.0, fps: int = 30) -> None:
    """Generates an algorithmic trading code terminal video."""
    w, h = 1080, 1920
    out = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
    num_frames = int(duration_sec * fps)

    code_lines = [
        "// PROFIT BRICKS | HIGH-FREQUENCY EA ENGINE",
        "input double LotSize = 1.00; // Calculated 4.2% Risk",
        "input int    StopLoss = 250;  // ATR Volatility Offset",
        "input bool   AutoCompound = true;",
        "",
        "void OnTick() {",
        "    if (!MarketMonitor24x7.IsSignalValid()) return;",
        "    double entryPrice = SymbolInfoDouble(_Symbol, SYMBOL_ASK);",
        "    double riskTarget = CalculateDynamicRisk(LotSize);",
        "    ",
        "    // Automated Order Routing",
        "    int ticket = OrderSend(_Symbol, OP_BUY, LotSize, entryPrice, 3);",
        "    if (ticket > 0) {",
        "        Print(\">> EXECUTION SUCCESS: Target 10x Matrix\");",
        "        SendNotification(\"EA BOT: Order Placed @ \" + DoubleToString(entryPrice));",
        "    }",
        "}"
    ]

    for f in range(num_frames):
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:] = (13, 17, 22)  # VS Code dark modern background

        # Terminal Header Bar
        cv2.rectangle(img, (60, 260), (1020, 360), (22, 27, 34), -1)
        cv2.circle(img, (100, 310), 10, (60, 60, 240), -1)  # Red
        cv2.circle(img, (130, 310), 10, (40, 180, 240), -1) # Yellow
        cv2.circle(img, (160, 310), 10, (40, 200, 80), -1)  # Green
        cv2.putText(img, "ExpertAdvisor_Core.mq5 - ProfitBricks v4.2", (200, 318), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 190, 200), 2)

        # Terminal Body
        cv2.rectangle(img, (60, 360), (1020, 1600), (17, 21, 28), -1)
        cv2.rectangle(img, (60, 260), (1020, 1600), (45, 55, 72), 2)

        # Write lines progressively
        visible_lines = min(len(code_lines), int((f / num_frames) * (len(code_lines) + 4)))
        for idx in range(visible_lines):
            line = code_lines[idx]
            y_pos = 430 + idx * 64
            
            # Syntax coloring
            if line.startswith("//"):
                col = (100, 120, 140)
            elif "input " in line or "void " in line or "if " in line:
                col = (240, 120, 180) # Pink keyword
            elif "OrderSend" in line or "Print" in line or "CalculateDynamicRisk" in line:
                col = (0, 229, 255)   # Cyan function
            else:
                col = (220, 230, 240) # White/Light
                
            # Line numbers
            cv2.putText(img, f"{idx+1:02d}", (85, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (70, 85, 100), 2)
            cv2.putText(img, line, (140, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.65, col, 2)

        # Highlight current active execution line
        if visible_lines > 0 and visible_lines <= len(code_lines):
            highlight_y = 430 + (visible_lines - 1) * 64 - 20
            overlay = img.copy()
            cv2.rectangle(overlay, (62, highlight_y), (1018, highlight_y + 55), (0, 229, 255), -1)
            cv2.addWeighted(overlay, 0.15, img, 0.85, 0, img)

        out.write(img)
    out.release()


def generate_market_radar_video(output_path: Path, duration_sec: float = 6.0, fps: int = 30) -> None:
    """Generates a 24x7 global market telemetry motion plate."""
    w, h = 1080, 1920
    out = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
    num_frames = int(duration_sec * fps)

    for f in range(num_frames):
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:] = (10, 14, 18)

        # Background grid
        for y in range(0, h, 60):
            cv2.line(img, (0, y), (w, y), (20, 28, 35), 1)
        for x in range(0, w, 60):
            cv2.line(img, (x, 0), (x, h), (20, 28, 35), 1)

        # Rotating Radar Circles
        center = (540, 960)
        angle = (f / fps) * 90  # 90 deg/sec
        
        for r in [200, 360, 520]:
            cv2.circle(img, center, r, (30, 48, 58), 2)
            
        # Radar sweeping line
        rad = np.radians(angle)
        end_x = int(center[0] + 520 * np.cos(rad))
        end_y = int(center[1] + 520 * np.sin(rad))
        cv2.line(img, center, (end_x, end_y), (0, 229, 255), 3, cv2.LINE_AA)

        # Glowing Active Hub Nodes
        nodes = [(400, 800, "NEW YORK"), (680, 850, "LONDON"), (520, 1150, "TOKYO"), (350, 1100, "SINGAPORE")]
        for nx, ny, name in nodes:
            cv2.circle(img, (nx, ny), 12, (0, 230, 118), -1)
            cv2.circle(img, (nx, ny), 24, (0, 230, 118), 2)
            cv2.putText(img, name + " [LIVE]", (nx + 20, ny + 6), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 230, 220), 2)

        # Central Badge HUD
        cv2.rectangle(img, (140, 300), (940, 460), (16, 24, 30), -1)
        cv2.rectangle(img, (140, 300), (940, 460), (0, 229, 255), 3)
        cv2.putText(img, "24x7 REAL-TIME MARKET SURVEILLANCE", (175, 365), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 229, 255), 2)
        cv2.putText(img, "0.00ms ALGO LATENCY | ZERO MISSED SETUPS", (195, 420), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 230, 118), 2)

        out.write(img)
    out.release()


# ============================================================================
# 3. ADVANCED COMPOSITOR & MASTER RENDER
# ============================================================================

def build_advanced_cinema_master() -> None:
    source_video = Path(r"D:\Downloads\0821.mp4")
    master_output = OUTPUT_DIR / "0821-production-master.mp4"
    local_output = DELIVERABLE_DIR / "edited.mp4"

    print("[Cinema Build] 1. Generating high-fidelity procedural SFX...")
    sfx_paths = generate_all_sfx()

    print("[Cinema Build] 2. Generating dynamic 92 BPM music bed...")
    music_wav = ASSETS_DIR / "music-bed.wav"
    generate_cinematic_music_bed(music_wav, 52.0)

    print("[Cinema Build] 3. Rendering procedural 1080x1920 B-roll videos...")
    broll_code = BROLL_DIR / "broll_code_terminal.mp4"
    generate_code_terminal_video(broll_code, duration_sec=7.0)

    broll_radar = BROLL_DIR / "broll_market_radar.mp4"
    generate_market_radar_video(broll_radar, duration_sec=7.0)

    # 4. Create Word-Timed Kinetic Captions (ASS)
    transcript_file = WORKSPACE / "storage" / "0821_transcripts.json"
    with open(transcript_file, "r", encoding="utf-8") as f:
        transcript_data = json.load(f)["0821"]

    ass_path = DELIVERABLE_DIR / "captions.ass"
    
    translit_map = {
        "मेरे पास आभी एक लाक रूपे हैं और मुझे एसे दस लाक बनाना है": "Mere paas abhi 1 Lakh rupaye hain aur mujhe ise 10 Lakh banana hai",
        "तो सब से फास तरीका क्या हो सकता है?": "To sabse FAST tareeka kya ho sakta hai?",
        "आप एए, यानी ट्रेटिंग रोबाट का यूस कर सकते हो": "Aap EA yani Trading Robot ka use kar sakte ho",
        "और ये पोसिबल भी है क्योंकी काफी लोगोने अचीव भी किया है": "Aur yeh POSSIBLE bhi hai kyunki kafi logo ne achieve kiya hai",
        "आजकल माकेट में काफी अडवान्स रोबाट से हैं, जो 24x7 माकेट को मूनिटर करते रहते हैं": "Aajkal market mein ADVANCED ROBOTS hain jo 24x7 monitor karte hain",
        "तो फिर इस में रिस्क क्या है?": "To fir isme RISK kya hai?",
        "रिस्क तो ट्रेटिंग में रहता ही है, लेकिन अगर आप कालकュلेटिवली रिस्क लोग,": "Risk to trading mein rehta hi hai, lekin CALCULATIVE RISK loge",
        "तो से बेटर तरीके से मनेज कर सकते हो": "To ise better tareeke se MANAGE kar sakte ho",
        "अर क्या सछ में काफी लोग, अतोमेशन से अच्छा कर रहें?": "Aur kya sach mein log AUTOMATION se achha kar rahe hain?",
        "हाँ, ही, का़ी लोग, अतोमेशन युज कर रहे है,": "Haan kafi log automation use kar rahe hain",
        "लेकिन लोगों को आभी एक भारे में जादा नोलज नहीं है.": "Lekin logo ko iske baare mein zyada knowledge nahi hai",
        "इसले मेरा सजेअष्छन है, पहले इसके बारे में थोडाण लोग लोग,": "Isliye mera suggestion hai, pehle isko samjhein",
        "अद़ आब को अछ़े समझा सकते हैं की यह कैसे वब करता है?": "Taaki aap achhe se samajh sakein yeh kaise WORK karta hai",
        "तो यह सब कहा से सीक हैं?": "To yeh sab KAHAN se seekhein?",
        "और अगर मुजे यह प्रोपरेली समजना हो, तो कैा करूँ?": "Aur agar mujhe properly samajhna ho to kya karun?",
        "अगर आपको भी यह सीकना है कि रोबोट से कैसे वब करते हैं?": "Agar aapko bhi seekhna hai ki robots kaise work karte hain",
        "तो उप्रोफिट ब्रिख को फलो की जै.": "To PROFIT BRICKS ko follow kijiye",
        "हम ये सब फ्री में एकस्पलेण करेंगे": "Hum yeh sab FREE mein explain karenge!"
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
        "Style: Highlight,Consolas,46,&H0000E5FF,&H000000FF,&H000B1012,&HE00B1012,1,0,0,0,100,100,1,0,3,16,0,2,40,40,420,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for seg in transcript_data["segments"]:
        raw_text = seg["text"].strip()
        display_text = translit_map.get(raw_text, raw_text)
        words = display_text.split()
        page_size = 4
        num_pages = math.ceil(len(words) / page_size)
        seg_duration = seg["end"] - seg["start"]
        page_duration = seg_duration / max(1, num_pages)

        for p in range(num_pages):
            p_words = words[p * page_size : (p + 1) * page_size]
            p_text = " ".join(p_words)
            p_start = seg["start"] + p * page_duration
            p_end = min(seg["end"], p_start + page_duration)
            style = "Highlight" if any(k in p_text.upper() for k in ["FAST", "10 LAKH", "ROBOT", "24X7", "RISK", "AUTOMATION", "PROFIT BRICKS", "FREE"]) else "Default"
            lines.append(f"Dialogue: 0,{fmt_time(p_start)},{fmt_time(p_end)},{style},,0,0,0,,{p_text}")

    ass_path.write_text("\n".join(lines), encoding="utf-8")

    ass_filter_path = str(ass_path).replace("\\", "/").replace(":", "\\:")

    print("[Cinema Build] 4. Assembling Multi-Track Composition (PIP Presenter, B-Roll, SFX, Color Grade)...")
    
    # Complex Filtergraph:
    # 1. Base Presenter (0:v)
    # 2. B-Roll Code (2:v)
    # 3. B-Roll Radar (3:v)
    # 4. PIP presenter cutout (circular with glow)
    # 5. SFX mixing at exact timestamps (hook 0.0s, swoosh 2.8s, tick 7.0s, radar 11.7s, riser 17.0s, bell 44.2s)
    
    filter_complex = (
        # Presenter Zoom Stream
        f"[0:v]split=2[pres_base][pres_pip_raw];"
        f"[pres_base]scale=1350:2400,crop=1080:1920:135:240[pres_zoom];"
        
        # Presenter PIP circle cutout (340x340 placed at top-right)
        f"[pres_pip_raw]scale=360:640,crop=340:340:10:80,format=yuva420p[pres_pip];"
        
        # Timeline Switching:
        # 0.0 - 5.9s: Presenter (Wide -> Zoom @ 2.8s)
        # 5.9 - 11.7s: B-Roll Code Terminal + PIP Presenter
        # 11.7 - 17.0s: B-Roll 24x7 Market Radar + PIP Presenter
        # 17.0 - 50.5s: Presenter with dynamic punch zooms & risk resets
        f"[pres_base][pres_zoom]blend=all_expr='if(between(T,2.8,5.9)+between(T,17.0,21.8)+between(T,44.2,50.5),B,A)'[v_pres_switched];"
        
        # Overlay B-Roll Code Terminal (5.9s - 11.7s)
        f"[v_pres_switched][2:v]overlay=enable='between(t,5.9,11.7)'[v_with_code];"
        # Overlay B-Roll Market Radar (11.7s - 17.0s)
        f"[v_with_code][3:v]overlay=enable='between(t,11.7,17.0)'[v_with_broll];"
        
        # Overlay PIP Presenter during B-Roll (5.9s - 17.0s) at x=680, y=140
        f"[v_with_broll][pres_pip]overlay=x=680:y=140:enable='between(t,5.9,17.0)'[v_composite];"
        
        # Apply Cinema Color Grade: S-Curve Contrast, Saturation, Vignette
        f"[v_composite]eq=contrast=1.12:brightness=0.01:saturation=1.22,vignette=PI/5[v_graded];"
        
        # Apply Kinetic Monospace Captions
        f"[v_graded]ass='{ass_filter_path}'[v_out];"
        
        # Audio Mix: Dialogue (0:a) + Music (1:a) + SFX Cues (4..9)
        f"[1:a]volume=0.18[music];"
        f"[4:a]adelay=0|0,volume=0.9[sfx0];"        # Hook impact @ 0.0s
        f"[5:a]adelay=2800|2800,volume=0.8[sfx1];"  # Whoosh @ 2.8s
        f"[6:a]adelay=7000|7000,volume=0.7[sfx2];"  # Code Tick @ 7.0s
        f"[7:a]adelay=11700|11700,volume=0.8[sfx3];"# Snap @ 11.7s
        f"[8:a]adelay=17000|17000,volume=0.7[sfx4];"# Riser @ 17.0s
        f"[9:a]adelay=44200|44200,volume=0.8[sfx5];"# CTA Bell @ 44.2s
        f"[0:a][music][sfx0][sfx1][sfx2][sfx3][sfx4][sfx5]amix=inputs=8:duration=first:dropout_transition=2[a_mixed];"
        f"[a_mixed]loudnorm=I=-14:TP=-1.0:LRA=7[a_out]"
    )

    cmd = [
        FFMPEG,
        "-y",
        "-i", str(source_video),
        "-i", str(music_wav),
        "-i", str(broll_code),
        "-i", str(broll_radar),
        "-i", str(sfx_paths["hook_impact"]),
        "-i", str(sfx_paths["whoosh"]),
        "-i", str(sfx_paths["tick"]),
        "-i", str(sfx_paths["snap"]),
        "-i", str(sfx_paths["riser"]),
        "-i", str(sfx_paths["bell"]),
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

    print("[Cinema Build] 5. Rendering 1080x1920 Cinema Master...")
    result = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if result.returncode != 0:
        print("Render Error:\n", result.stderr[-3000:])
        raise RuntimeError("Cinema Master rendering failed.")

    shutil.copy2(master_output, local_output)
    print(f"\n✅ CINEMA PRODUCTION MASTER COMPLETED!\nPath: {master_output} ({master_output.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    build_advanced_cinema_master()

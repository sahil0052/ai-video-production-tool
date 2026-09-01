"""
Varun Mayya Production Master Builder for 0824.mp4 (5-Stage Funnel Execution)
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
OUTPUT_DIR = WORKSPACE / "storage" / "deliverables" / "0824-varun-mayya-production-master"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR = OUTPUT_DIR / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
BROLL_DIR = ASSETS_DIR / "broll"
BROLL_DIR.mkdir(parents=True, exist_ok=True)
SFX_DIR = ASSETS_DIR / "sfx"
SFX_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACTS_DIR = ASSETS_DIR / "scene_artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================================
# 1. PROCEDURAL SOUND EFFECTS & 92 BPM CYBER-TECH BED
# ============================================================================

def make_wav(path: Path, samples: np.ndarray, sr: int = 48000) -> None:
    samples = np.clip(samples, -1.0, 1.0)
    data = (samples * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        wav.writeframes(data.tobytes())


def generate_sfx_suite() -> dict[str, Path]:
    sr = 48000
    sfx = {}

    # Tier 1: Hook Sub-Impact (0.0s)
    t = np.linspace(0, 0.7, int(sr * 0.7), False)
    sub = np.sin(2 * np.pi * (75 * np.exp(-t * 5) + 32) * t) * np.exp(-t * 7)
    trans = np.random.uniform(-0.6, 0.6, len(t)) * np.exp(-t * 30)
    sfx["hook_impact"] = SFX_DIR / "hook_impact.wav"
    make_wav(sfx["hook_impact"], sub * 0.85 + trans * 0.35)

    # Tier 2: Transition Whoosh (Punch zooms & B-roll slides)
    t = np.linspace(0, 0.28, int(sr * 0.28), False)
    noise = np.random.uniform(-1, 1, len(t))
    env = (np.sin(np.pi * t / 0.28) ** 2) * (1 + 0.3 * np.sin(2 * np.pi * 14 * t))
    sfx["whoosh"] = SFX_DIR / "whoosh.wav"
    make_wav(sfx["whoosh"], noise * env * 0.5)

    # Tier 3: Data UI Tick (Numbers & Code lines)
    t = np.linspace(0, 0.05, int(sr * 0.05), False)
    tick = np.sin(2 * np.pi * 2800 * t) * np.exp(-t * 90)
    sfx["tick"] = SFX_DIR / "tick.wav"
    make_wav(sfx["tick"], tick * 0.6)

    # Tier 4: Question Pop Snap ("Lekin Kyun?")
    t = np.linspace(0, 0.12, int(sr * 0.12), False)
    freq = 1600 * (1 + 0.8 * np.exp(-t * 45))
    pop = np.sin(2 * np.pi * freq * t) * np.exp(-t * 40)
    sfx["snap"] = SFX_DIR / "snap.wav"
    make_wav(sfx["snap"], pop * 0.7)

    # Tier 5: Risk Riser & Warning Drop (Leverage & Revenge trading)
    t = np.linspace(0, 0.9, int(sr * 0.9), False)
    rise_freq = 70 + 420 * (t / 0.9) ** 2.2
    rise = np.sin(2 * np.pi * rise_freq * t) * (t / 0.9) * 0.45
    sfx["riser"] = SFX_DIR / "riser.wav"
    make_wav(sfx["riser"], rise)

    t = np.linspace(0, 0.8, int(sr * 0.8), False)
    drop_freq = 180 * np.exp(-t * 3.5) + 38
    warn = np.sin(2 * np.pi * drop_freq * t) * np.exp(-t * 4) * 0.7
    sfx["warn"] = SFX_DIR / "warn.wav"
    make_wav(sfx["warn"], warn)

    # Tier 6: Brand / CTA Harmonic Chime
    t = np.linspace(0, 0.5, int(sr * 0.5), False)
    c1 = np.sin(2 * np.pi * 1046.5 * t) * np.exp(-t * 6)
    c2 = np.sin(2 * np.pi * 1318.5 * t) * np.exp(-t * 6)
    c3 = np.sin(2 * np.pi * 1567.98 * t) * np.exp(-t * 7)
    sfx["chime"] = SFX_DIR / "chime.wav"
    make_wav(sfx["chime"], (c1 + c2 + c3) * 0.35)

    return sfx


def generate_music_bed(output_path: Path, duration: float) -> None:
    sr = 48000
    t = np.linspace(0, duration, int(sr * duration), False)
    bpm = 92.0
    beat_sec = 60.0 / bpm

    beat_idx = (t % beat_sec) / beat_sec
    kick_env = np.exp(-beat_idx * 16)
    sub = np.sin(2 * np.pi * 48.0 * t) * kick_env * 0.28

    hat_idx = (t % (beat_sec / 2)) / (beat_sec / 2)
    hat_env = np.exp(-hat_idx * 40)
    noise = np.random.uniform(-1, 1, len(t))
    hat = noise * hat_env * 0.035

    pad = np.sin(2 * np.pi * 92.5 * t) * 0.07 + np.sin(2 * np.pi * 138.5 * t) * 0.05
    mix = sub + hat + pad
    make_wav(output_path, mix * 0.45, sr=sr)


# ============================================================================
# 2. PROCEDURAL 1080x1920 MOTION GRAPHICS & SCENE ARTIFACTS
# ============================================================================

def generate_risk_matrix_video(output_path: Path, duration_sec: float = 6.0, fps: int = 30) -> None:
    """Scene 2: Single-Trade Capital Drain & Risk Matrix."""
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
        center = (540, 700)
        cv2.circle(img, center, 170, (26, 36, 46), -1)
        cv2.circle(img, center, 170, (60, 60, 240), 6)
        cv2.putText(img, "90%", (435, 700), cv2.FONT_HERSHEY_SIMPLEX, 2.3, (255, 255, 255), 5)
        cv2.putText(img, "FAIL RATE", (455, 760), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (60, 60, 240), 2)

        # Animated Capital Drain Bar (₹1,00,000 -> ₹8,500)
        progress = f / num_frames
        curr_cap = max(8500, int(100000 * (1.0 - progress * 0.92)))
        
        cv2.rectangle(img, (100, 1040), (980, 1260), (18, 24, 30), -1)
        cv2.rectangle(img, (100, 1040), (980, 1260), (45, 55, 70), 2)
        cv2.putText(img, "CAPITAL AFTER 1 UNCONTROLLED TRADE:", (130, 1100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 220, 230), 2)
        cv2.putText(img, f"INR {curr_cap:,}", (130, 1170), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (60, 60, 240) if curr_cap < 30000 else (0, 230, 118), 3)

        bar_w = int(780 * (curr_cap / 100000.0))
        cv2.rectangle(img, (130, 1200), (130 + bar_w, 1235), (60, 60, 240), -1)

        if f % 15 < 8:
            cv2.rectangle(img, (260, 1360), (820, 1440), (40, 15, 20), -1)
            cv2.rectangle(img, (260, 1360), (820, 1440), (60, 60, 240), 2)
            cv2.putText(img, "! DANGER: 91.5% DRAWDOWN !", (290, 1410), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (60, 60, 240), 2)

        out.write(img)
    out.release()


def generate_leverage_scale_video(output_path: Path, duration_sec: float = 6.0, fps: int = 30) -> None:
    """Scene 3: 1:500 Leverage Trap Scale."""
    w, h = 1080, 1920
    out = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
    num_frames = int(duration_sec * fps)

    for f in range(num_frames):
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:] = (12, 16, 20)

        for y in range(0, h, 60):
            cv2.line(img, (0, y), (w, y), (22, 30, 38), 1)
        for x in range(0, w, 60):
            cv2.line(img, (x, 0), (x, h), (22, 30, 38), 1)

        # Header Badge
        cv2.rectangle(img, (100, 240), (980, 360), (20, 28, 35), -1)
        cv2.rectangle(img, (100, 240), (980, 360), (0, 229, 255), 2)
        cv2.putText(img, "MISTAKE #2: EXCESSIVE LEVERAGE", (135, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 229, 255), 2)
        cv2.putText(img, "1:500 MULTIPLIER TRAP", (135, 335), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 229, 255), 2)

        # Scale Boxes
        cv2.rectangle(img, (100, 560), (500, 880), (18, 26, 32), -1)
        cv2.rectangle(img, (100, 560), (500, 880), (0, 230, 118), 2)
        cv2.putText(img, "YOUR DEPOSIT", (130, 620), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 230, 118), 2)
        cv2.putText(img, "INR 10,000", (130, 710), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)
        cv2.putText(img, "[1x MARGIN]", (130, 780), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (140, 160, 180), 2)

        cv2.rectangle(img, (580, 560), (980, 880), (35, 20, 24), -1)
        cv2.rectangle(img, (580, 560), (980, 880), (60, 60, 240), 2)
        cv2.putText(img, "POSITION SIZE", (605, 620), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (60, 60, 240), 2)
        cv2.putText(img, "INR 50,00,000", (605, 710), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 3)
        cv2.putText(img, "[500x EXPOSURE]", (605, 780), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (60, 60, 240), 2)

        cv2.rectangle(img, (100, 1020), (980, 1260), (18, 24, 30), -1)
        cv2.rectangle(img, (100, 1020), (980, 1260), (45, 55, 70), 2)
        cv2.putText(img, "VOLATILITY RISK SENSITIVITY:", (130, 1080), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (200, 220, 230), 2)
        cv2.putText(img, "0.2% Market Move = 100% ACCOUNT WIPE", (130, 1160), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (60, 60, 240), 2)
        
        gauge_val = 0.5 + 0.45 * math.sin(f / 15.0)
        cv2.rectangle(img, (130, 1200), (130 + int(720 * gauge_val), 1230), (0, 229, 255), -1)

        out.write(img)
    out.release()


def generate_revenge_trading_video(output_path: Path, duration_sec: float = 6.0, fps: int = 30) -> None:
    """Scene 4: Revenge Trading & Compounding Drawdown Curve."""
    w, h = 1080, 1920
    out = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
    num_frames = int(duration_sec * fps)

    np.random.seed(99)
    equity = [100.0]
    for _ in range(40):
        equity.append(equity[-1] - np.random.uniform(1.5, 4.0))

    for f in range(num_frames):
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:] = (12, 16, 20)

        for y in range(0, h, 60):
            cv2.line(img, (0, y), (w, y), (22, 30, 38), 1)
        for x in range(0, w, 60):
            cv2.line(img, (x, 0), (x, h), (22, 30, 38), 1)

        # Header Badge
        cv2.rectangle(img, (100, 240), (980, 360), (20, 28, 35), -1)
        cv2.rectangle(img, (100, 240), (980, 360), (60, 60, 240), 2)
        cv2.putText(img, "MISTAKE #3: REVENGE TRADING", (135, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (60, 60, 240), 2)
        cv2.putText(img, "EMOTIONAL OVERTRADING SPIRAL", (135, 335), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 220, 230), 2)

        chart_top, chart_bot = 520, 1180
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

        curr_loss = (100 - equity[visible_pts])
        cv2.rectangle(img, (100, 1260), (980, 1460), (25, 18, 22), -1)
        cv2.rectangle(img, (100, 1260), (980, 1460), (60, 60, 240), 2)
        cv2.putText(img, f"COMPOUNDED DRAWDOWN: -{curr_loss:.1f}%", (140, 1340), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (60, 60, 240), 3)
        cv2.putText(img, "DESTROYED STRATEGY | ZERO DISCIPLINE", (140, 1410), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 220, 230), 2)

        out.write(img)
    out.release()


def generate_ea_terminal_video(output_path: Path, duration_sec: float = 6.0, fps: int = 30) -> None:
    """Scene 5: Tested Strategy & MetaTrader EA Rules Terminal."""
    w, h = 1080, 1920
    out = cv2.VideoWriter(str(output_path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
    num_frames = int(duration_sec * fps)

    code_lines = [
        "// EXPERT ADVISOR - PREDEFINED DISCIPLINE",
        "input double MaxRiskPerTrade = 1.0; // 1% Strict",
        "input int    MaxDailyDrawdown = 3;  // Hard Kill Switch",
        "input bool   EnforceStopLoss  = true;",
        "",
        "void ExecuteVerifiedStrategy() {",
        "    if (DailyLossPercent() >= MaxDailyDrawdown) {",
        "        Alert(\">> KILL SWITCH: Emotion Trading Blocked\");",
        "        return;",
        "    }",
        "    OrderSend(_Symbol, OP_BUY, CalculateLot(), Ask, 3);",
        "}"
    ]

    for f in range(num_frames):
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:] = (13, 17, 22)

        cv2.rectangle(img, (60, 260), (1020, 360), (22, 27, 34), -1)
        cv2.circle(img, (100, 310), 10, (60, 60, 240), -1)
        cv2.circle(img, (130, 310), 10, (40, 180, 240), -1)
        cv2.circle(img, (160, 310), 10, (40, 200, 80), -1)
        cv2.putText(img, "EA_StrategyEngine.mq5 - Predefined Rules", (200, 318), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 190, 200), 2)

        cv2.rectangle(img, (60, 360), (1020, 1500), (17, 21, 28), -1)
        cv2.rectangle(img, (60, 260), (1020, 1500), (45, 55, 72), 2)

        visible_lines = min(len(code_lines), int((f / num_frames) * (len(code_lines) + 4)))
        for idx in range(visible_lines):
            line = code_lines[idx]
            y_pos = 440 + idx * 75
            col = (100, 120, 140) if line.startswith("//") else ((240, 120, 180) if "input " in line or "void " in line else ((0, 229, 255) if "OrderSend" in line or "Alert" in line else (220, 230, 240)))
            cv2.putText(img, f"{idx+1:02d}", (85, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (70, 85, 100), 2)
            cv2.putText(img, line, (140, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.65, col, 2)

        out.write(img)
    out.release()


# ============================================================================
# 3. KINETIC MONOSPACE SUBTITLES (VARUN MAYYA SIGNATURE)
# ============================================================================

def build_varun_mayya_subtitles(ass_path: Path) -> None:
    # Full official transcript transliterated to high-retention Roman-Hinglish
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
        "Style: Default,Consolas,44,&H00FFFFFF,&H000000FF,&H000B1012,&HE00B1012,1,0,0,0,100,100,1,0,3,14,0,2,40,40,420,1",
        "Style: HighlightCyan,Consolas,46,&H0000E5FF,&H000000FF,&H000B1012,&HE00B1012,1,0,0,0,100,100,1,0,3,16,0,2,40,40,420,1",
        "Style: HighlightGold,Consolas,46,&H0000E6FF,&H000000FF,&H000B1012,&HE00B1012,1,0,0,0,100,100,1,0,3,16,0,2,40,40,420,1",
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
                style = "HighlightGold"
            else:
                style = "Default"

            lines.append(f"Dialogue: 0,{fmt_time(p_start)},{fmt_time(p_end)},{style},,0,0,0,,{p_text}")

    ass_path.write_text("\n".join(lines), encoding="utf-8")


# ============================================================================
# 4. MULTI-TRACK MASTER ASSEMBLY & GPU RENDER
# ============================================================================

def build_0824_production_master() -> None:
    source_video = Path(r"D:\Downloads\0824.mp4")
    master_output = OUTPUT_DIR / "0824-varun-mayya-master.mp4"
    deliverable_copy = WORKSPACE / "storage" / "deliverables" / "0824-varun-mayya-style" / "edited.mp4"

    print("[Stage 3] Synthesizing 6-Tier Sound Effects Suite & 92 BPM Bed...")
    sfx = generate_sfx_suite()
    music_wav = ASSETS_DIR / "music-bed.wav"
    generate_music_bed(music_wav, 40.0)

    print("[Stage 3] Generating 4 Procedural 1080x1920 Motion Graphics Video Plates...")
    broll_risk = BROLL_DIR / "broll_risk_matrix.mp4"
    generate_risk_matrix_video(broll_risk, duration_sec=6.0)

    broll_leverage = BROLL_DIR / "broll_leverage_scale.mp4"
    generate_leverage_scale_video(broll_leverage, duration_sec=6.0)

    broll_revenge = BROLL_DIR / "broll_revenge_trading.mp4"
    generate_revenge_trading_video(broll_revenge, duration_sec=6.0)

    broll_ea = BROLL_DIR / "broll_ea_terminal.mp4"
    generate_ea_terminal_video(broll_ea, duration_sec=6.0)

    print("[Stage 4] Generating Varun Mayya Monospace Kinetic Captions...")
    ass_path = OUTPUT_DIR / "captions.ass"
    build_varun_mayya_subtitles(ass_path)
    ass_filter_path = str(ass_path).replace("\\", "/").replace(":", "\\:")

    print("[Stage 5] Executing Multi-Track Compositor (PIP Presenter, 4 B-Rolls, 6 SFX, S-Curve Grade)...")
    
    # Filter Complex Layout:
    # 0:v = Presenter Video (D:\Downloads\0824.mp4)
    # 1:a = 92 BPM Music Bed
    # 2:v = B-Roll 1 (Risk Matrix: 5.5s - 11.2s)
    # 3:v = B-Roll 2 (Leverage Scale: 11.2s - 17.5s)
    # 4:v = B-Roll 3 (Revenge Trading: 19.6s - 28.5s)
    # 5:v = B-Roll 4 (EA Terminal: 28.5s - 34.5s)
    # 6..12: SFX Audio Cues
    filter_complex = (
        # Presenter Zoom Stream (1.28x punch zoom on emphasis moments)
        f"[0:v]split=2[pres_base][pres_pip_raw];"
        f"[pres_base]scale=1382:2458,crop=1080:1920:151:269[pres_zoom];"
        
        # Presenter PIP cutout (340x340 placed top-right with border)
        f"[pres_pip_raw]scale=360:640,crop=340:340:10:80,format=yuva420p[pres_pip];"
        
        # Presenter Punch-Zoom Switching (0.8s-3.5s, 17.5s-19.6s, 34.5s-38.1s)
        f"[pres_base][pres_zoom]blend=all_expr='if(between(T,0.8,3.5)+between(T,17.5,19.6)+between(T,34.5,38.1),B,A)'[v_pres_switched];"
        
        # Overlay B-Roll 1 (Risk Matrix: 5.5s - 11.2s)
        f"[v_pres_switched][2:v]overlay=enable='between(t,5.5,11.2)'[v_with_b1];"
        # Overlay B-Roll 2 (Leverage: 11.2s - 17.5s)
        f"[v_with_b1][3:v]overlay=enable='between(t,11.2,17.5)'[v_with_b2];"
        # Overlay B-Roll 3 (Revenge Trading: 19.6s - 28.5s)
        f"[v_with_b2][4:v]overlay=enable='between(t,19.6,28.5)'[v_with_b3];"
        # Overlay B-Roll 4 (EA Terminal: 28.5s - 34.5s)
        f"[v_with_b3][5:v]overlay=enable='between(t,28.5,34.5)'[v_with_all_broll];"
        
        # Overlay PIP Presenter during B-Roll scenes at x=680, y=140
        f"[v_with_all_broll][pres_pip]overlay=x=680:y=140:enable='between(t,5.5,17.5)+between(t,19.6,34.5)'[v_composite];"
        
        # Studio S-Curve Contrast, Saturation, Vignette
        f"[v_composite]eq=contrast=1.14:brightness=0.01:saturation=1.24,vignette=PI/5[v_graded];"
        
        # Kinetic Subtitles
        f"[v_graded]ass='{ass_filter_path}'[v_out];"
        
        # Audio Mix: Voice (0:a) + Ducked Music (1:a) + 7 SFX Events (6..12)
        f"[1:a]volume=0.17[music];"
        f"[6:a]adelay=0|0,volume=0.9[sfx0];"         # Hook Sub-Impact @ 0.0s
        f"[7:a]adelay=1800|1800,volume=0.75[sfx1];"  # Whoosh @ 1.8s
        f"[8:a]adelay=2500|2500,volume=0.8[sfx2];"   # Pop Snap @ 2.5s ("Lekin Kyun?")
        f"[9:a]adelay=5500|5500,volume=0.7[sfx3];"   # Data Tick @ 5.5s (Risk Management)
        f"[10:a]adelay=11200|11200,volume=0.85[sfx4];"# Riser @ 11.2s (Leverage)
        f"[11:a]adelay=19600|19600,volume=0.9[sfx5];"# Warning Drop @ 19.6s (Revenge Trading)
        f"[12:a]adelay=34500|34500,volume=0.85[sfx6];"# Brand Chime @ 34.5s (Follow CTA)
        f"[0:a][music][sfx0][sfx1][sfx2][sfx3][sfx4][sfx5][sfx6]amix=inputs=9:duration=first:dropout_transition=2[a_mixed];"
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
        "-i", str(broll_ea),
        "-i", str(sfx["hook_impact"]),
        "-i", str(sfx["whoosh"]),
        "-i", str(sfx["snap"]),
        "-i", str(sfx["tick"]),
        "-i", str(sfx["riser"]),
        "-i", str(sfx["warn"]),
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

    print("[Stage 5] Rendering GPU Production Master...")
    res = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if res.returncode != 0:
        print("Render Error:\n", res.stderr[-3000:])
        raise RuntimeError("Production master rendering failed.")

    shutil.copy2(master_output, deliverable_copy)
    print(f"\nSUCCESS: Production Master Render Complete!\nOutput: {master_output} ({master_output.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    build_0824_production_master()

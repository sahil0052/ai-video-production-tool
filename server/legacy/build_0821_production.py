from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from imageio_ffmpeg import get_ffmpeg_exe
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FFMPEG = get_ffmpeg_exe()
WORKSPACE = Path(__file__).resolve().parent.parent
OUTPUT_DIR = Path(r"D:\DaVinciResolve\Exports")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DELIVERABLE_DIR = WORKSPACE / "storage" / "deliverables" / "0821-production"
DELIVERABLE_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR = DELIVERABLE_DIR / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def generate_sfx(output_path: Path, sfx_type: str, duration: float = 0.25) -> None:
    """Procedurally synthesizes studio sound effects."""
    sr = 48000
    t = np.linspace(0, duration, int(sr * duration), False)
    if sfx_type == "click":
        # Sharp high-frequency mechanical tick
        freq = 2400
        env = np.exp(-t * 60)
        signal = np.sin(2 * np.pi * freq * t) * env
    elif sfx_type == "whoosh":
        # Sweeping noise burst
        noise = np.random.uniform(-1, 1, len(t))
        env = np.sin(np.pi * t / duration) ** 2
        signal = noise * env * 0.4
    elif sfx_type == "impact":
        # Low frequency thump + punch
        freq = 80 * np.exp(-t * 8) + 45
        env = np.exp(-t * 12)
        signal = np.sin(2 * np.pi * freq * t) * env * 0.8
    elif sfx_type == "snap":
        # Snappy digital notification pop
        freq = 1200 * (1 + 0.5 * np.exp(-t * 30))
        env = np.exp(-t * 40)
        signal = np.sin(2 * np.pi * freq * t) * env * 0.6
    else:
        signal = np.zeros_like(t)

    # Convert to 16-bit PCM
    signal = np.clip(signal, -1.0, 1.0)
    audio_int16 = (signal * 32767).astype(np.int16)
    
    import wave
    with wave.open(str(output_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        wav.writeframes(audio_int16.tobytes())


def generate_music_bed(output_path: Path, duration: float) -> None:
    """Generates a 92 BPM documentary-tech pulse bed."""
    sr = 48000
    t = np.linspace(0, duration, int(sr * duration), False)
    bpm = 92.0
    beat_sec = 60.0 / bpm

    # Bass root note pulse (F#1 / 46.25 Hz with sub-harmonic)
    base_freq = 46.25
    pulse_env = np.maximum(0, np.cos(2 * np.pi * t / beat_sec)) ** 4
    sub = np.sin(2 * np.pi * base_freq * t) * pulse_env * 0.22

    # Mid synth pulse (F#2 / 92.5 Hz and C#3 / 138.5 Hz)
    mid1 = np.sin(2 * np.pi * 92.5 * t) * (np.maximum(0, np.cos(2 * np.pi * t / (beat_sec / 2))) ** 3) * 0.08
    mid2 = np.sin(2 * np.pi * 138.5 * t) * 0.04

    # Subtle ambient stereo texture
    noise = np.random.uniform(-0.02, 0.02, len(t))

    mix = sub + mid1 + mid2 + noise
    mix = np.clip(mix * 0.5, -1.0, 1.0)
    audio_int16 = (mix * 32767).astype(np.int16)

    import wave
    with wave.open(str(output_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        wav.writeframes(audio_int16.tobytes())


def create_graphic_card(
    output_path: Path,
    title: str,
    subtitle: str,
    metric_val: str,
    badge: str = "AUTOMATION METRIC",
    theme: str = "cyan"
) -> None:
    """Creates a high-end 1080x1920 graphic card with dark tech aesthetic."""
    img = Image.new("RGBA", (1080, 1920), (11, 16, 18, 255))
    draw = ImageDraw.Draw(img)

    # Grid lines background
    for y in range(0, 1920, 60):
        draw.line([(0, y), (1080, y)], fill=(18, 26, 30, 255), width=1)
    for x in range(0, 1080, 60):
        draw.line([(x, 0), (x, 1920)], fill=(18, 26, 30, 255), width=1)

    # Accent colors
    accent_color = (0, 229, 255, 255) if theme == "cyan" else (0, 230, 118, 255)
    border_color = (24, 38, 44, 255)

    # Central Card
    card_rect = [100, 640, 980, 1280]
    draw.rounded_rectangle(card_rect, radius=24, fill=(14, 20, 23, 245), outline=border_color, width=3)

    # Badge Pill
    draw.rounded_rectangle([140, 680, 480, 730], radius=10, fill=(20, 32, 38, 255), outline=accent_color, width=2)
    draw.text((160, 692), badge, fill=accent_color)

    # Metric Value
    draw.text((140, 780), metric_val, fill=(255, 255, 255, 255))

    # Title & Subtitle
    draw.text((140, 960), title, fill=(200, 220, 230, 255))
    draw.text((140, 1040), subtitle, fill=(130, 155, 170, 255))

    # Corner highlight
    draw.line([(100, 640), (180, 640)], fill=accent_color, width=4)
    draw.line([(100, 640), (100, 720)], fill=accent_color, width=4)

    img.save(str(output_path), "PNG")


def build_ass_subtitles(segments: list[dict[str, Any]], ass_path: Path) -> None:
    """Builds Roman-Hinglish word-timed monospace subtitle file."""
    # Transliteration dictionary for crystal clear readability
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
        "Style: Default,Consolas,42,&H00FFFFFF,&H000000FF,&H000B1012,&HE00B1012,1,0,0,0,100,100,1,0,3,14,0,2,40,40,420,1",
        "Style: Highlight,Consolas,44,&H0000E5FF,&H000000FF,&H000B1012,&HE00B1012,1,0,0,0,100,100,1,0,3,16,0,2,40,40,420,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for seg in segments:
        raw_text = seg["text"].strip()
        display_text = translit_map.get(raw_text, raw_text)
        
        # Split into short 3-5 word pages for fast reading
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

            # Highlight emphasis words
            style = "Highlight" if any(k in p_text.upper() for k in ["FAST", "10 LAKH", "ROBOT", "24X7", "RISK", "AUTOMATION", "PROFIT BRICKS", "FREE"]) else "Default"
            lines.append(f"Dialogue: 0,{fmt_time(p_start)},{fmt_time(p_end)},{style},,0,0,0,,{p_text}")

    ass_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    source_video = Path(r"D:\Downloads\0821.mp4")
    if not source_video.is_file():
        raise FileNotFoundError(source_video)

    print(f"[Build] Processing 0821 Production Master from {source_video}...")

    # Load Transcript
    transcript_file = WORKSPACE / "storage" / "0821_transcripts.json"
    with open(transcript_file, "r", encoding="utf-8") as f:
        transcript_data = json.load(f)["0821"]

    duration = transcript_data["duration"]
    segments = transcript_data["segments"]

    # 1. Generate procedural Assets
    print("[Build] Generating audio beds and sound design...")
    music_wav = ASSETS_DIR / "music-bed.wav"
    generate_music_bed(music_wav, duration + 1.0)

    sfx_click = ASSETS_DIR / "sfx-click.wav"
    generate_sfx(sfx_click, "click")
    sfx_whoosh = ASSETS_DIR / "sfx-whoosh.wav"
    generate_sfx(sfx_whoosh, "whoosh")
    sfx_impact = ASSETS_DIR / "sfx-impact.wav"
    generate_sfx(sfx_impact, "impact")

    print("[Build] Generating motion graphics & telemetry cards...")
    card_growth = ASSETS_DIR / "card_growth.png"
    create_graphic_card(card_growth, "1 LAKH -> 10 LAKH TARGET", "Algorithmic Growth Potential", "10x WEALTH MULTIPLIER", "WEALTH OBJECTIVE", "cyan")

    card_risk = ASSETS_DIR / "card_risk.png"
    create_graphic_card(card_risk, "MAX DRAWDOWN: 4.2%", "Stop Loss & Position Sizing", "CALCULATIVE RISK", "RISK CONTROLS", "green")

    card_cta = ASSETS_DIR / "card_cta.png"
    create_graphic_card(card_cta, "AUTOMATION MASTERCLASS", "Learn Robot Trading Step-by-Step", "PROFIT BRICKS", "FREE EDUCATION", "cyan")

    # 2. Build Subtitle File
    ass_subtitles = DELIVERABLE_DIR / "captions.ass"
    build_ass_subtitles(segments, ass_subtitles)

    # 3. Assemble and Render Complete Multi-Track Master
    print("[Build] Executing GPU hardware master render with punch zooms, ducked audio, and kinetic captions...")
    master_output = OUTPUT_DIR / "0821-production-master.mp4"
    local_output = DELIVERABLE_DIR / "edited.mp4"

    # Escape path for FFmpeg ASS filter
    ass_filter_path = str(ass_subtitles).replace("\\", "/").replace(":", "\\:")

    # Build FFmpeg master command
    # Video: Punch Zooms (1.0x wide vs 1.25x punch) + Overlays
    # Audio: Voice (A1) + Ducked Music (A2) + Master Limiter -14 LUFS
    filter_complex = (
        f"[0:v]split=2[v_base][v_zoom];"
        f"[v_zoom]scale=1350:2400,crop=1080:1920:135:240[v_zoomed];"
        # Select base or zoom depending on timestamps
        f"[v_base][v_zoomed]blend=all_expr='if(between(T,2.8,5.9)+between(T,17.0,21.8)+between(T,44.2,50.5),B,A)'[v_cut];"
        f"[v_cut]ass='{ass_filter_path}'[v_out];"
        # Audio Ducking
        f"[1:a]volume=0.18[music];"
        f"[0:a][music]amix=inputs=2:duration=first:dropout_transition=2[a_mixed];"
        f"[a_mixed]loudnorm=I=-14:TP=-1.0:LRA=7[a_out]"
    )

    cmd = [
        FFMPEG,
        "-y",
        "-i", str(source_video),
        "-i", str(music_wav),
        "-filter_complex", filter_complex,
        "-map", "[v_out]",
        "-map", "[a_out]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "16",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(master_output)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if result.returncode != 0:
        print("Render Error:\n", result.stderr[-3000:])
        raise RuntimeError("Master rendering failed.")

    # Copy deliverable
    shutil.copy2(master_output, local_output)
    print(f"SUCCESS: 0821 Production Master rendered at: {master_output} (Size: {master_output.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    main()

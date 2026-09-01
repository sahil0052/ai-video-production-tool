import json
import os
import subprocess
from pathlib import Path
from imageio_ffmpeg import get_ffmpeg_exe

FFMPEG = get_ffmpeg_exe()
TRAINING_DIR = Path(r"c:\websites\ai video production tool\training videos data")
OUT_ANALYSIS_DIR = Path(r"storage\training_analysis")
OUT_ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

videos = list(TRAINING_DIR.glob("*.mp4"))
print(f"Found {len(videos)} training videos to analyze:")

results = []

for idx, v in enumerate(videos):
    print(f"\n--- [{idx+1}/{len(videos)}] Analyzing: {v.name[:60]}... ---")
    
    # 1. Get video duration and resolution
    probe_cmd = [
        FFMPEG, "-i", str(v)
    ]
    p = subprocess.run(probe_cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    err = p.stderr
    
    # Extract duration & resolution from ffmpeg output
    duration = 0.0
    for line in err.split("\n"):
        if "Duration:" in line:
            # Duration: 00:00:45.32, start: ...
            parts = line.split("Duration:")[1].split(",")[0].strip().split(":")
            if len(parts) == 3:
                duration = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    
    print(f"  Duration: {duration:.2f}s")
    
    # Extract sample frames every 2 seconds to classify layout
    frames_dir = OUT_ANALYSIS_DIR / f"vid_{idx+1:02d}"
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    sample_timestamps = [round(t, 1) for t in list(range(0, int(duration), 2))]
    if len(sample_timestamps) > 25:
        # sample at key points if video is long
        sample_timestamps = [round(t, 1) for t in [0.5, 1.5, 3.0, 5.0, 7.5, 10.0, 13.0, 16.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0] if t < duration]
    
    frame_files = []
    for ts in sample_timestamps:
        frame_path = frames_dir / f"f_{ts:05.1f}s.jpg"
        extract_cmd = [
            FFMPEG, "-y", "-ss", str(ts), "-i", str(v),
            "-vframes", "1", "-q:v", "3", str(frame_path)
        ]
        subprocess.run(extract_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if frame_path.exists():
            frame_files.append({"time": ts, "path": str(frame_path)})
            
    results.append({
        "video_index": idx + 1,
        "filename": v.name,
        "duration": duration,
        "sample_frames_count": len(frame_files),
        "frames_dir": str(frames_dir)
    })

with open(OUT_ANALYSIS_DIR / "summary.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nFinished initial extraction across all training videos!")

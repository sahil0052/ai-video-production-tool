import json
import os
from pathlib import Path
from PIL import Image
import numpy as np

ANALYSIS_DIR = Path(r"storage\training_analysis")

def classify_frame(img_path: Path) -> str:
    """Classify frame into layout category by inspecting image regions."""
    try:
        with Image.open(img_path) as img:
            img = img.convert("RGB").resize((108, 192))
            arr = np.array(img, dtype=np.float32)
            
            # Top half: 0 to 96 (Y), Bottom half: 96 to 192 (Y)
            top_half = arr[0:90, :, :]
            bot_half = arr[102:192, :, :]
            mid_strip = arr[93:99, :, :]
            
            # Check horizontal divider line near Y = 96 (y=50% in portrait)
            # A distinct horizontal split usually has a sharp gradient or distinct color change across mid strip
            row_diff = np.abs(np.diff(arr, axis=0))
            mid_divider_strength = np.mean(row_diff[94:98, :, :])
            
            # Character detection heuristic:
            # Presenter typically has warm skin tones (R > G > B, R-G > 15, R-B > 25)
            r, g, b = bot_half[:, :, 0], bot_half[:, :, 1], bot_half[:, :, 2]
            skin_mask_bot = (r > 80) & (g > 50) & (b > 40) & (r > g) & (g > b) & ((r - g) > 10) & ((r - b) > 15)
            skin_ratio_bot = np.mean(skin_mask_bot)
            
            r_t, g_t, b_t = top_half[:, :, 0], top_half[:, :, 1], top_half[:, :, 2]
            skin_mask_top = (r_t > 80) & (g_t > 50) & (b_t > 40) & (r_t > g_t) & (g_t > b_t) & ((r_t - g_t) > 10) & ((r_t - b_t) > 15)
            skin_ratio_top = np.mean(skin_mask_top)
            
            # If top has high variance / graphical content and bottom has character:
            if mid_divider_strength > 12.0 or (skin_ratio_bot > 0.08 and skin_ratio_top < 0.04):
                return "SPLIT_SCREEN_50_50"
            elif skin_ratio_top > 0.06 and skin_ratio_bot > 0.06:
                return "FULL_SCREEN_CHARACTER"
            else:
                return "FULL_SCREEN_EXPLAINER"
    except Exception as e:
        return "UNKNOWN"

summary_file = ANALYSIS_DIR / "summary.json"
with open(summary_file, "r", encoding="utf-8") as f:
    vids = json.load(f)

video_patterns = []

for v in vids:
    fdir = Path(v["frames_dir"])
    frames = sorted(list(fdir.glob("*.jpg")), key=lambda p: float(p.name.split("_")[1].replace("s.jpg", "")))
    
    timeline = []
    for f in frames:
        ts = float(f.name.split("_")[1].replace("s.jpg", ""))
        layout = classify_frame(f)
        timeline.append({"time": ts, "layout": layout, "frame": f.name})
    
    # Calculate state percentages
    counts = {}
    for item in timeline:
        counts[item["layout"]] = counts.get(item["layout"], 0) + 1
        
    total = len(timeline)
    stats = {k: f"{v/total*100:.1f}%" for k, v in counts.items()}
    
    video_patterns.append({
        "video": v["filename"],
        "duration": v["duration"],
        "layout_distribution": stats,
        "timeline": timeline
    })
    
    print(f"\n=======================================================")
    print(f"VIDEO: {v['filename'][:65]}")
    print(f"Duration: {v['duration']:.1f}s | Layout Distribution: {stats}")
    print(f"Opening 10s Sequence: {[t['layout'] for t in timeline[:5]]}")

with open(ANALYSIS_DIR / "layout_patterns_report.json", "w", encoding="utf-8") as f:
    json.dump(video_patterns, f, indent=2)

print(f"\nSaved comprehensive pattern analysis to {ANALYSIS_DIR / 'layout_patterns_report.json'}")

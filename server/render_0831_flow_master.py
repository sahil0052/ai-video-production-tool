import subprocess, os, sys
from pathlib import Path
from imageio_ffmpeg import get_ffmpeg_exe

ffmpeg = get_ffmpeg_exe()
base_dir = Path(r"c:\websites\ai video production tool")
flow_dir = base_dir / "renderer" / "public" / "flow_videos"
work_dir = base_dir / "storage" / "deliverables" / "voxpipe_0831" / "rendered_segments"
work_dir.mkdir(parents=True, exist_ok=True)
deliverable_dir = base_dir / "storage" / "deliverables" / "voxpipe_0831"

print("Rendering 0831 Google Flow 3D Animation Top Track (Zero Text Clutter)...")

# Map 6 beats to high-end Google Flow 3D animation videos
flow_beats = [
    (1, flow_dir / "flow0829_01_human_vs_robot_faceoff.mp4", 0.0, 7.5, "seg1_flow_brain_faceoff.mp4"),
    (2, flow_dir / "gold05_market_price_breakout.mp4", 0.0, 7.0, "seg2_flow_profit_breakout.mp4"),
    (3, flow_dir / "gold02_buyers_sellers_scale.mp4", 0.0, 7.5, "seg3_flow_fear_greed_scale.mp4"),
    (4, flow_dir / "flow_crash_03_price_drops_700_question.mp4", 0.0, 7.5, "seg4_flow_crash_drop.mp4"),
    (5, flow_dir / "flow0829_02_zero_emotion_processor.mp4", 0.0, 7.0, "seg5_flow_emotion_override.mp4"),
    (6, flow_dir / "flow0829_05_strategy_risk_management_trophy.mp4", 0.0, 7.9, "seg6_flow_discipline_trophy.mp4"),
]

concat_list = []

for b_id, src_video, ss, dur, out_name in flow_beats:
    out_path = work_dir / out_name
    print(f"Rendering Beat {b_id}: {src_video.name} ({dur}s)...")
    
    # Scale, crop to 1080x960, set exact duration, clean 30fps
    cmd = [
        ffmpeg, "-y",
        "-ss", str(ss), "-t", str(dur), "-i", str(src_video),
        "-filter_complex",
        "[0:v]scale=1080:960:force_original_aspect_ratio=increase,crop=1080:960[outv]",
        "-map", "[outv]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        str(out_path)
    ]
    subprocess.run(cmd, check=True)
    concat_list.append(out_path)

# Concatenate all 6 top segments into top_flow_track.mp4
concat_txt = work_dir / "concat_flow_list.txt"
with open(concat_txt, "w") as f:
    for seg in concat_list:
        f.write(f"file '{seg.as_posix()}'\n")

top_track_path = deliverable_dir / "top_flow_track.mp4"
cmd = [
    ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30", str(top_track_path)
]
subprocess.run(cmd, check=True)
print("Saved 100% Clean Google Flow Top Track:", top_track_path)

import subprocess, os
from pathlib import Path
import cv2
from imageio_ffmpeg import get_ffmpeg_exe

ffmpeg = get_ffmpeg_exe()
work_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0831_1_nishahomes")
temp_video = work_dir / "temp_composed_video.mp4"
raw_video = Path(r"D:\Downloads\0831 (1).mp4")
master_audio = work_dir / "master_audio_track.wav"
output_master = work_dir / "edited.mp4"

print("1. Mastering audio to -14.0 LUFS...")
cmd_audio = [
    ffmpeg, "-y",
    "-i", str(raw_video),
    "-vn",
    "-af", "acompressor=threshold=-20dB:ratio=3.5:attack=15:release=150,volume=1.0,loudnorm=I=-14.0:TP=-1.5:LRA=7.0",
    "-ar", "48000",
    str(master_audio)
]
subprocess.run(cmd_audio, check=True)
print("Saved mastered audio:", master_audio)

print("2. Muxing video and audio to final master...")
cmd_mux = [
    ffmpeg, "-y",
    "-i", str(temp_video),
    "-i", str(master_audio),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast", "-crf", "18",
    "-c:a", "aac", "-b:a", "192k",
    "-shortest",
    str(output_master)
]
subprocess.run(cmd_mux, check=True)
print(f"Master Deliverable Created: {output_master} ({(output_master.stat().st_size/1024/1024):.2f} MB)")

# Extract 20 QC Frames
print("3. Extracting 20 QC Audit Frames...")
audit_dir = work_dir / "audit_frames"
audit_dir.mkdir(parents=True, exist_ok=True)
audit_vid = cv2.VideoCapture(str(output_master))
audit_fps = audit_vid.get(cv2.CAP_PROP_FPS) or 30.0
audit_total = int(audit_vid.get(cv2.CAP_PROP_FRAME_COUNT))

step = audit_total // 20
for idx in range(20):
    f_num = min(idx * step, audit_total - 1)
    audit_vid.set(cv2.CAP_PROP_POS_FRAMES, f_num)
    ret, frame = audit_vid.read()
    if ret:
        out_f = audit_dir / f"frame_{idx+1:03d}.jpg"
        cv2.imwrite(str(out_f), frame)
audit_vid.release()
print("Saved 20 QC Audit Frames to:", audit_dir)
print("COMPLETED SUCCESSFULLY!")

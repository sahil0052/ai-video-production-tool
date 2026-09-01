import subprocess, json
from pathlib import Path
from imageio_ffmpeg import get_ffmpeg_exe

ffmpeg = get_ffmpeg_exe()
vid_path = r"D:\Downloads\0901.mp4"
work_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0901_profitbricks")
work_dir.mkdir(parents=True, exist_ok=True)

# 1. Probe video
cmd_probe = f'ffprobe -v quiet -print_format json -show_format -show_streams "{vid_path}"'
res = subprocess.run(cmd_probe, shell=True, capture_output=True, text=True)
if res.returncode == 0:
    info = json.loads(res.stdout)
    with open(work_dir / "probe.json", "w") as f:
        json.dump(info, f, indent=2)
    
    # print summary
    fmt = info.get("format", {})
    duration = float(fmt.get("duration", 0))
    v_stream = next((s for s in info.get("streams", []) if s["codec_type"] == "video"), {})
    a_stream = next((s for s in info.get("streams", []) if s["codec_type"] == "audio"), {})
    print(f"Duration: {duration:.3f}s")
    print(f"Video: {v_stream.get('width')}x{v_stream.get('height')} @ {v_stream.get('r_frame_rate')} fps, codec: {v_stream.get('codec_name')}")
    print(f"Audio: sample_rate {a_stream.get('sample_rate')}, channels {a_stream.get('channels')}")
else:
    print("Probe error:", res.stderr)

# 2. Extract audio
audio_out = work_dir / "raw_audio.wav"
subprocess.run([ffmpeg, "-y", "-i", vid_path, "-vn", "-ar", "16000", "-ac", "1", str(audio_out)], check=True)
print(f"Audio extracted to: {audio_out}")

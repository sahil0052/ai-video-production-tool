import cv2
from pathlib import Path

vid = cv2.VideoCapture(r"D:\Downloads\0831 (1).mp4")
out_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0831_1_nishahomes\raw_sample_frames")
out_dir.mkdir(parents=True, exist_ok=True)

timestamps = [1.0, 5.0, 9.5, 16.0, 23.0, 30.0, 36.0, 39.0]
fps = vid.get(cv2.CAP_PROP_FPS) or 30.0

for t in timestamps:
    vid.set(cv2.CAP_PROP_POS_FRAMES, int(t * fps))
    ret, frame = vid.read()
    if ret:
        out_path = out_dir / f"frame_{int(t*10):03d}.jpg"
        cv2.imwrite(str(out_path), frame)
        print(f"Saved {out_path}")
vid.release()

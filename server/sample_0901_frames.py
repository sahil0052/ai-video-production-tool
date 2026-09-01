import cv2
from pathlib import Path

vid_path = r"D:\Downloads\0901.mp4"
work_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0901_profitbricks\raw_frames")
work_dir.mkdir(parents=True, exist_ok=True)

cap = cv2.VideoCapture(vid_path)
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
step = total // 10

for i in range(10):
    f_num = min(i * step, total - 1)
    cap.set(cv2.CAP_PROP_POS_FRAMES, f_num)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(str(work_dir / f"frame_{i+1:02d}.jpg"), frame)
cap.release()
print("Saved 10 sample frames!")

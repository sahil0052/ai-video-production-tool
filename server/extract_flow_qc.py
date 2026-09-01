import cv2
from pathlib import Path
p = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0831_1_nishahomes\test_flow_generated_clip.mp4")
out_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0831_1_nishahomes\flow_qc_frames")
out_dir.mkdir(parents=True, exist_ok=True)

cap = cv2.VideoCapture(str(p))
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"Total Frames: {total}, FPS: {fps}, Res: {w}x{h}")

for idx, f_num in enumerate([10, total // 2, total - 10]):
    cap.set(cv2.CAP_PROP_POS_FRAMES, f_num)
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(str(out_dir / f"flow_frame_{idx+1}.jpg"), frame)
cap.release()
print("Saved QC frames successfully!")

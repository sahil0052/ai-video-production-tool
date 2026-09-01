import cv2
from pathlib import Path

flow_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0901_profitbricks\flow_clips")
qc_dir = flow_dir / "qc_frames"
qc_dir.mkdir(parents=True, exist_ok=True)

clips = [
    "flow_0901_01_dollar_surge.mp4",
    "flow_0901_02_double_whammy.mp4",
    "flow_0901_03_investor_checklist.mp4"
]

for clip_name in clips:
    p = flow_dir / clip_name
    cap = cv2.VideoCapture(str(p))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, total // 2)
    ret, frame = cap.read()
    if ret:
        out_path = qc_dir / f"{clip_name}.jpg"
        cv2.imwrite(str(out_path), frame)
        print(f"Saved QC frame for {clip_name}")
    cap.release()

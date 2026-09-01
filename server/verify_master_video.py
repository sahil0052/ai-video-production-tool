import cv2
from pathlib import Path

p = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0901_profitbricks\edited.mp4")
print("Master Video Exists:", p.exists())
print("File Size:", p.stat().st_size, "bytes")

cap = cv2.VideoCapture(str(p))
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
dur = total / fps
print(f"Total Frames: {total}, FPS: {fps}, Duration: {dur:.2f}s, Resolution: {w}x{h}")
cap.release()

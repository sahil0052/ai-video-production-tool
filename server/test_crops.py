import cv2
from pathlib import Path

img = cv2.imread(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0831_1_nishahomes\raw_sample_frames\frame_010.jpg")
out_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0831_1_nishahomes\test_crops")
out_dir.mkdir(parents=True, exist_ok=True)

for y in [160, 200, 240, 280, 320]:
    crop = img[y:y+960, 0:1080]
    cv2.imwrite(str(out_dir / f"crop_y_{y}.jpg"), crop)
    print(f"Saved crop_y_{y}.jpg")

import os
from pathlib import Path
p = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0831_1_nishahomes\test_flow_generated_clip.mp4")
print("Video File Exists:", p.exists())
print("Video File Size:", p.stat().st_size, "bytes")

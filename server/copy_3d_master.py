import shutil
from pathlib import Path

SRC = Path(r"storage/deliverables/0826_3_bankrun_master/edited.mp4")
ART_DIR = Path(r"C:\Users\HPUSER\.gemini\antigravity\brain\511882d1-5377-47fa-86e8-4adac25cec42")
DEST = ART_DIR / "bankrun_final_3d_master.mp4"

shutil.copy2(SRC, DEST)
print(f"Copied 3D Master to: {DEST} ({DEST.stat().st_size / (1024*1024):.2f} MB)")

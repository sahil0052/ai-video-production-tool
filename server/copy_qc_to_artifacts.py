import shutil
from pathlib import Path

src_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0901_profitbricks\qc_audit")
art_dir = Path(r"C:\Users\HPUSER\.gemini\antigravity\brain\511882d1-5377-47fa-86e8-4adac25cec42\qc_frames_0901")
art_dir.mkdir(parents=True, exist_ok=True)

for img_p in src_dir.glob("*.jpg"):
    dest = art_dir / img_p.name
    shutil.copy2(img_p, dest)
    print(f"Copied: {img_p.name} -> {dest}")

print("All QC frames copied to artifacts directory!")

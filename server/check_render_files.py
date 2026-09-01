from pathlib import Path
work_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0901_profitbricks")
for f in work_dir.glob("*"):
    print(f.name, f.stat().st_size)

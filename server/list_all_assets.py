import os
from pathlib import Path
v_dir = Path(r"c:\websites\ai video production tool\storage\assets\real_estate_verified")
r_dir = Path(r"c:\websites\ai video production tool\storage\assets\real_estate_raw")

print("VERIFIED ASSETS:")
for f in v_dir.glob("*"):
    print(" ", f.name, f.stat().st_size)

print("\nRAW ASSETS:")
for f in r_dir.glob("*"):
    print(" ", f.name, f.stat().st_size)

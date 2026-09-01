import cv2
import numpy as np
from pathlib import Path
from PIL import Image

work_dir = Path(r"c:\websites\ai video production tool\storage\deliverables\voxpipe_0901_profitbricks")
work_dir.mkdir(parents=True, exist_ok=True)
asset_dir = work_dir / "assets"
asset_dir.mkdir(parents=True, exist_ok=True)

# 1. Process Profit Bricks Logo
src_logo = Path(r"c:\websites\profitbricks website\JEPG Profit Bricks Logo-01.jpg (1).jpeg")
img = Image.open(src_logo).convert("RGBA")
datas = img.getdata()

# Make white background transparent
newData = []
for item in datas:
    # If pixel is near white
    if item[0] > 240 and item[1] > 240 and item[2] > 240:
        newData.append((255, 255, 255, 0))
    else:
        newData.append(item)

img.putdata(newData)
logo_path = asset_dir / "profit_bricks_logo.png"
img.save(logo_path, "PNG")
print(f"Profit Bricks transparent logo saved: {logo_path}")

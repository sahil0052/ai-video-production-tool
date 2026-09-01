from PIL import Image
from pathlib import Path

logo_src = Path(r"C:\Users\HPUSER\.gemini\antigravity\brain\511882d1-5377-47fa-86e8-4adac25cec42\.user_uploaded\media_1788175714409.png")
out_dir = Path(r"c:\websites\ai video production tool\storage\assets\logos")
out_dir.mkdir(parents=True, exist_ok=True)

img = Image.open(logo_src)
print("Nisha Homes Logo size:", img.size, img.mode)

# Save high-res master copy
nisha_logo_path = out_dir / "nisha_homes_logo.png"
img.save(nisha_logo_path)
print("Saved official Nisha Homes logo to:", nisha_logo_path)
